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
from extensions import db, SessionLocal
import os
from datetime import datetime, timedelta
import base64
import logging
from decimal import Decimal
from blueprints.payments_helpers import MARZ_BASE_URL
import sys
from flask import Blueprint, request, jsonify, session
from blueprints.payments_helpers import  (validate_payment_input, handle_existing_payment,
    create_payment_record, send_to_marzpay
)
from blueprints.package_helpers import PackagePurchaseValidator


bp = Blueprint("payments", __name__)  
logger = logging.getLogger(__name__)

#=============================================================================================
#      PAYMENT INITIATION ENDPOINT
#============================================================================================
@bp.route("/payments/callback", methods=['POST'])
def payment_callback():
    print("=== MARZ CALLBACK TRIGGERED ===") 

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No JSON data"}), 400

    transaction = data.get("transaction", {})
    status = transaction.get("status", "completed").lower()
    reference = (
        data.get("transaction", {}).get("reference") or
        data.get("reference")
    )
    ext_uuid = transaction.get("uuid") or data.get("uuid")
    
    if not reference and not ext_uuid:
        return jsonify({"error": "Missing reference"}), 400
    
    # Initialize payment variable
    payment = None
    if reference:
        payment = Payment.query.filter_by(reference=reference).first()
    
    if not payment and ext_uuid:
        payment = Payment.query.filter_by(external_ref=ext_uuid).first()
    
    if not payment:
        print(f"No matching payment for reference {reference} / ext {ext_uuid}")
        return jsonify({"status": "ignored"}), 200
    
    # Debug print - NOW payment is guaranteed to exist
    print(f"🔍 DEBUG: Payment ID: {payment.id}, Status: {payment.status}, Type: {payment.payment_type}")
    print(f"🔍 DEBUG: Callback status: {status}")
    
    # Process NEW successful payments
    if status in ("success", "completed", "paid", "sandbox"):
        print("🔄 Processing new successful payment...")
        
        # Update payment status to completed
        payment.status = PaymentStatus.COMPLETED.value
        payment.verified = True
        payment.updated_at = datetime.utcnow()
        payment.provider = data.get("transaction", {}).get("provider")
        payment.external_ref = data.get("transaction", {}).get("uuid")
        payment.raw_response = json.dumps(data)
        payment.provider_reference = transaction.get("provider_reference")
        
        db.session.commit()  # Commit payment status first
        
        # NOW process package and bonuses
        if payment.payment_type == "package":
            print("🎯 Starting package and bonus processing...")
            
            description = (
                data.get("transaction", {}).get("description") or
                data.get("description", "")
            )
            package = None
            if "payment_for_" in description:
                package = description.replace("payment_for_", "").strip()
                package_catalog = PackageCatalog.query.filter(
                    db.func.lower(PackageCatalog.name) == package.lower()
                ).first()
                
            print(f"Extracted package name: {package}")
            if payment.user_id and package:
                user = User.query.get(payment.user_id)
                
                print(f"Payment user_id: {payment.user_id}")
                if user:
                    package_catalog = PackageCatalog.query.filter_by(name=package).first()
                print(f"Package catalog found: {package_catalog}")
                if package_catalog:
                    print(f"Package catalog ID: {package_catalog.id}, Duration: {package_catalog.duration_days}")
                    
                    new_package = Package(
                        user_id = user.id,
                        catalog_id = package_catalog.id,
                        package=package_catalog.name,
                        type="purchased",
                        status='active',
                        activated_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=package_catalog.duration_days)
                    )
                    db.session.add(new_package)
                    db.session.commit()

                    # NOW process bonuses
                    try:
                        from bonus.validation import BonusValidationHelper
                        from bonus.bonus_calculation import BonusCalculationHelper
                        from bonus.bonus_payment import BonusPaymentHelper
                        from bonus.refferral_tree import ReferralTreeHelper
                        
                        print("🔄 Starting 20-level bonus processing...")
                        
                        # 1. Check if we can process bonuses for this purchase
                        can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
                        
                        if not can_process:
                            print(f"⚠️ Bonus processing skipped: {process_message}")
                            return jsonify({"status": "ok", "bonus_status": "skipped", "message": process_message}), 200
                        else:
                            print("✅ Pre-validation passed, calculating multi-level bonuses...")
                            
                            # 2. Calculate bonuses
                            success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
                            
                            if not success and not bonus_calculations:
                                print(f"❌ Bonus calculation failed: {calc_message}")
                                BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                                return jsonify({"status": "ok", "bonus_status": "calculation_failed", "message": calc_message}), 200
                            else:
                                print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated")
                                
                                # 3. Validate bonuses
                                valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
                                
                                print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
                                
                                # 4. Store valid bonuses
                                bonus_ids = []
                                if valid_bonuses:
                                    for bonus_data in valid_bonuses:
                                        bonus = ReferralBonus(**bonus_data)
                                        db.session.add(bonus)
                                        db.session.flush()
                                        bonus_ids.append(bonus.id)
                                    
                                    db.session.commit()
                                    
                                    # 5. Queue for payout
                                    for bonus_id in bonus_ids:
                                        BonusPaymentHelper.queue_bonus_payout(bonus_id)
                                    
                                    total_bonus_amount = sum(Decimal(str(b['amount'])) for b in valid_bonuses)
                                    print(f"🎉 Successfully created {len(valid_bonuses)} bonus records!")
                                    
                                    BonusValidationHelper.cleanup_processing_flag(payment.id, success=True)
                                    return jsonify({
                                        "status": "ok", 
                                        "bonus_status": "success",
                                        "bonuses_created": len(valid_bonuses),
                                        "levels": len(set(b['level'] for b in valid_bonuses)),
                                        "total_amount": str(total_bonus_amount)
                                    }), 200
                                else:
                                    print("ℹ️ No valid bonuses to create")
                                    BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                                    return jsonify({"status": "ok", "bonus_status": "no_valid_bonuses"}), 200

                    except Exception as e:
                        BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                        logger.error(f"Multi-level bonus distribution failed: {e}")
                        print(f"❌ Multi-level bonus error: {e}")
                        return jsonify({"status": "ok", "bonus_status": "error", "message": str(e)}), 200
        
        elif payment.payment_type == "deposit":
            user = User.query.get(payment.user_id)
            if user:
                user.actual_balance += payment.amount
                print(f"Deposit completed: Added {payment.amount} to user {user.id} actual balance")
                db.session.commit()
                return jsonify({"status": "ok", "message": "Deposit processed"}), 200
    
    else:
        # Handle failed payments
        print(f"❌ Payment failed with status: {status}")
        payment.status = PaymentStatus.FAILED.value
        payment.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "ok", "message": "Payment marked as failed"}), 200
    
    return jsonify({"status": "ok"}), 200
@bp.route("/payments/initiate", methods=['POST'])
def initiate_payment():
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
        package_id = package_obj.id if package_obj else None

        # FIX: Validate that package exists for package payments
        if payment_type == "package" and not package_obj:
            return jsonify({"error": "Package not found"}), 400

        payment = None

        if payment_type == "package":
            # FIX: Check for existing payments first (for both internal and external)
            existing_response = handle_existing_payment(user, amount, payment_type)
            if existing_response:
                return existing_response

            # Internal balance payment
            if user.actual_balance >= package_obj.amount:
                user.actual_balance -= package_obj.amount

                payment = create_payment_record(
                    user, amount, phone, payment_type, package=package_obj
                )
                if not payment:
                    return jsonify({"error": "Failed to create payment record"}), 500
                    
                payment.status = PaymentStatus.COMPLETED.value
                payment.raw_response = json.dumps({"method": "internal_balance"})
                payment.balance_type_used = "actual_balance" 
                
                db.session.add(payment)
                db.session.flush() 
            
                new_package = Package(
                    user_id=user.id,
                    catalog_id=package_obj.id,
                    package=package_obj.name,
                    type="purchased",
                    status='active',
                    activated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=package_obj.duration_days)
                )
                db.session.add(new_package)
            
                try:
                    print(f"Processing referral bonus for internal balance package purchase: {payment.id}")
                    #distribute_referral_bonus(payment, db.session)
                except Exception as e:
                    logger.error(f"Bonus distribution failed for internal payment: {e}")
                
                db.session.commit()
                
                return jsonify({
                    "reference": payment.reference,
                    "status": PaymentStatus.COMPLETED.value,
                    "payment_type": payment_type,
                    "package": package_id,
                    "message": "Package purchased using account balance",
                    "new_actual_balance": user.actual_balance,
                    "available_balance": user.available_balance,
                    "referral_bonus_processed": True  
                }), 200
            
            else:
                # External payment for insufficient balance
                payment = create_payment_record(user, amount, phone, payment_type, package=package_obj)
                if not payment:
                    return jsonify({"error": "Failed to create payment record"}), 500

                # FIX: Ensure send_to_marzpay returns proper format
                marz_response = send_to_marzpay(payment, phone, amount, package_obj)
                if isinstance(marz_response, tuple) and len(marz_response) == 2:
                    marz_data, error = send_to_marzpay(payment, phone, amount, package_obj)
                    if error:
                        # Update payment status to failed
                        payment.status = PaymentStatus.FAILED.value
                        db.session.commit()
                        return error
                    db.session.commit()

                    return jsonify({
                        "reference": payment.reference,
                        "status": payment.status,  # Use the status set by send_to_marzpay
                        "payment_type": payment_type,
                        "package": package_id,
                        "checkout_url": marz_data.get("checkout_url") if marz_data else None
                    }), 200
                else:
                    # Handle case where function doesn't return tuple
                    payment.status = PaymentStatus.FAILED.value
                    db.session.commit()
                    return jsonify({"error": "Invalid response from payment gateway"}), 500

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
                "checkout_url": marz_data.get("checkout_url") if marz_data else None,
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
#@bp.route("/payments/callback", methods=['POST'])
#def payment_callback():
    print("=== MARZ CALLBACK TRIGGERED ===") 
    print(f"Payment ID: {payment.id if payment else 'None'}")
    print(f"Payment Status: {payment.status if payment else 'None'}")
    print(f"Payment Type: {payment.payment_type if payment else 'None'}")
    print(f"Callback Status: {status}")
        
    
    data = request.get_json(silent=True) or {}
    if not data:
       
        return jsonify({"error": "No JSON data"}), 400

    transaction = data.get("transaction", {})
    status = transaction.get("status", "completed").lower()
  
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
        return jsonify({"status": "ignored"}), 200
    
    if not payment:
        print(f"No matching payment for reference {reference} / ext {ext_uuid}")
        return jsonify({"status": "ignored"}), 200
    # Process NEW successful payments
    if status in ("success", "completed", "paid", "sandbox"):
        print("🔄 Processing new successful payment...")
        
        # Update payment status to completed
        payment.status = PaymentStatus.COMPLETED.value
        payment.verified = True
        payment.updated_at = datetime.utcnow()
        payment.provider = data.get("transaction", {}).get("provider")
        payment.external_ref = data.get("transaction", {}).get("uuid")
        payment.raw_response = json.dumps(data)
        payment.provider_reference = transaction.get("provider_reference")
        
        db.session.commit()  # Commit payment status first
        
        # NOW process package and bonuses
        if payment.payment_type == "package":
            print("🎯 Starting package and bonus processing...")
            
            description = (
                data.get("transaction", {}).get("description") or
                data.get("description", "")
            )
            package = None
            if "payment_for_" in description:
                package = description.replace("payment_for_", "").strip()
                package_catalog = PackageCatalog.query.filter(
                    db.func.lower(PackageCatalog.name) == package.lower()
                ).first()
                
            print(f"Extracted package name: {package}")
            if payment.user_id and package:
                user = User.query.get(payment.user_id)
                
                print(f"Payment user_id: {payment.user_id}")
                if user:
                    package_catalog = PackageCatalog.query.filter_by(name=package).first()
                print(f"Package catalog found: {package_catalog}")
                if package_catalog:
                    print(f"Package catalog ID: {package_catalog.id}, Duration: {package_catalog.duration_days}")
                    
                    new_package = Package(
                        user_id = user.id,
                        catalog_id = package_catalog.id,
                        package=package_catalog.name,
                        type="purchased",
                        status='active',
                        activated_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=package_catalog.duration_days)
                    )
                    db.session.add(new_package)
                    db.session.commit()

                    # NOW process bonuses (your existing bonus code here)
                    # COMPLETE MULTI-LEVEL BONUS PROCESSING - REPLACING OLD DIRECT REFERRAL
                    try:
                        # Fix the imports - use the correct module names from your snippets
                        from bonus.validation import BonusValidationHelper
                        from bonus.bonus_calculation import BonusCalculationHelper
                        from bonus.bonus_payment import BonusPaymentHelper
                        from bonus.refferral_tree import ReferralTreeHelper
                        
                        print("🔄 Starting 20-level bonus processing...")
                        
                        # 1. Check if we can process bonuses for this purchase (with locking)
                        can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
                        
                        if not can_process:
                            print(f"⚠️ Bonus processing skipped: {process_message}")
                            current_app.logger.warning(f"Bonus processing skipped for payment {payment.id}: {process_message}")
                            return jsonify({"status": "ok"}), 200  # ADD THIS RETURN
                        else:
                            print("✅ Pre-validation passed, calculating multi-level bonuses...")
                            
                            # 2. Calculate bonuses for all 20 levels (includes internal validation)
                            success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
                            
                            if not success and not bonus_calculations:
                                print(f"❌ Bonus calculation failed: {calc_message}")
                                current_app.logger.error(f"Bonus calculation failed for payment {payment.id}: {calc_message}")
                                
                                # Still cleanup processing flag even on failure
                                BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                                return jsonify({"status": "ok"}), 200  # ADD THIS RETURN
                            else:
                                print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated across {audit_info.get('eligible_ancestors', 0)} levels")
                                
                                # 3. Validate the calculated bonuses
                                valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
                                
                                print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
                                
                                # 4. Store valid bonuses
                                bonus_ids = []
                                if valid_bonuses:
                                    for bonus_data in valid_bonuses:
                                        bonus = ReferralBonus(**bonus_data)
                                        db.session.add(bonus)
                                        db.session.flush()  # Get the bonus ID
                                        bonus_ids.append(bonus.id)
                                    
                                    db.session.commit()
                                    
                                    # 5. Queue bonuses for payment processing
                                    for bonus_id in bonus_ids:
                                        BonusPaymentHelper.queue_bonus_payout(bonus_id)
                                    
                                    # 6. Log successful processing
                                    total_bonus_amount = sum(Decimal(str(b['amount'])) for b in valid_bonuses)
                                    current_app.logger.info(
                                        f"Multi-level bonuses processed for payment {payment.id}: "
                                        f"{len(valid_bonuses)} valid bonuses created across {len(set(b['level'] for b in valid_bonuses))} levels, "
                                        f"Total amount: {total_bonus_amount}"
                                    )
                                    
                                    print(f"🎉 Successfully created {len(valid_bonuses)} bonus records across {len(set(b['level'] for b in valid_bonuses))} levels!")
                                else:
                                    print("ℹ️ No valid bonuses to create")
                                
                                # 7. Log invalid bonuses for investigation
                                if invalid_bonuses:
                                    current_app.logger.warning(
                                        f"Invalid bonuses for payment {payment.id}: {len(invalid_bonuses)} records failed validation"
                                    )
                                
                                # 8. Cleanup processing flag
                                BonusValidationHelper.cleanup_processing_flag(payment.id, success=len(valid_bonuses) > 0)
                                
                                return jsonify({"status": "ok"}), 200  # ADD THIS RETURN

                    except Exception as e:
                        # Critical error handling - cleanup processing flag
                        BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                        logger.error(f"Multi-level bonus distribution failed: {e}")
                        print(f"❌ Multi-level bonus error: {e}")
                        # Return 200 even on error so Marz doesn't retry
                        return jsonify({"status": "ok"}), 200
#     if payment.status == PaymentStatus.COMPLETED.value:
        
#         print("Payment already processed:", payment.reference)
#         if payment.payment_type == "package":
#             try:
#                if status in ("success", "completed", "paid", "sandbox"):
#                 print("🔄 Processing new successful payment...")
#                 payment.status = PaymentStatus.COMPLETED.value
#                 payment.verified = True
#                # distribute_referral_bonus(payment, db.session)

#                else:
#                 payment.status = PaymentStatus.FAILED.value

#             except Exception as e:
#                   logger.error(f"Bonus distribution failed: {e}")
        
#             payment.updated_at = datetime.utcnow()
#             payment.provider = data.get("transaction", {}).get("provider")
#             payment.external_ref = data.get("transaction", {}).get("uuid")
#             payment.raw_response = json.dumps(data)
#             payment.provider_reference = transaction.get("provider_reference")

#             db.session.commit()
#             description = (
#                 data.get("transaction", {}).get("description") or
#                 data.get("description", "")
#             )
#             package = None
#             if "payment_for_" in description:
#                 package = description.replace("payment_for_", "").strip()
#                 package_catalog = PackageCatalog.query.filter(
#                 db.func.lower(PackageCatalog.name) == package.lower()
#             ).first()
#             print(f"Extracted package name: {package}")
#             if payment.user_id and package:
#                 user = User.query.get(payment.user_id)
                
#                 print(f"Payment user_id: {payment.user_id}")
#                 if user:
#                    package_catalog = PackageCatalog.query.filter_by(name=package).first()
#                 print(f"Package catalog found: {package_catalog}")
#                 if package_catalog:
#                     print(f"Package catalog ID: {package_catalog.id}, Duration: {package_catalog.duration_days}")
                
#                     new_package = Package(
#                         user_id = user.id,
#                         catalog_id = package_catalog.id,
#                         package=package_catalog.name,
#                         type="purchased",
#                         status='active',
#                         activated_at=datetime.utcnow(),
#                         expires_at=datetime.utcnow() + timedelta(days=package_catalog.duration_days)
#                         )
#                     db.session.add(new_package)
#                     db.session.commit()

#                     # ... after package creation and commit (around line 279) ...

# # COMPLETE MULTI-LEVEL BONUS PROCESSING - REPLACING OLD DIRECT REFERRAL
#                 try:
#                     from bonus.validation import BonusValidationHelper
#                     from bonus.bonus_calculation import BonusCalculationHelper
#                     from bonus.bonus_payment import BonusPaymentHelper
#                     from bonus.refferral_tree import ReferralTreeHelper
#                     print("🔄 Starting 20-level bonus processing...")
                    
#                     # 1. Check if we can process bonuses for this purchase (with locking)
#                     can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
                    
#                     if not can_process:
#                         print(f"⚠️ Bonus processing skipped: {process_message}")
#                         current_app.logger.warning(f"Bonus processing skipped for payment {payment.id}: {process_message}")
#                     else:
#                         print("✅ Pre-validation passed, calculating multi-level bonuses...")
                        
#                         # 2. Calculate bonuses for all 20 levels (includes internal validation)
#                         success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
                        
#                         if not success and not bonus_calculations:
#                             print(f"❌ Bonus calculation failed: {calc_message}")
#                             current_app.logger.error(f"Bonus calculation failed for payment {payment.id}: {calc_message}")
                            
#                             # Still cleanup processing flag even on failure
#                             BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#                         else:
#                             print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated across {audit_info.get('eligible_ancestors', 0)} levels")
                            
#                             # 3. Validate the calculated bonuses
#                             valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
                            
#                             print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
                            
#                             # 4. Store valid bonuses
#                             bonus_ids = []
#                             if valid_bonuses:
#                                 for bonus_data in valid_bonuses:
#                                     bonus = ReferralBonus(**bonus_data)
#                                     db.session.add(bonus)
#                                     db.session.flush()  # Get the bonus ID
#                                     bonus_ids.append(bonus.id)
                                
#                                 db.session.commit()
                                
#                                 # 5. Queue bonuses for payment processing
#                                 for bonus_id in bonus_ids:
#                                     BonusPaymentHelper.queue_bonus_payout(bonus_id)
                                
#                                 # 6. Log successful processing
#                                 total_bonus_amount = sum(Decimal(str(b['amount'])) for b in valid_bonuses)
#                                 current_app.logger.info(
#                                     f"Multi-level bonuses processed for payment {payment.id}: "
#                                     f"{len(valid_bonuses)} valid bonuses created across {len(set(b['level'] for b in valid_bonuses))} levels, "
#                                     f"Total amount: {total_bonus_amount}"
#                                 )
                                
#                                 print(f"🎉 Successfully created {len(valid_bonuses)} bonus records across {len(set(b['level'] for b in valid_bonuses))} levels!")
#                             else:
#                                 print("ℹ️ No valid bonuses to create")
                            
#                             # 7. Log invalid bonuses for investigation
#                             if invalid_bonuses:
#                                 current_app.logger.warning(
#                                     f"Invalid bonuses for payment {payment.id}: {len(invalid_bonuses)} records failed validation"
#                                 )
#                                 # Log first few errors for debugging
#                                 for invalid in invalid_bonuses[:5]:
#                                     current_app.logger.debug(
#                                         f"Invalid bonus - User: {invalid.get('ancestor_id')}, "
#                                         f"Level: {invalid.get('level')}, "
#                                         f"Error: {invalid.get('validation_error', 'Unknown error')}"
#                                     )
                            
#                             # 8. Cleanup processing flag
#                             BonusValidationHelper.cleanup_processing_flag(payment.id, success=len(valid_bonuses) > 0)

#                 except Exception as e:
#                     # Critical error handling - cleanup processing flag
#                     BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#                     logger.error(f"Multi-level bonus distribution failed: {e}")
#                     print(f"❌ Multi-level bonus error: {e}")
#                     # Don't re-raise - package creation should not be affected by bonus errors
#                     return jsonify({"status": "ok"}), 200
#         elif payment.payment_type == "deposit":
           
#             user = User.query.get(payment.user_id)
#             if user:
#                 user.actual_balance += payment.amount
#                 print(f"Deposit completed: Added {payment.amount} to user {user.id} actual balance")
#                 db.session.commit()
    
#     return jsonify({"status": "ok"}), 200
#========================================================================================================================
#=======================================================================================================================    
#============================================================================
#      WITHDRAWAL ENDPOINT
#============================================================================

@bp.route("/payments/withdraw", methods=["POST"])
def withdraw():
    if not request.is_json:
         return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    amount = data.get("amount")
    phone = data.get("phone") or data.get("phone_number")
    narration = data.get("narration", "Cash Out")

    if not amount or not phone:
        return jsonify({"error": "Amount and phone number are required"}), 400

    try:
        amount = Decimal(amount)
    except:
        return jsonify({"error": "Invalid amount format"}), 400

    if amount < 5000:
        return jsonify({"error": "Minimum withdrawal is UGX 5,000"}), 400

   
    phone_regex = re.compile(r"^\+2567\d{8}$")
    if not phone_regex.match(phone):
        return jsonify({"error": "Invalid phone number"}), 400


    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    merchant_reference = str(uuid.uuid4())

    withdrawal = Withdrawal(
        user_id=user.id,
        amount=float(amount),
        phone=phone,
        status="pending",
        transaction_id=None
    )

    db.session.add(withdrawal)
    db.session.commit()

    CALL_BACK_URL = "https://bedfast-kamron-nondeclivitous.ngrok-free.dev/withdraw/callback"
    
    payload = {
        "reference": str(merchant_reference),
        "amount": int(amount),
        "phone_number": f"+256{phone.strip()[-9:]}",  
        "country": "UG",
        "description": "customer_withdraw",
        "callback_url": CALL_BACK_URL,

    }
    headers = {
        "Authorization": f"Basic {os.environ.get('MARZ_AUTH_HEADER')}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(f"{MARZ_BASE_URL}/send-money", json=payload, headers=headers, timeout=10)
        print("MarzPay response status:", response.status_code, "body:", response.text, flush=True)
        response.raise_for_status()
        marz_data = response.json()

       
        return jsonify({
        "message": "Withdrawal request created successfully",
        "withdrawal_id": withdrawal.id,
        "marz_response": marz_data
    }), 200

    except requests.exceptions.RequestException as e:
        print("MarzPay request error:", str(e), flush=True)
        
        return jsonify({
        "error": "Gateway failed",
        "details": str(e)
    }), 502  
#=====================================================================================================
#
#-----------------WITHDRAW CALLBACK ENDPOINT------------------------------------

@bp.route('/withdraw/callback', methods=['POST'])
def withdraw_callback():
    try:
        # Get the callback data from Marz
        callback_data = request.get_json()
        
        if not callback_data:
            return jsonify({"error": "No JSON data received"}), 400
        
        # Extract relevant data from callback
        marz_reference = callback_data.get('reference')
        marz_status = callback_data.get('status')
        marz_amount = callback_data.get('amount')
        
        if not marz_reference:
            return jsonify({"error": "Missing reference in callback"}), 400
        
        print(f"Callback received - Reference: {marz_reference}, Status: {marz_status}, Amount: {marz_amount}", flush=True)
        
        # Find the withdrawal with the matching reference
        withdrawal = Withdrawal.query.filter(
            and_(
                Withdrawal.merchant_reference == marz_reference,
                Withdrawal.status == 'pending'
            )
        ).first()
        
        if not withdrawal:
            print(f"Withdrawal not found for reference: {marz_reference}", flush=True)
            return jsonify({"error": "Withdrawal not found"}), 404
        
        # Update withdrawal status based on Marz response
        if marz_status == 'success' or marz_status == 'completed':
            # Get the user associated with this withdrawal
            user = User.query.get(withdrawal.user_id)
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            
            # Check if user has sufficient balance
            if user.balance < withdrawal.amount:
                withdrawal.status = 'failed'
                withdrawal.note = 'Insufficient balance'
                db.session.commit()
                return jsonify({"error": "Insufficient balance"}), 400
            
            # Deduct the amount from user's balance
            user.balance -= withdrawal.amount
            
            # Update withdrawal status
            withdrawal.status = 'completed'
            withdrawal.transaction_id = callback_data.get('transaction_id')
            
            db.session.commit()
            
            return jsonify({
                "message": "Callback processed successfully",
                "status": "completed",
                "user_id": user.id,
                "amount_deducted": withdrawal.amount,
                "new_balance": user.balance
            }), 200
        
        elif marz_status == 'failed':
            # Update withdrawal status to failed
            withdrawal.status = 'failed'
            withdrawal.note = f"Failed by provider: {callback_data.get('reason', 'Unknown reason')}"
            db.session.commit()
            
            print(f"Withdrawal failed - Reference: {marz_reference}, Reason: {callback_data.get('reason', 'Unknown')}", flush=True)
            
            return jsonify({
                "message": "Withdrawal marked as failed",
                "status": "failed"
            }), 200
        
        else:
            # Handle other statuses (pending, processing, etc.)
            withdrawal.status = marz_status
            db.session.commit()
            
            return jsonify({
                "message": f"Withdrawal status updated to {marz_status}",
                "status": marz_status
            }), 200
            
    except Exception as e:
        print(f"Error processing callback: {str(e)}", flush=True)
        db.session.rollback()
        return jsonify({"error": "Internal server error processing callback"}), 500