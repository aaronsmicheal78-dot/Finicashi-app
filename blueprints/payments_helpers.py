import os, re, json, uuid, requests
from flask import jsonify
from models import db, Payment, PaymentStatus, PackageCatalog, TransactionType, Package
from datetime import datetime, timedelta
from decimal import Decimal

REQUEST_TIMEOUT_SECONDS = int(os.getenv('REQUEST_TIMEOUT_SECONDS', '60'))
MARZ_BASE_URL = 'https://wallet.wearemarz.com/api/v1'

PACKAGE_MAP = {
    10000: "Bronze",
    20000: "Silver",
    50000: "Gold",
    100000: "Platinum",
    150000: "Premium",
    200000: "Ultimate",
    500000: "diamond",
    750000: "ruby",
    1000000: "emerald"
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
    # if not re.match(r"^(?:\+256|0)?7\d{8}$", phone):
    #   return None, (jsonify({"error": "Invalid phone number"}), 400)

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
 
        validated_data = {
            "amount": int(amount),
            "phone": phone,
            "package": None,
            "payment_type": payment_type,
            "package_obj": None
            }
        return validated_data, None
    else: 
        return None, (jsonify({"error": "Invalid payment type"}), 400)


# =========================
# CHECK EXISTING PAYMENT
# =========================
import logging
logger = logging.getLogger(__name__)

def handle_existing_payment(user, amount, payment_type):
    """Return existing pending payment object if available, None otherwise."""
    logging.info(f"Searching for existing payment: user={user.id}, amount={amount}, type={payment_type}")
    try:
        existing = Payment.query.filter_by(
            user_id=user.id,
            amount=amount,
            transaction_type=TransactionType[payment_type.upper()],
            status=PaymentStatus.PENDING.value
        ).first()
        logging.info(f"Found existing payment: {existing}")
        return existing  
    except Exception as e:
        logging.error(f"Error in handle_existing_payment: {str(e)}")
        return None
# =========================
# CREATE PAYMENT RECORD
# =========================
def create_payment_record(user, amount, phone, payment_type, package=None):
    """Create a new Payment record."""
    logging.info(f"Creating payment record for user {user.id}")
    reference = str(uuid.uuid4())
    transaction_type = TransactionType[payment_type.upper()]
    try:
        if isinstance(package, PackageCatalog):
            package_id = package.id
            pkg_obj = package
        else:
            package_id = None
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
            payment_type=payment_type,
            transaction_type=transaction_type,
            package_catalog_id=package_id if isinstance(package, PackageCatalog) else package,
            package_catalog=pkg_obj if isinstance(package, PackageCatalog) else None    
        )
        
        db.session.add(payment)
        db.session.flush()
        print(f"payment created: {payment}")
        logging.info(f"Payment record created with ID: {payment.id}")
        return payment
    except Exception as e:
        logging.error(f"Error in create_payment_record: {str(e)}")
        return None

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

    callback_url = "https://finicashi-app.onrender.com/payments/callback"
   

    if payment.payment_type == "package" and package:
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
    
   # print(f"Payload being sent to MarzPay: {payload}")
    print("🔹 MarzPay payload:", json.dumps(payload, indent=2))

    try:
        resp = requests.post(f"{MARZ_BASE_URL}/collect-money", json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
      

        resp.raise_for_status()
        marz_data = resp.json()
        print("🔹 MarzPay response status:", resp.status_code)
        print("🔹 MarzPay response body:", resp.text)


        status_map = {
            "confirmed": PaymentStatus.COMPLETED.value,
            "approved": PaymentStatus.COMPLETED.value,
            "success": PaymentStatus.COMPLETED.value,
            "successful": PaymentStatus.COMPLETED.value,
            "completed": PaymentStatus.COMPLETED.value,
            "complete": PaymentStatus.COMPLETED.value,
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
    
    except requests.HTTPError as e:
        print("MarzPay HTTP error:", e)
        print("Response body:", e.response.text)
        return None, e
    
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



def create_user_package(user, package_catalog: PackageCatalog):
    """Create a new Package for a user after successful payment."""
    if not package_catalog:
        raise ValueError("Invalid package catalog")

    package_amount = package_catalog.amount

    new_package = Package(
        user_id=user.id,
        catalog_id=package_catalog.id,
        package=package_catalog.name,
        type="purchased",
        status="active",
        package_amount=package_catalog.amount,  
        daily_bonus_rate=Decimal("0.05"),
        total_bonus_paid=Decimal("0.00"),
        activated_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=30)  
    )
    db.session.add(new_package)
    db.session.commit()
    return new_package
