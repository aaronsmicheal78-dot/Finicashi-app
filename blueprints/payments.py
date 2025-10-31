
# we initiate payments and call Marz Pay
# blueprints/payments.py - Handles payment initiation, status checks, and webhook processing
from flask import Blueprint, request, jsonify, current_app, session, url_for             # Flask essentials                                                        # HTTP client to call Marz
import uuid                                                          # for generating unique references
from extensions import db, logger, sess                             # DB session factory & logger
from models import Payment, PaymentStatus, User                           # DB models
from utils import safe_marz_headers, verify_webhook_signature           # helper utilities
from sqlalchemy.exc import IntegrityError                               # DB error handling
from sqlalchemy import select                                            # query helper
from sqlalchemy.orm import Session   
import re
import hmac
import hashlib   
import json
import requests 
from blueprints.payment_webhooks import SessionLocal 
  


bp = Blueprint("payments", __name__, url_prefix="/api")  

PACKAGE_MAP = {
    10000: "Bronze",
    20000: "Silver",
    50000: "Gold",
    100000: "Diamond",
    200000: "Platinum",
    500000: "Ultimate"
}

MARZ_API_BASE = current_app.config.get("MARZ_BASE_URL")
MARZ_API_KEY = current_app.config.get("MARZ_API_KEY")
MARZ_SECRET = current_app.config.get("MARZ_SECRET")


def generate_hmac_signature(payload: dict, secret: str) -> str:
    """
    Generate HMAC SHA256 signature for Marz API
    - Payload is converted to JSON string with no whitespace
    - Secret is the Marz secret key
    """
    body_json = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    signature = hmac.new(secret.encode(), body_json.encode(), hashlib.sha256).hexdigest()
    return signature, body_json


@bp.route("/initiate", methods=["POST"])
def initiate_payment():
    # 1️⃣ Validate logged-in user
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 2️⃣ Parse payload
    payload = request.get_json(force=True)
    amount = payload.get("amount")
    phone = payload.get("phone_number")
    description = payload.get("description", "")

    # 3️⃣ Validate amount
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid amount"}), 400
    if amount not in PACKAGE_MAP:
        return jsonify({"error": "Amount does not match any package"}), 400

    # 4️⃣ Validate phone
    if not phone or not isinstance(phone, str):
        return jsonify({"error": "Missing phone number"}), 400
    phone = phone.strip()
    if not re.fullmatch(r"(?:\+256|0)\d{9}", phone):
        return jsonify({"error": "Invalid phone number"}), 400

    # 5️⃣ Generate merchant reference
    merchant_reference = str(uuid.uuid4())

    # 6️⃣ Create pending payment record
    try:
        payment = Payment(
            user_id=user.id,
            reference=merchant_reference,
            amount=amount,
            currency="UGX",
            phone_number=phone,
            description=description,
            status=PaymentStatus.PENDING
        )
        db.session.add(payment)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = Payment.query.filter_by(reference=merchant_reference).first()
        return jsonify({
            "reference": existing.reference,
            "status": existing.status.value,
            "note": "Idempotent - existing record returned"
        }), 200
    except Exception as ex:
        db.session.rollback()
        logger.exception("Failed to create payment record: %s", ex)
        return jsonify({"error": "Internal server error"}), 500

    # 7️⃣ Prepare payload for Marz
    marz_payload = {
        "phone_number": phone,
        "amount": str(amount),
        "country": "UG",
        "reference": merchant_reference,
        "description": description,
        "callback_url": payload.get("callback_url") or f"{current_app.config.get('APP_BASE_URL')}/api/payments/webhook",
        "metadata": {
            "user_id": user.id,
            "package": PACKAGE_MAP[amount]
        }
    }

    # 8️⃣ Generate HMAC signature
    signature, body_json = generate_hmac_signature(marz_payload, MARZ_SECRET)

    headers = {
        "Content-Type": "application/json",
        "Api-Key": MARZ_API_KEY,
        "Signature": signature,          #  Marz server verifies this
        "Idempotency-Key": merchant_reference
    }

    # 9️⃣ Call Marz API
    try:
        resp = requests.post(
            f"{MARZ_API_BASE.rstrip('/')}/collect-money",
            data=body_json,
            headers=headers,
            timeout=15
        )
        resp.raise_for_status()
        marz_data = resp.json()
    except requests.RequestException as e:
        logger.exception("Marz API request failed: %s", e)
        payment.status = PaymentStatus.FAILED
        payment.raw_response = str(e)
        db.session.commit()
        return jsonify({"error": "Payment provider error"}), 502

    # 10️⃣ Save response
    payment.raw_response = json.dumps(marz_data)
    payment.gateway_id = marz_data.get("transaction_id") or marz_data.get("id")
    payment.gateway_status = marz_data.get("status")
    db.session.commit()

    # 11️⃣ Return to client
    checkout_url = marz_data.get("checkout_url") or marz_data.get("redirect_url")
    return jsonify({
        "reference": merchant_reference,
        "status": "pending",
        "package": PACKAGE_MAP[amount],
        "checkout_url": checkout_url,
        "marz_response": marz_data
    }), 200


# Webhook endpoint that Marz will call asynchronously
@bp.route("/webhook", methods=["POST"])
def webhook_handler():
    """
    POST /api/payments/webhook
    This endpoint handles asynchronous events from Marz (payment.success, payment.failed, etc).
    Security:
      - Verifies HMAC signature using WEBHOOK_SECRET and timestamp header
      - Uses idempotency via payment reference to avoid re-processing retries
    """
    raw_body = request.get_data()                                         # raw bytes required for signature validation
    headers = {k: v for k, v in request.headers.items()}                  # capture headers for verification

    # signature verification (reject early if required)
    if current_app.config.get("REQUIRE_WEBHOOK_SIGNATURE", True):
        if not verify_webhook_signature(raw_body, headers):
            logger.warning("Webhook signature verification failed; returning 400")
            return jsonify({"error": "invalid signature"}), 400

    # parse JSON after verifying signature (helps avoid processing false payloads)
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


# Query endpoint for merchant to check status (or for your frontend)
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
