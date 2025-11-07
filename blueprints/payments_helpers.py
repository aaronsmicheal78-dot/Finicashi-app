import requests
from flask import current_app
from uuid import uuid4
from utils import get_marz_authorization_header

def send_withdraw_request(withdraw_obj):
    """
    Sends a withdrawal request to MarzPay securely.
    withdraw_obj: instance of Withdraw model.
    """

    
    MARZ_BASE_URL = current_app.config.get("MARZ_BASE_URL")
    CALLBACK_URL = f"{current_app.config.get('APP_BASE_URL')}/payments/withdraw"
    AUTH_HEADER = get_marz_authorization_header\\\\if not MARZ_BASE_URL or not AUTH_HEADER:
        raise ValueError("MarzPay configuration missing")


    payload = {
        "reference": str(withdraw_obj.id), 
        "amount": float(withdraw_obj.amount),
        "phone_number": f"+256{withdraw_obj.phone.strip()[-9:]}",  
        "country_code": "UG",
        "callback_url": CALLBACK_URL,
    }

    headers = {
        "Authorization": AUTH_HEADER,
        "Content-Type": "application/json"
    }

    # Send request securely
    try:
        response = requests.post(f"{MARZ_BASE_URL}/collect_money", json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # raise exception for non-2xx
        data = response.json()
        return {"success": True, "response": data}
    except requests.exceptions.RequestException as e:
        # log or handle request errors
        return {"success": False, "error": str(e)}
