                                                    
import time                                                        
from flask import current_app                                       
from extensions import logger  
import base64
import requests                                    
import os
import re
import uuid

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
    
except ValueError as e:
    print(f"❌ Error: {e}")


    # Update your MarzPay API calls with better timeout handling:

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class MarzPayHelper:
    @staticmethod
    def create_payment_session(phone_number, amount, description=""):
        """Create payment session with retry logic"""
        try:
            # Create session with retry strategy
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            payload = {
                'phone_number': phone_number,
                'amount': amount,
                'country': 'UG',
                'reference': str(uuid.uuid4()),
                'callback_url': 'https://finicashi-app.onrender.com/payments/callback',
                'description': description
            }
            
            # Increased timeout to 30 seconds
            response = session.post(
                'https://wallet.wearemarz.com/api/v1/payments/initiate',
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return True, response.json(), "Payment session created"
            else:
                return False, None, f"API error: {response.status_code} - {response.text}"
                
        except requests.exceptions.Timeout:
            return False, None, "MarzPay API timeout after 30 seconds"
        except requests.exceptions.ConnectionError:
            return False, None, "MarzPay API connection error"
        except Exception as e:
            return False, None, f"MarzPay API error: {str(e)}"


