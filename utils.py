# utils.py - cryptographic helpers and common utilities
import hmac                                                         # HMAC library for signature verification
import hashlib                                                      # hashing algorithms
import time                                                         # timestamp operations
from flask import current_app                                       # app config access
from extensions import logger                                        # centralized logger

def verify_webhook_signature(raw_body: bytes, headers: dict) -> bool:
    """
    Verify webhook signatures using HMAC-SHA256.
    The expected format (common pattern): signature = HMAC_SHA256(webhook_secret, f"{timestamp}.{raw_body}")
    This function reads timestamp and signature header names from Config and performs a constant-time compare.
    """
    conf = current_app.config                                        # get app config
    webhook_secret = conf.get("WEBHOOK_SECRET")                      # secret must be set for verification
    if not webhook_secret:                                           # if missing, log & reject for safety
        logger.error("WEBHOOK_SECRET not configured; rejecting webhook")  # log critical error
        return False

    sig_header_name = conf.get("WEBHOOK_SIGNATURE_HEADER", "Marz-Signature")  # signature header
    ts_header_name = conf.get("WEBHOOK_TIMESTAMP_HEADER", "Marz-Timestamp")   # timestamp header

    signature = headers.get(sig_header_name)                          # signature provided by Marz
    timestamp = headers.get(ts_header_name)                           # timestamp provided by Marz

    if signature is None or timestamp is None:                        # both headers required
        logger.warning("Webhook missing signature or timestamp headers")     # warn for debugging
        return False

    try:
        signed_payload = timestamp + "." + raw_body.decode("utf-8")   # canonical string to sign
    except Exception as e:
        logger.exception("Failed to decode raw_body while verifying signature: %s", e)
        return False

    # compute HMAC using SHA256
    computed_hmac = hmac.new(webhook_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    # compare using constant time comparison to avoid timing attacks
    if hmac.compare_digest(computed_hmac, signature):
        return True
    else:
        logger.warning("Webhook signature mismatch: expected %s got %s", computed_hmac, signature)
        return False

def safe_marz_headers():
    """
    Returns HTTP headers required to call Marz endpoints securely.
    Pulls the Basic token from the app config and sets appropriate Content-Type.
    """
    from flask import current_app
    token = current_app.config.get("MARZ_BASIC_TOKEN")
    if not token:
        logger.error("MARZ_BASIC_TOKEN not set")                      # developer error; fail loudly
        raise RuntimeError("MARZ_BASIC_TOKEN not configured")
    return {
        "Authorization": f"Basic {token}",                           # Basic auth token expected by Marz
        # Do not set content-type here if using multipart/form-data; the requests lib will handle it
    }
import re

def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    return re.match(r'^\+?\d{9,15}$', phone)
