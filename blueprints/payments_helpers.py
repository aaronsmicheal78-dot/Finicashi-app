import os, re, json, uuid, requests
from flask import jsonify
from models import db, Payment, PaymentStatus, PackageCatalog, TransactionType, Package

REQUEST_TIMEOUT_SECONDS = int(os.getenv('REQUEST_TIMEOUT_SECONDS', '15'))
MARZ_BASE_URL = 'https://wallet.wearemarz.com/api/v1'

PACKAGE_MAP = {
    10000: "Bronze",
    20000: "Silver",
    50000: "Gold",
    100000: "Platinum",
    150000: "Premium",
    200000: "Ultimate"
}
ALLOWED_AMOUNTS = set(PACKAGE_MAP.keys())


# =========================
# VALIDATE PAYMENT INPUT
# =========================
def validate_payment_input(data):
    """Validate common input for both deposits and packages."""
    amount = data.get('amount')
    phone = data.get('phone')
    payment_type = data.get('payment_type', 'package').lower()
    package = data.get('package', '').lower()

    if not all([amount, phone]):
        return None, (jsonify({"error": "Missing required fields"}), 400)

    # Validate Ugandan phone
    if not re.match(r"^(?:\+256|0)?7\d{8}$", phone):
        return None, (jsonify({"error": "Invalid phone number"}), 400)

    # Validate per type
    if payment_type == "package":
        if amount not in ALLOWED_AMOUNTS:
            return None, (jsonify({"error": "Invalid package amount"}), 400)

        expected_package = PACKAGE_MAP.get(amount)
        if not expected_package or expected_package.lower() != package:
            return None, (jsonify({"error": "Mismatched package"}), 400)

        pkg_obj = PackageCatalog.query.filter_by(name=expected_package).first()
        if not pkg_obj:
            return None, (jsonify({"error": "Package not found"}), 404)

        validated_data= {
            "amount": int(amount),
            "phone": phone,
            "package": pkg_obj.name,     
            "payment_type": payment_type,
            "package_obj": pkg_obj       
        }
        return validated_data, None


    elif payment_type == "deposit":
        if int(amount) < 1000:
            return None, (jsonify({"error": "Deposit must be at least UGX 1,000"}), 400)
        package = None
    else:
        return None, (jsonify({"error": "Invalid payment type"}), 400)

    return {
        "amount": amount,
        "phone": phone,
        "package": package,
        "payment_type": payment_type
    }, None


# =========================
# CHECK EXISTING PAYMENT
# =========================
def handle_existing_payment(user, amount, payment_type):
    """Return existing pending payment if available."""
    existing = Payment.query.filter_by(
        user_id=user.id,
        amount=amount,
        transaction_type=TransactionType[payment_type.upper()],
        status=PaymentStatus.PENDING.value
    ).first()

    if existing:
        return jsonify({
            "reference": existing.reference,
            "status": existing.status,
            "note": "Idempotent: existing record returned"
        }), 200

    return None  # safe to continue


# =========================
# CREATE PAYMENT RECORD
# =========================
def create_payment_record(user, amount, phone, payment_type, package=None):
    """Create a new Payment record."""
    reference = str(uuid.uuid4())
    transaction_type = TransactionType[payment_type.upper()]
    
    if isinstance(package, PackageCatalog):
        package_id = package.id
        pkg_obj = package
    else:
        package_id = package
        pkg_obj = None

    payment = Payment(
        user_id=user.id,
        reference=reference,
        amount=amount,
        currency="UGX",
        phone_number=phone,
        provider=None,
        status=PaymentStatus.PENDING.value,
        method="MarzPay",
        external_ref=None,
        idempotency_key=str(uuid.uuid4()),
        raw_response=None,
        transaction_type=transaction_type,
        package_catalog_id=package_id if isinstance(package, PackageCatalog) else package,
        package_catalog=pkg_obj if isinstance(package, PackageCatalog) else None,    
    )
    
    db.session.add(payment)
    db.session.commit()
    return payment

# In payment processing code
def update_payment_status(payment, marz_response):
    marz_status = marz_response.get('status')
    if marz_status in ('success', 'completed', 'paid', 'sandbox'):
        payment.status = 'completed' 
        payment.verified = True
    elif marz_status == 'failed':
        payment.status = 'failed'
    else:
        payment.status = 'pending'
# =========================
# SEND TO MARZPAY
# =========================
def send_to_marzpay(payment, phone, amount, package=None):
    """Initiate payment request to MarzPay API."""
    headers = {
        "Authorization": f"Basic {os.environ.get('MARZ_AUTH_HEADER')}",
        "Content-Type": "application/json"
    }

    callback_url = "https://bedfast-kamron-nondeclivitous.ngrok-free.dev/payments/callback"
   

    if package:
        description = f"payment_for_{package.name}"
    elif payment.payment_type == "deposit":
        description = "account_deposit"
    else:
        description = "payment"
        
    print(f"Description: {description}")

    #Proper phone number formatting
    formatted_phone = phone
    if phone.startswith('0'):
        formatted_phone = "+256" + phone[1:]  # Convert 078... to +25678...
    elif phone.startswith('256'):
        formatted_phone = "+" + phone  # Convert 256... to +256...
    # If it already starts with +256, leave it as is
    
    payload = {
        "phone_number": formatted_phone,
        "amount": int(amount),
        "country": "UG",
        "reference": str(payment.reference),
        "callback_url": callback_url,
        "description": description
    }
    
    print(f"Payload being sent to MarzPay: {payload}")
    
    try:
        resp = requests.post(f"{MARZ_BASE_URL}/collect-money", json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
      

        resp.raise_for_status()
        marz_data = resp.json()
       

        status_map = {
            "success": PaymentStatus.COMPLETED.value,
            "completed": PaymentStatus.COMPLETED.value,
            "pending": PaymentStatus.PENDING.value,
            "failed": PaymentStatus.FAILED.value,
            "cancelled": PaymentStatus.FAILED.value,
            "expired": PaymentStatus.FAILED.value,
            "rejected": PaymentStatus.FAILED.value
        }

        marz_status = marz_data.get("status", "pending").lower()
        mapped_status = status_map.get(marz_status, PaymentStatus.PENDING.value)

        # Update payment status
        payment.status = mapped_status
        payment.raw_response = json.dumps(marz_data)
        payment.external_ref = marz_data.get("transaction_id")

        return marz_data, None

    except requests.RequestException as e:
        print(f"MarzPay API Request Exception: {e}")
        payment.status = PaymentStatus.FAILED.value
        payment.raw_response = json.dumps({"error": str(e)})
        
        error_response = jsonify({"error": f"Payment provider error: {str(e)}"})
        return None, error_response

    except Exception as e:
        print(f"Unexpected error in send_to_marzpay: {e}")
        payment.status = PaymentStatus.FAILED.value
        payment.raw_response = json.dumps({"error": str(e)})
        
        error_response = jsonify({"error": "Unexpected payment error"})
        return None, error_response



    description = f"payment_for_{package.name}" if package else "account_deposit"
    print(f"Description: {description}")
    
    # FIX: Proper phone number formatting
    formatted_phone = phone
    if phone.startswith('0'):
        formatted_phone = "+256" + phone[1:]  # Convert 078... to +25678...
    elif phone.startswith('256'):
        formatted_phone = "+" + phone  # Convert 256... to +256...
    # If it already starts with +256, leave it as is
    
    payload = {
        "phone_number": formatted_phone,  # FIX: Use properly formatted phone
        "amount": int(amount),
        "country": "UG",
        "reference": str(payment.reference),
        "callback_url": callback_url,
        "description": description
    }
    
    print(f"Payload being sent to MarzPay: {payload}")
    
    try:
        resp = requests.post(f"{MARZ_BASE_URL}/collect-money", json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        print(f"MarzPay API Response Status: {resp.status_code}")
        print(f"MarzPay API Response Text: {resp.text}")

        resp.raise_for_status()
        marz_data = resp.json()
        print(f"MarzPay API Success Response: {marz_data}")

        status_map = {
            "success": PaymentStatus.COMPLETED.value,
            "completed": PaymentStatus.COMPLETED.value,
            "pending": PaymentStatus.PENDING.value,
            "failed": PaymentStatus.FAILED.value,
            "cancelled": PaymentStatus.FAILED.value,
            "expired": PaymentStatus.FAILED.value,
            "rejected": PaymentStatus.FAILED.value
        }

        marz_status = marz_data.get("status", "pending").lower()
        mapped_status = status_map.get(marz_status, PaymentStatus.PENDING.value)

        # FIX: Update payment but don't commit here - let the route handle it
        payment.status = mapped_status
        payment.raw_response = json.dumps(marz_data)
        payment.external_ref = marz_data.get("transaction_id")

        # FIX: Remove db.session.commit() from here
        # The route will handle the commit

        return marz_data, None

    except requests.RequestException as e:
        print(f"MarzPay API Request Exception: {e}")
        # FIX: Update payment status but don't commit
        payment.status = PaymentStatus.FAILED.value
        payment.raw_response = json.dumps({"error": str(e)})
        
        # FIX: Return proper error format
        error_response = jsonify({"error": "Payment provider error"})
        return None, error_response

    except Exception as e:
        print(f"Unexpected error in send_to_marzpay: {e}")
        payment.status = PaymentStatus.FAILED.value
        payment.raw_response = json.dumps({"error": str(e)})
        
        error_response = jsonify({"error": "Unexpected payment error"})
        return None, error_response







# def send_to_marzpay(payment, phone, amount, package=None):
#     """Initiate payment request to MarzPay API."""
#     headers = {
#         "Authorization": f"Basic {os.environ.get('MARZ_AUTH_HEADER')}",
#         "Content-Type": "application/json"
#     }

#     callback_url ="https://bedfast-kamron-nondeclivitous.ngrok-free.dev/payments/callback"                                                  #os.environ.get("MARZ_CALLBACK_URL")
#     print(f"Callback URL being sent to Marz: {callback_url}")  
#     description = f"payment_for_{package.name}" if package else "account_deposit"
#     print(f"Description: {description}")
#     payload = {
#         "phone_number": f"+256{phone.lstrip('0')}",
#         "amount": int(amount),
#         "country": "UG",
#         "reference": str(payment.reference),
#         "callback_url": callback_url,
#         "description": description
#     }
#     try:
#         resp = requests.post(f"{MARZ_BASE_URL}/collect-money", json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)

   
#         resp.raise_for_status()
#         marz_data = resp.json()

#         status_map = {
#             "success": PaymentStatus.COMPLETED.value,
#             "completed": PaymentStatus.COMPLETED.value,
#             "pending": PaymentStatus.PENDING.value,
#             "failed": PaymentStatus.FAILED.value,
#             "cancelled": PaymentStatus.FAILED.value,
#             "expired": PaymentStatus.FAILED.value,
#             "rejected": PaymentStatus.FAILED.value
#         }

#         marz_status = marz_data.get("status", "pending").lower()
#         mapped_status = status_map.get(marz_status, PaymentStatus.PENDING.value)

#         payment.status = mapped_status
#         payment.raw_response = json.dumps(marz_data)
#         payment.external_ref = marz_data.get("transaction_id")

#         db.session.commit()

#         return marz_data, None

#     except requests.RequestException as e:
#         payment.status = PaymentStatus.FAILED.value
#         payment.raw_response = json.dumps({"error": str(e)})
#         db.session.commit()
#         return None, (jsonify({"error": "Payment provider error"}), 502)












































