#======================================================================================================
#
#   PAYMENT API BLUEPRINT FOR MARZ PAYMENT GATEWAY INTEGRATION
#
#===========================================================================================================
from flask import Blueprint, request, jsonify, current_app, session, url_for, current_app                                                                   # HTTP client to call Marz
import uuid                                                                              
from models import Payment, PaymentStatus, User                        
from utils import validate_phone, validate_email, get_marz_authorization_header      
from sqlalchemy.exc import IntegrityError                             
from sqlalchemy import select                                          
from sqlalchemy.orm import Session   
import re  
import json
import requests 
from extensions import db
#from blueprints.payment_webhooks import SessionLocal 
import os
from datetime import datetime, timedelta
import base64
import logging
from flask_login import current_user, login_required
from decimal import Decimal
from blueprints.payments_helpers import send_withdraw_request

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
@bp.route('/payments/initiate/', methods=['POST'])
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
    #   package=package,
       status=PaymentStatus.PENDING
    ).first()
  
    if existing_payment:
        return jsonify({
        "reference": existing_payment.reference,
        "status": existing_payment.status.value,
        "note": "Idempotent: existing record returned"}), 200
  

    payment = Payment(
        user_id=user.id,
        reference=merchant_reference,
        amount=amount,
        currency="UGX",
        phone_number=phone,
    #    package=package,
        status=PaymentStatus.PENDING
        )
    db.session.add(payment)
    db.session.commit()
    

    headers = {
        "Authorization": get_marz_authorization_header(),
        "Content-Type": "application/json",}
    
    callback_url = f"{current_app.config.get('APP_BASE_URL')}/payments/webhook"
    marz_payload = {
        "phone_number": phone,
        "amount": str(amount),
        "currency": "UGX",
        "reference": merchant_reference,
        "callback_url": callback_url,
        "metadata": {
            "user_id": user.id,
            "package": package
        }       
    }
 
  
    try:
        resp = requests.post(
            f"{MARZ_BASE_URL}/collect-money",
            json=marz_payload,
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        marz_data = resp.json()
    except requests.RequestException as e:
        payment.status = PaymentStatus.FAILED
        payment.raw_response = str(e)
        db.session.commit()
        return jsonify({"error": "Payment provider error"}), 502

    # Update payment record with gateway response
    payment.payment_id = marz_data.get("transaction_id")
    payment.payment_status = marz_data.get("status")
    payment.raw_response = json.dumps(marz_data)
    db.session.commit()

    # Return checkout URL to frontend
    checkout_url = marz_data.get("checkout_url")
    return jsonify({
        "reference": merchant_reference,
        "status": "pending",
        "package": package,
        "checkout_url": checkout_url
    }), 200

#============================================================================
#      PAYMENT WEBHOOK ENDPOINT
#============================================================================
@bp.route("/payments/webhook", methods=["POST"])
def webhook_handler():
    """
    POST /payments/webhook
    This endpoint handles asynchronous events from Marz (payment.success, payment.failed, etc).
    Security:
      - Verifies HMAC signature using WEBHOOK_SECRET and timestamp header
      - Uses idempotency via payment reference to avoid re-processing retries
    """
    raw_body = request.get_data()                                         
    headers = {k: v for k, v in request.headers.items()}                  

    try:
        data = request.get_json(force=True)
    except Exception as ex:
        logger.exception("Invalid JSON on webhook payload: %s", ex)
        return jsonify({"error": "invalid json"}), 400

    # Example payload fields: {'reference': 'ref', 'status': 'success', 'transaction_id': 'tx123', ...}
    reference = data.get("reference") or (data.get("data") and data["data"].get("reference"))  # be flexible
    status_text = data.get("status") or (data.get("data") and data["data"].get("status"))

    if not reference:
        logger.warning("Webhook missing reference; ignoring. payload=%s", data)
        return jsonify({"error": "missing reference"}), 400

    # idempotent update: fetch by reference and apply state transitions only once
    db = SessionLocal()
    try:
        record = db.execute(select(Payment).filter_by(reference=reference)).scalar_one_or_none()
        if record is None:
            # if we do not have a record, we can optionally create one as 'unknown origin' or return 404
            logger.warning("Received webhook for unknown reference %s - creating audit record", reference)
            # create a minimal audit record to avoid losing info
            record = Payment(
                reference=reference,
                amount=float(data.get("amount", 0.0)),
                currency=data.get("currency", "UGX"),
                phone_number=data.get("phone_number"),
                status=PaymentStatus.PENDING,
                raw_response=str(data)
            )
            db.add(record)
            db.commit()
            # reload record
            record = db.execute(select(Payment).filter_by(reference=reference)).scalar_one()

        # Determine target status and idempotently update (only transition from pending -> final states)
        if record.status == PaymentStatus.SUCCESS:
            logger.info("Webhook for reference %s ignored: already success", reference)
            return jsonify({"status": "already_processed"}), 200

        # map provider status to our enum (example mapping, adapt if Marz uses different values)
        if status_text and status_text.lower() in ("success", "completed", "paid"):
            record.status = PaymentStatus.SUCCESS
        elif status_text and status_text.lower() in ("failed", "declined"):
            record.status = PaymentStatus.FAILED
        else:
            # if ambiguous, leave pending but store raw payload
            record.raw_response = str(data)
            db.commit()
            logger.info("Webhook for %s left as pending (ambiguous status: %s)", reference, status_text)
            return jsonify({"status": "pending"}), 200

        # store Marz's transaction id if present for reconciliation
        txid = data.get("transaction_id") or (data.get("data") and data["data"].get("transaction_id"))
        if txid:
            record.marz_transaction_id = txid
        record.raw_response = str(data)                                      # save full payload for audits
        db.commit()                                                          # persist state change
        logger.info("Webhook processed: reference=%s new_status=%s", reference, record.status.value)
    except Exception as e:
        db.rollback()
        logger.exception("Error processing webhook for %s: %s", reference, e)
        return jsonify({"error": "processing error"}), 500
    finally:
        db.close()

    # respond 200 to acknowledge receipt to Marz
    return jsonify({"status": "ok"}), 200

#============================================================================
#      PAYMENT STATUS CHECK ENDPOINT
#============================================================================

@bp.route("/status/<reference>", methods=["GET"])
def check_status(reference):
    """
    GET /api/payments/status/<reference>
    Returns local status for the given merchant reference and optionally queries Marz for reconciliation.
    This should be used by the frontend to show final status to the user.
    """
    db = SessionLocal()
    try:
        record = db.execute(select(Payment).filter_by(reference=reference)).scalar_one_or_none()
        if not record:
            return jsonify({"error": "not_found"}), 404
        # option: return local DB status; if you want live status, you may call Marz transactions endpoint
        return jsonify({
            "reference": record.reference,
            "status": record.status.value,
            "marz_transaction_id": record.marz_transaction_id,
            "raw_response": record.raw_response
        }), 200
    finally:
        db.close()

#============================================================================
#      WITHDRAWAL ENDPOINT
#============================================================================

@bp.route("/payments/withdraw", methods=["POST"])
@login_required
def withdraw():
 
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    amount = data.get("amount")
    phone = data.get("phone")

   
    if not amount or not phone:
        return jsonify({"error": "Amount and phone number are required"}), 400

    try:
        amount = Decimal(amount)
    except:
        return jsonify({"error": "Invalid amount format"}), 400

    if amount <= 5000:
        return jsonify({"error": "Withdrawal amount must be positive"}), 400


    user_id = session.get("user_id") or getattr(current_user, "id", None)
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404


    if user.balance is None or user.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

 
    withdraw_request = {
        "user_id": user.id,
        "amount": float(amount),
        "phone": phone,
        "status": "pending"}
    
    user.balance -= amount
   
    db.session.add(withdraw_request)
    db.session.commit()

    marz_response = send_withdraw_request(withdraw_request)


    if not marz_response["success"]:
        return jsonify({"error": "Failed to send to MarzPay", "details": marz_response["error"]}), 502

    return jsonify({
        "message": "Withdrawal request sent successfully",
        "withdraw_id": withdraw_request.id,
        "marz_response": marz_response["response"]
    }), 200
    