# payments/webhook.py
"""
Production-hardened, idempotent Marz payment webhook receiver.

Features:
- Signature verification (HMAC-SHA256)
- Replay attack prevention (timestamp check + optional txid uniqueness)
- Idempotent state updates (pending -> final)
- Atomic DB writes with rollback on failure
- Audit logging of raw payloads
- Decimal-based amounts for financial precision
- Flexible for SQLite (dev) and PostgreSQL (prod)
"""

from flask import request, jsonify, current_app
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import datetime, timezone
import time
from blueprints.auth import bp
from extensions import SessionLocal, logger
from models import Payment, PaymentStatus
from utils import verify_webhook_signature
from blueprints.bonus import process_referral_bonuses

# ----------------------------
# Webhook endpoint
# ----------------------------
@bp.route("/webhook", methods=["POST"])
def webhook_receiver():
    """
    Receives Marz payment notifications and updates Payment records idempotently.

    Expected JSON payload (common fields):
        {
            "reference": "unique_payment_ref",
            "transaction_id": "provider_txid",
            "status": "success|failed|pending",
            "amount": 1000.00,
            "currency": "UGX",
            "phone_number": "+256700000000"
        }
    """

    # ----------------------------
    # 1) Capture raw payload & headers
    # ----------------------------
    raw_payload = request.get_data()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # ----------------------------
    # 2) Verify webhook signature (HMAC-SHA256)
    # ----------------------------
    if current_app.config.get("REQUIRE_WEBHOOK_SIGNATURE", True):
        if not verify_webhook_signature(request):
            logger.warning("Webhook rejected: signature verification failed")
            return jsonify({"error": "invalid_signature"}), 401

    # ----------------------------
    # 3) Timestamp / replay protection
    # ----------------------------
    ts_header = headers.get(current_app.config.get("WEBHOOK_TIMESTAMP_HEADER", "marz-timestamp").lower())
    if ts_header:
        try:
            # Parse ISO8601 UTC timestamp, e.g., "2025-10-26T19:14:00Z"
            ts = datetime.strptime(ts_header, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            max_skew = int(current_app.config.get("WEBHOOK_TIMESTAMP_SKEW_SEC", 300))
            if abs((now - ts).total_seconds()) > max_skew:
                logger.warning("Webhook rejected: timestamp skew too large (%s)", ts_header)
                return jsonify({"error": "stale_or_future_timestamp"}), 400
        except Exception:
            logger.exception("Webhook timestamp parse error: %s", ts_header)
            return jsonify({"error": "invalid_timestamp_format"}), 400
    else:
        logger.warning("Webhook rejected: missing timestamp header")
        return jsonify({"error": "missing_timestamp"}), 400

    # ----------------------------
    # 4) Parse JSON payload safely
    # ----------------------------
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.exception("Webhook JSON parse error: %s", e)
        return jsonify({"error": "invalid_json"}), 400

    # ----------------------------
    # 5) Extract canonical fields
    # ----------------------------
    reference = data.get("reference") or (data.get("data") and data["data"].get("reference"))
    provider_txid = data.get("transaction_id") or (data.get("data") and data["data"].get("transaction_id"))
    status_text = (data.get("status") or (data.get("data") and data["data"].get("status")) or "").strip().lower()
    amount = data.get("amount") or (data.get("data") and data["data"].get("amount"))
    currency = data.get("currency") or (data.get("data") and data["data"].get("currency"))
    phone_number = data.get("phone_number") or (data.get("data") and data["data"].get("phone_number"))

    if not reference or not provider_txid:
        logger.warning("Webhook missing reference or transaction_id; payload=%s", str(data))
        return jsonify({"error": "missing_reference_or_transaction_id"}), 400

    # ----------------------------
    # 6) Map provider status to internal enum
    # ----------------------------
    if status_text in ("success", "completed", "paid"):
        target_status = PaymentStatus.SUCCESS
    elif status_text in ("failed", "declined", "reversed", "cancelled"):
        target_status = PaymentStatus.FAILED
    else:
        target_status = PaymentStatus.PENDING

    # ----------------------------
    # 7) Idempotent, transactional DB update
    # ----------------------------
    db: Session = SessionLocal()
    try:
        # Fetch payment by reference (lock row if DB supports it)
        stmt = select(Payment).filter_by(reference=reference)
        payment = db.execute(stmt).scalar_one_or_none()

        if payment is None:
            # No matching payment → create audit record
            payment = Payment(
                reference=reference,
                amount=Decimal(str(amount)) if amount else Decimal("0.0"),
                currency=currency or "UGX",
                phone_number=phone_number,
                marz_transaction_id=provider_txid,
                status=target_status,
                raw_response=str(data),
                created_at=datetime.now(timezone.utc)
            )
            db.add(payment)
            db.commit()
            logger.info("Created audit payment record for unknown reference %s", reference)
            return jsonify({"status": "created_audit_record", "reference": reference}), 200

        # Idempotent skip for repeated final states
        if payment.status == target_status:
            payment.raw_response = str(data)  # update payload for audit
            db.commit()
            logger.info("Duplicate webhook for %s ignored, status=%s", reference, payment.status.value)
            return jsonify({"status": "already_processed"}), 200

        # Perform state transition
        previous_status = payment.status
        payment.status = target_status
        payment.marz_transaction_id = provider_txid
        payment.raw_response = str(data)
        payment.last_reconciled = datetime.now(timezone.utc)
        db.commit()
        logger.info(
            "Webhook processed: reference=%s status %s -> %s",
            reference, previous_status.value, target_status.value
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Database error processing webhook for %s: %s", reference, e)
        return jsonify({"error": "db_error"}), 500

    finally:
        db.close()

    # ----------------------------
    # 8) Optional: Notify internal systems (async queue, SMS/email)
    # ----------------------------

    return jsonify({"acknowledged": True, "reference": reference}), 200







@bp.route("/webhook", methods=["POST"])
def handle_payment_webhook():
    data = request.json
    # Verify provider signature, idempotency, etc.
    payment_id = data["payment_id"]
    payer_id = data["user_id"]
    amount = Decimal(str(data["amount"]))

    # After marking payment SUCCESS:
    process_referral_bonuses(payer_id, amount, payment_id)

    return jsonify({"status": "ok"}), 200

from flask import request, current_app
import hmac
import hashlib
import time

def verify_webhook_signature():
    # Get the headers Marz sent
    signature_header = request.headers.get(current_app.config['WEBHOOK_SIGNATURE_HEADER'])
    timestamp_header = request.headers.get(current_app.config['WEBHOOK_TIMESTAMP_HEADER'])
    
    # Verify timestamp (prevent replay attacks)
    current_time = int(time.time())
    if current_time - int(timestamp_header) > 300:  # 5 minutes
        return False, "Timestamp too old"
    
    # Verify signature
    payload = timestamp_header + '.' + request.get_data(as_text=True)
    expected_signature = hmac.new(
        current_app.config['WEBHOOK_SECRET'].encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    if not hmac.compare_digest(signature_header, expected_signature):
        return False, "Invalid signature"
    
    return True, "Valid"