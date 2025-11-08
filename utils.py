                                                    
import time                                                        
from flask import current_app                                       
from extensions import logger  
import base64
import requests                                    
import os
import re


def safe_marz_headers():
    """
    Returns HTTP headers required to call Marz endpoints securely.
    Pulls the Basic token from the app config and sets appropriate Content-Type.
    """
    token = current_app.config.get("MARZ_BASIC_TOKEN")
    if not token:
        logger.error("MARZ_BASIC_TOKEN not set")                     
        raise RuntimeError("MARZ_BASIC_TOKEN not configured")
    return {
        "Authorization": f"Basic {token}",                         
        "Content-Type": "application/json"
    }


def validate_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_phone(phone):
    return re.match(r'^\+?\d{9,15}$', phone)



def get_marz_authorization_header():
    API_KEY = "your_api_key_here"  
    SECRET = "your_secret_here"   
    
    credentials = f"{API_KEY}:{SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"






def get_marz_authorization_header():
    MARZ_API_KEY = os.environ.get('MARZ_API_KEY')
    MARZ_API_SECRET = os.environ.get('MARZ_API_SECRET')
    
    if not MARZ_API_KEY or not MARZ_API_SECRET:
        raise ValueError("Marz Pay API credentials not found in environment variables")
    
    credentials = f"{MARZ_API_KEY}:{MARZ_API_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded_credentials}"

try:
    auth_header = get_marz_authorization_header()
    print("✅ Authorization header generated successfully")
except ValueError as e:
    print(f"❌ Error: {e}")


