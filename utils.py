# utils.py - cryptographic helpers and common utilities
import hmac                                                         # HMAC library for signature verification
import hashlib                                                      # hashing algorithms
import time                                                         # timestamp operations
from flask import current_app                                       # app config access
from extensions import logger  
import base64
import requests                                      # centralized logger
import os
import re

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


def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    return re.match(r'^\+?\d{9,15}$', phone)



def get_marz_authorization_header():
    API_KEY = "your_api_key_here"  # Replace with your actual API key
    SECRET = "your_secret_here"    # Replace with your actual secret
    
    credentials = f"{API_KEY}:{SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"






def get_marz_authorization_header():
    API_KEY = os.environ.get('MARZ_API_KEY')
    SECRET = os.environ.get('MARZ_SECRET')
    
    if not API_KEY or not SECRET:
        raise ValueError("Marz Pay API credentials not found in environment variables")
    
    credentials = f"{API_KEY}:{SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

# Example usage with error handling
try:
    auth_header = get_marz_authorization_header()
    print("✅ Authorization header generated successfully")
except ValueError as e:
    print(f"❌ Error: {e}")


# Usage in your payment route:
#@bp.route('/payments/initiate/', methods=['POST'])
def initiate_payment():
    try:
        # Your existing code...
        
        # Prepare Marz Pay API request
        headers = {
            'Authorization': get_marz_authorization_header(),
            'Content-Type': 'application/json'
        }
        
        # payload = {
        #     'amount': amount,
        #     'currency': 'UGX',
        # #    'description': f'{package.title()} Package Payment',
        #     'phone': phone,
        #     'callback_url': 'http://yourdomain.com/payments/webhook',
        #     'return_url': 'http://yourdomain.com/payments/success'
        
        
        # # Make API call to Marz Pay
        # response = requests.post(
        #     'https://api.marzpay.com/v1/payments',  # Replace with actual Marz Pay endpoint
        #     headers=headers,
        #     json=payload,
        #     timeout=30
        # )
        
        # Handle response...
        
    except Exception as e:
        # Error handling...
        pass