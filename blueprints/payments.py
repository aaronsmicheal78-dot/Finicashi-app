#======================================================================================================
#
#   PAYMENT API BLUEPRINT FOR MARZ PAYMENT GATEWAY INTEGRATION
#
#===========================================================================================================
from flask import Blueprint, request, jsonify, current_app, session, url_for, current_app                                                                   # HTTP client to call Marz
import uuid                                                                              
from models import Payment, PaymentStatus, User, Withdrawal, PackageCatalog, User, Package, Referral, Bonus, ReferralBonus                    
from sqlalchemy.exc import IntegrityError                             
from sqlalchemy import select                                          
from sqlalchemy.orm import Session   
import re  
import json
from sqlalchemy import and_
import requests 
from extensions import db
import os
from datetime import datetime, timedelta, timezone
import base64
import logging
from decimal import Decimal
from blueprints.payments_helpers import MARZ_BASE_URL
import sys
from flask import Blueprint, request, jsonify, session
from blueprints.payments_helpers import  (validate_payment_input, handle_existing_payment,
    create_payment_record, send_to_marzpay
)



bp = Blueprint("payments", __name__)  
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')



    
#=============================================================================================
#      PAYMENT INITIATION ENDPOINT
#============================================================================================
@bp.route("/payments/callback", methods=['POST'])
def payment_callback():
    data = request.get_json(silent=True) or {}
    print(f"🔍 RAW CALLBACK DATA: {json.dumps(data, indent=2)}") 
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    transaction = data.get("transaction", {})
    status = transaction.get("status", "completed").lower()
    print(f"🔄 MARZ STATUS: {status}")
    
    reference = (
        data.get("transaction", {}).get("reference") or
        data.get("reference")
    )
    ext_uuid = transaction.get("uuid") or data.get("uuid")
    
    if not reference and not ext_uuid:
        return jsonify({"error": "Missing reference"}), 400
    
    payment = None
    if reference:
        payment = Payment.query.filter_by(reference=reference).first()
    
    if not payment and ext_uuid:
        payment = Payment.query.filter_by(external_ref=ext_uuid).first()
    
    if not payment:
       print(f"No matching payment for reference {reference} / ext {ext_uuid}")
       return jsonify({"status": "ignored"}), 200
    
    if status in ("success", "completed", "paid", "sandbox"):
        try:
            from sqlalchemy.exc import SQLAlchemyError
            old_status = payment.status
            payment.status = PaymentStatus.COMPLETED.value
            print(f"🔄 Updated payment status from {old_status} to {payment.status}") 
            payment.verified = True
            payment.updated_at = datetime.now(timezone.utc)
            payment.provider = data.get("transaction", {}).get("provider")
            payment.external_ref = data.get("transaction", {}).get("uuid")
            payment.raw_response = json.dumps(data)
            payment.provider_reference = transaction.get("provider_reference")
            print(f"🔍 Checking payment type: {payment.payment_type}")
            db.session.add(payment)
            db.session.commit()  
            print(f"✅ Payment status updated to: {payment.status}") 
            current_payment = Payment.query.get(payment.id)
            current_app.logger.info(f"DB payment status: {current_payment.status}")
 

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to commit payment update: {e}")

        
        if payment.payment_type == "package":
            from bonus.payment_processor import process_package_purchase
            success, message = process_package_purchase(payment)
            if success:
                
                return jsonify({"status": "ok", "bonus_status": "success", "message": message}), 200
            else:
                return jsonify({"status": "ok", "bonus_status": "error", "message": message}), 200
        
        elif payment.payment_type == "deposit":
            user = User.query.get(payment.user_id)
            if user:
                user.actual_balance += payment.amount
                print(f"Deposit completed: Added {payment.amount} to user {user.id} actual balance")
                db.session.commit()
                return jsonify({"status": "ok", "message": "Deposit processed"}), 200
        
    else:
       
        print(f"❌ Payment failed with status: {status}")
        payment.status = PaymentStatus.FAILED.value
        payment.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({"status": "ok", "message": "Payment marked as failed"}), 200
    
    
    return jsonify({"status": "ok"}), 200
#========================================================================================================
#========================================================================================================

#=====================================================================================================================
# 
# 
# 
@bp.route("/payments/initiate", methods=['POST'])
def initiate_payment():
    print("DATA RECIEVED: SILENTLY PROCESSING")
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        validated, error = validate_payment_input(data)
        if error:
            return error

        amount = validated["amount"]
        phone = validated["phone"]
        payment_type = validated["payment_type"]          
        package_obj = validated.get("package_obj")  

        if payment_type == "package":
            if not package_obj:
               return jsonify({"error": "Package not found"}), 400

            if payment_type == "package" and user.actual_balance >= package_obj.amount:
                logging.info("=== STARTING PAYMENT PROCESS ===")
                logging.info(f"User: {user.id}, Amount: {package_obj.amount}, Type: {payment_type}")
                
                user.actual_balance -= package_obj.amount
                db.session.add(user)

                # Check for existing payment
                logging.info("Checking for existing payment...")
                existing_payment = handle_existing_payment(user, package_obj.amount, payment_type)
                
                if existing_payment:
                    logging.info("Found existing payment, returning it")
                    return jsonify({
                        "reference": existing_payment.reference,
                        "status": existing_payment.status,
                        "note": "Idempotent: existing record returned"
                    }), 200

                # Create payment record
                logging.info("Creating new payment record...")
                payment = create_payment_record(user, amount, phone, payment_type, package=package_obj)
                
                if not payment:
                    return jsonify({"error": "Failed to create payment record"}), 500

                # Create user package
                logging.info("Creating user package...")
                from blueprints.payments_helpers import create_user_package
                user_package = create_user_package(user, package_obj)
                logging.info(f"Created user package: {user_package}")
                
                # Update payment status
                payment.status = PaymentStatus.COMPLETED.value
                payment.raw_response = json.dumps({"method": "internal_balance"})
                payment.balance_type_used = "actual_balance"

                db.session.add(payment)
                db.session.commit()
                logging.info("=== PAYMENT PROCESS COMPLETED SUCCESSFULLY ===")
        
                # USE THE HELPER FOR PACKAGE + BONUS PROCESSING
                try:
                    from bonus.payment_processor import process_package_purchase
                    print(f"🔄 Processing package and bonuses for internal purchase: {payment.id}")
                    success, message = process_package_purchase(payment)
                    
                    if success:
                        
                        print(f"✅ Internal purchase bonuses processed: {message}")
                        bonus_status = "success"
                       
                    else:
                        print(f"⚠️ Internal purchase bonuses failed: {message}")
                        bonus_status = "error"
                        
                except Exception as e:
                    logger.error(f"Bonus processing failed for internal payment: {e}")
                    bonus_status = "error"
                    message = str(e)
                
                return jsonify({
                    "reference": payment.reference,
                    "status": PaymentStatus.COMPLETED.value,
                    "payment_type": payment_type,
                    "package": package_obj.id,
                    "message": "Package purchased using account balance",
                    "new_actual_balance": user.actual_balance,
                    "available_balance": user.available_balance,
                    "referral_bonus_processed": bonus_status == "success",
                    "bonus_message": message
                }), 200
            
            else:
                # External payment for insufficient balance
                payment = create_payment_record(user, amount, phone, payment_type, package=package_obj)
                if not payment:
                    return jsonify({"error": "Failed to create payment record"}), 500

                # FIX: Ensure send_to_marzpay returns proper format
                # marz_response = send_to_marzpay(payment, phone, amount, package_obj)
                #if isinstance(marz_response, tuple) and len(marz_response) == 2:
                marz_data, error = send_to_marzpay(payment, phone, amount, package_obj)
                if error:
                    payment.status = PaymentStatus.FAILED.value
                    db.session.commit()
                    return error
                db.session.commit()
                # checkout_url = marz_data.get("checkout_url") if marz_data else None
                # if not checkout_url:
                #     payment.status = PaymentStatus.FAILED.value
                #     db.session.commit()
                #     return jsonify({"error": "No checkout URL returned from gateway"}), 500
                return jsonify({
                    "reference": payment.reference,
                    "status": payment.status,  # Use the status set by send_to_marzpay
                    "payment_type": payment_type,
                    "package": package_obj.id,
                    "checkout_url": marz_data.get("pop_up_info") if marz_data else None
                }), 200
            # else:
            #     # Handle case where function doesn't return tuple
            #     payment.status = PaymentStatus.FAILED.value
            #     db.session.commit()
            #     return jsonify({"error": "Invalid response from payment gateway"}), 500

        elif payment_type == "deposit":
            existing_response = handle_existing_payment(user, amount, payment_type)
            if existing_response:
                return existing_response

            payment = create_payment_record(user, amount, phone, payment_type)
            if not payment:
                return jsonify({"error": "Failed to create payment record"}), 500

            marz_data, error = send_to_marzpay(payment, phone, amount)  
            if error:
                payment.status = PaymentStatus.FAILED.value
                db.session.commit()
                return error
            
            db.session.commit()

            return jsonify({
                "reference": payment.reference,
                "status": payment.status,
                "payment_type": payment_type,
                "checkout_url": marz_data.get("pop_up_info") if marz_data else None,
                "message": "Deposit initiated successfully"
            }), 200

        else:
            return jsonify({"error": "Invalid payment type. Use 'package' or 'deposit'"}), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Payment initiation error: {e}")
        return jsonify({"error": "Payment processing failed"}), 500 


#=======================================================================================================
#                   ------------------------------------------------------
#---------------------WEBHOOK CALLBACK ENDPOINT FOR PAYMENT INITIATION--------------------------------------
#=========================================================================================================


from decimal import Decimal
import uuid
import os
import requests
from flask import jsonify, request, session, Blueprint
from .withdraw_helpers import (
    WithdrawalProcessor, 
    WithdrawalQueryHelper,
    WithdrawalConfig,
    WithdrawalException
)


# MarzPay configuration
#api.MARZ_BASE_URL = os.environ.get("MARZ_BASE_URL")
MARZ_BASE_URL = 'https://wallet.wearemarz.com/api/v1'
#=================================================================================================================
@bp.route("/payments/withdraw", methods=["POST"])
def withdraw():
    """
    Main withdrawal endpoint with MarzPay integration
    """
    

    data = request.get_json(force=True, silent=True)
    amount = data.get("amount")
    phone_number = data.get("phone") or data.get("phone_number")

    print("MOBILE DEBUG:", request.headers)
    print("BODY:", request.data)
    logger.info(f"WITHDRAW PROCESSING STARTED: {data}, {amount}, {phone_number}")


    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
   
    if not amount or not phone_number:
        return jsonify({"error": "Amount and phone number are required"}), 400
    
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    try:
        # Convert amount to Decimal for processing
        amount_decimal = Decimal(str(amount))
        
        # Step 1: Process withdrawal internally (validate, deduct balances, create record)
        success, message, withdrawal_data = WithdrawalProcessor.process_withdrawal_request(
            user_id, amount_decimal, phone_number
        )
        
        if not success:
            return jsonify({"error": message}), 400

       
        merchant_reference = withdrawal_data['reference'] 
        amount = withdrawal_data['net_amount']
        
        CALL_BACK_URL = "https://finicashi-app.onrender.com/withdraw/callback"
        
        formatted_phone = phone_number.strip()
        if formatted_phone.startswith('0'):
            formatted_phone = f"+256{formatted_phone[1:]}"
        elif formatted_phone.startswith('256'):
            formatted_phone = f"+{formatted_phone}"
        elif not formatted_phone.startswith('+'):
            formatted_phone = f"+256{formatted_phone[-9:]}"
        
        payload = {
            "reference": withdrawal_data['reference'],
            "amount":  withdrawal_data['net_amount'],                                                  #int(amount), 
            "phone_number": formatted_phone,  
            "country": "UG",
            "description": "customer_withdraw",
            "callback_url": CALL_BACK_URL,
        }
        print("🔹 MarzPay payload:", json.dumps(payload, indent=2))
        headers = {
            "Authorization": f"Basic {os.environ.get('MARZ_AUTH_HEADER')}",
            "Content-Type": "application/json"
        }

        # Step 3: Call MarzPay API
        print(f"Calling MarzPay API for withdrawal {merchant_reference}", flush=True)
        response = requests.post(
            f"{MARZ_BASE_URL}/send-money", 
            json=payload, 
            headers=headers, 
            timeout=60
        )
        
        print(f"MarzPay response status: {response.status_code}, body: {response.text}", flush=True)
        response.raise_for_status()
        marz_data = response.json()

        # Step 4: Update withdrawal status based on MarzPay response
        if marz_data.get('status') in ['success', 'pending', 'processing']:
            # Withdrawal successfully submitted to MarzPay
            WithdrawalProcessor.complete_withdrawal(withdrawal_data['withdrawal_id'])
            
            return jsonify({
                "success": True,
                "message": "Withdrawal request submitted successfully",
                "withdrawal_id": merchant_reference,
                "marz_response": marz_data,
                "net_amount": str(withdrawal_data.get('net_amount', amount)),
                "fee": str(withdrawal_data.get('fee', '0'))
            }), 200
        else:
            # MarzPay returned non-success status
            raise Exception(f"MarzPay returned status: {marz_data.get('status')}")

    except requests.exceptions.RequestException as e:
        print(f"MarzPay request error: {str(e)}", flush=True)
        
        # Reverse the withdrawal since MarzPay failed
        if 'withdrawal_data' in locals():
            WithdrawalProcessor.fail_withdrawal(
                withdrawal_data['withdrawal_id'],
                user_id,
                amount_decimal,
                withdrawal_data.get('balances', {})
            )
        
        return jsonify({
            "error": "Payment gateway temporarily unavailable",
            "details": "Your funds have been refunded. Please try again later."
        }), 502
        
    except WithdrawalException as e:
        print(f"Withdrawal processing error: {str(e)}", flush=True)
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        print(f"Unexpected error in withdrawal: {str(e)}", flush=True)
        
        # Attempt to reverse on any unexpected error
        if 'withdrawal_data' in locals():
            WithdrawalProcessor.fail_withdrawal(
                withdrawal_data['withdrawal_id'],
                user_id,
                amount_decimal,
                withdrawal_data.get('balances', {})
            )
        
        return jsonify({
            "error": "Withdrawal processing failed",
            "details": "Your funds have been refunded. Please try again."
        }), 500
    
#=================================================================================================
#=================================================================================================

import logging
from flask import request, jsonify
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
#===================================================================================================
@bp.route("/withdraw/callback", methods=["POST"])
def withdraw_callback():
    print("MARZ WITHDRAW CALLBACK RECEIVED")
    
    try:
        data = request.get_json()
        print(f"RAW CALLBACK DATA: {json.dumps(data, indent=2)}")
        if not data:
            return jsonify({"error": "No data received"}), 400
        
        # EXACT SAME LOGIC AS PAYMENT CALLBACK
        transaction = data.get("transaction", {})
        
        # Get references - SAME AS PAYMENT
        reference = (
            transaction.get("reference") or
            data.get("reference")  
        )
        provider_reference = data.get("ptovider_reference") or transaction.get("provider_reference")

        ext_uuid = transaction.get("uuid") or data.get("uuid")
        
        status = transaction.get("status", "").lower()
        print(f"🔄 MARZ WITHDRAW STATUS: {status}")
        print(f"🔍 Checking references: reference={reference}, ext_uuid={ext_uuid}")

        # SIMPLE SEARCH - SAME AS PAYMENT
        withdrawal = None
        
        # Try by reference (your UUID) first
        if reference:
            withdrawal = Withdrawal.query.filter_by(reference=reference).first()
            if withdrawal:
                print(f"✅ Found withdrawal by reference: {reference}")
        
        # Try by external UUID
        if not withdrawal and ext_uuid:
            withdrawal = Withdrawal.query.filter_by(external_ref=ext_uuid).first()
            if withdrawal:
                print(f"✅ Found withdrawal by external UUID: {ext_uuid}")

        if not withdrawal and provider_reference:
            withdrawal = Withdrawal.query.filter_by(reference=provider_reference).first()
            if withdrawal:
                print(f"✅ Found withdrawal by provider_reference: {provider_reference}")
        
        if not withdrawal:
            print(f"❌ No withdrawal found for reference={reference}")
            return jsonify({"status": "ignored"}), 200
    
        print(f"🎯 Processing withdrawal ID: {withdrawal.id}, current status: {withdrawal.status}")
        
        # Store MarzPay's reference if we don't have it
        if not withdrawal.external_ref and ext_uuid:
            withdrawal.external_ref = ext_uuid
            db.session.commit()
            print(f"💾 Stored external_ref: {ext_uuid}")
        
        # Process status (your existing logic)
        if withdrawal.status in ["completed", "failed"]:
            print(f"⏭️ Withdrawal {withdrawal.id} already {withdrawal.status}. Skipping.")
            return jsonify({"status": "ok"}), 200
        
        if status in ['success', 'completed', 'approved', 'paid', 'sandbox']:
            print(f"✅ Completing withdrawal ID: {withdrawal.id}")
            WithdrawalProcessor.complete_withdrawal(withdrawal.id, reference or ext_uuid)
        
        elif status in ['failed', 'rejected']:
            print(f"❌ Failing withdrawal ID: {withdrawal.id}")
            WithdrawalProcessor.fail_withdrawal(withdrawal.id, withdrawal.user_id, withdrawal.amount, {...})
        
        return jsonify({"status": "callback processed"}), 200
    
    except Exception as e:
        print(f"💥 Error processing MarzPay callback: {e}")
        return jsonify({"error": "Callback processing failed"}), 500

#===============================================================================================================

@bp.route("/payments/withdraw/history", methods=["GET"])
def withdrawal_history():
    """
    Get user's withdrawal history
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        limit = request.args.get('limit', 10, type=int)
        withdrawals = WithdrawalQueryHelper.get_user_withdrawals(user_id, limit)
        
        withdrawal_list = []
        for withdrawal in withdrawals:
            withdrawal_list.append({
                'id': withdrawal.id,
                'amount': str(withdrawal.amount),
                'net_amount': str(withdrawal.net_amount) if withdrawal.net_amount else None,
                'fee': str(withdrawal.fee) if withdrawal.fee else None,
                'phone': withdrawal.phone,
                'status': withdrawal.status,
                'external_ref': withdrawal.external_ref,
                'external_txid': withdrawal.external_txid,
                'created_at': withdrawal.created_at.isoformat() if withdrawal.created_at else None,
                'updated_at': withdrawal.updated_at.isoformat() if withdrawal.updated_at else None
            })
        
        return jsonify({
            "success": True,
            "withdrawals": withdrawal_list,
            "total": len(withdrawal_list)
        }), 200
        
    except Exception as e:
        print(f"Error fetching withdrawal history: {str(e)}", flush=True)
        return jsonify({"error": "Failed to fetch withdrawal history"}), 500


@bp.route("/payments/withdraw/limits", methods=["GET"])
def withdrawal_limits():
    """
    Get withdrawal limits and configuration
    """
    return jsonify({
        "success": True,
        "limits": {
            "min_withdrawal": str(WithdrawalConfig.MIN_WITHDRAWAL),
            "max_withdrawal": str(WithdrawalConfig.MAX_WITHDRAWAL),
            "processing_fee_percent": str(WithdrawalConfig.PROCESSING_FEE_PERCENT),
            "hold_period_hours": WithdrawalConfig.HOLD_PERIOD_HOURS
        }
    }), 200


@bp.route("/payments/withdraw/<withdrawal_id>", methods=["GET"])
def get_withdrawal_status(withdrawal_id):
    """
    Get specific withdrawal status
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        withdrawal = Withdrawal.query.filter_by(
            id=withdrawal_id, 
            user_id=user_id
        ).first()
        
        if not withdrawal:
            return jsonify({"error": "Withdrawal not found"}), 404
        
        return jsonify({
            "success": True,
            "withdrawal": {
                'id': withdrawal.id,
                'amount': str(withdrawal.amount),
                'net_amount': str(withdrawal.net_amount) if withdrawal.net_amount else None,
                'fee': str(withdrawal.fee) if withdrawal.fee else None,
                'phone': withdrawal.phone,
                'status': withdrawal.status,
                'external_ref': withdrawal.external_ref,
                'external_txid': withdrawal.external_txid,
                'created_at': withdrawal.created_at.isoformat() if withdrawal.created_at else None,
                'updated_at': withdrawal.updated_at.isoformat() if withdrawal.updated_at else None
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching withdrawal status: {str(e)}", flush=True)
        return jsonify({"error": "Failed to fetch withdrawal status"}), 500

#==================================================================================================

