#======================================================================================================
#
#   PAYMENT API BLUEPRINT FOR MARZ PAYMENT GATEWAY INTEGRATION
#
#===========================================================================================================
from flask import Blueprint, request, jsonify, current_app, session, url_for, current_app                                                                   # HTTP client to call Marz
import uuid                                                                              
from models import Payment, PaymentStatus, User, Withdrawal                      
from utils import validate_phone, validate_email, get_marz_authorization_header      
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
from flask_login import current_user, login_required, login_user
from decimal import Decimal
from blueprints.payments_helpers import send_withdraw_request
import sys


bp = Blueprint("payments", __name__)  
logger = logging.getLogger(__name__)


REQUEST_TIMEOUT_SECONDS = int(os.getenv('REQUEST_TIMEOUT_SECONDS', '15'))

MARZ_BASE_URL=('https://wallet.wearemarz.com/api/v1')

def deterministic_json(obj):
   """Return deterministic JSON string for signing: keys sorted, separators compact.
   Avoids variations between client/server serializations.
   """
   return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)

PACKAGE_MAP = {
    10000: "Bronze",
    20000: "Silver",
    50000: "Gold",
    100000: "Diamond",
    200000: "Platinum",
    500000: "Ultimate"
}
ALLOWED_AMOUNTS = set(PACKAGE_MAP.keys())

#=============================================================================================
#      PAYMENT INITIATION ENDPOINT
#=============================================================================================
@bp.route("/payments/initiate", methods=['POST'])
def initiate_payment():


    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
   
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    amount = data.get('amount')
    package = data.get('package', '').lower()
    phone = data.get('phone')
 
   
    if not all([amount, package, phone]):
       return jsonify({"error": "Missing fields"}), 400

    if amount not in ALLOWED_AMOUNTS:
       return jsonify({"error": "Invalid amount"}), 400
    
    expected_package = PACKAGE_MAP.get(amount).lower()
       
    if expected_package != package.lower():
       return jsonify({"error": "Invalid or mismatched package"}), 400
    if not re.match(r"^(?:\+256|0)?7\d{8}$", phone):
        return jsonify({"error": "Invalid phone number"}), 400
    
    merchant_reference = str(uuid.uuid4())
   
    existing_payment = Payment.query.filter_by(
       user_id=user.id,
       amount=amount,
       status=PaymentStatus.PENDING.value,
    ).first()
    print("Existing payment found:", existing_payment, flush=True)
    
    if existing_payment:
        return jsonify({
        "reference": existing_payment.reference,
        "status": existing_payment.status,
        "note": "Idempotent: existing record returned"}), 200
  
   
    payment = Payment(
    user_id=user.id,
    reference=merchant_reference,
    amount=amount,
    currency="UGX",
    phone_number=phone,
    provider=None,
    status="pending",  
    method="MarzPay",         
    external_ref=None,        
    idempotency_key=str(uuid.uuid4()), 
    raw_response=None,  
    )
    db.session.add(payment)
    db.session.commit()
    
    headers = {
        "Authorization": f"Basic {os.environ.get('MARZ_AUTH_HEADER')}",
        "Content-Type": "application/json",}
    
    callback_url = "https://bedfast-kamron-nondeclivitous.ngrok-free.dev/payments/callback"
    marz_payload = {
        "phone_number": f"+256{phone.lstrip('0')}",
        "amount": int(amount),
        "country": "UG",
        "reference": str(merchant_reference),
        "callback_url": callback_url,
        "description": f"payment_for_{package}" }   

     
    try:
        resp = requests.post(
            f"{MARZ_BASE_URL}/collect-money",
            json=marz_payload,
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        marz_data = resp.json()
        print("Sandbox MarzPay response:", marz_data, flush=True)

    except requests.RequestException as e:
       
        payment.status = PaymentStatus.failed
        payment.raw_response = json.dumps(marz_data)
        db.session.commit()
        return jsonify({"error": "Payment provider error"}), 502

    
    payment.payment_id = marz_data.get("transaction_id")
    payment.payment_status = marz_data.get("status")
    payment.raw_response = json.dumps(marz_data)
    db.session.commit()

   
    checkout_url = marz_data.get("checkout_url")
    return jsonify({
        "reference": merchant_reference,
        "status": "PENDING",
        "package": package,
        "checkout_url": checkout_url
    }), 200
#=======================================================================================================
#                   ------------------------------------------------------
#---------------------WEBHOOK CALLBACK ENDPOINT FOR PAYMENT INITIATION--------------------------------------
#=========================================================================================================
@bp.route("/payments/callback", methods=['POST'])
def payment_callback():
    data = request.get_json(silent=True) or {}

    transaction = data.get("transaction", {})
    status = transaction.get("status", "completed").lower() 
    reference = (
        data.get("transaction", {}).get("reference") or
        data.get("reference")
    )
    
    if not reference:
        return jsonify({"error": "Missing reference"}), 400

    payment = Payment.query.filter_by(status="pending").first()
    if not payment:
        return jsonify({"status": "ignored"}), 200
    
    if status == "completed":
        payment.status = PaymentStatus.COMPLETED.value
    else:
        payment.status = PaymentStatus.FAILED.value
        
    payment.updated_at = datetime.utcnow()
    payment.provider = data.get("transaction", {}).get("provider")
    payment.external_ref = data.get("transaction", {}).get("uuid")
    payment.raw_response = json.dumps(data)
    payment.provider_reference = transaction.get("provider_reference")

    db.session.commit()
    description = (
        data.get("transaction", {}).get("description") or
        data.get("description", "")
    )
    package = None
    if "payment_for_" in description:
        package = description.replace("payment_for_", "").strip()

    if payment.user_id and package:
        user = User.query.get(payment.user_id)
        if user:
            user.package = package
            db.session.commit()
        
    return jsonify({"status": "ok"}), 200
#========================================================================================================================
#=======================================================================================================================


#============================================================================
#      WITHDRAWAL ENDPOINT
#============================================================================

@bp.route("/payments/withdraw", methods=["POST"])
def withdraw():
    # if not request.is_json:
    #     return jsonify({"error": "Request must be JSON"}), 400

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

   
    # phone_regex = re.compile(r"^\+2567\d{8}$")
    # if not phone_regex.match(phone):
    #     return jsonify({"error": "Invalid phone number"}), 400


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
            
            print(f"Withdrawal completed successfully - User: {user.id}, Amount: {withdrawal.amount}, New Balance: {user.balance}", flush=True)
            
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