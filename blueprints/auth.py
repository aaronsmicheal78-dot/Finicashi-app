
from flask import request, jsonify, session, Blueprint, current_app

from models import User, Bonus, Referral, OTPRequest
import re, secrets, string
from utils import validate_email, validate_phone 
from flask import Blueprint, jsonify, request, session
from extensions import db
import logging
import string
import secrets
import logging
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from blueprints.otp import send_sms
from datetime import datetime, timedelta
import random
import bcrypt

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
#==================================================================================================================

bp = Blueprint("auth", __name__, url_prefix="")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("REDIS_URL")
)

# routes/auth.py
from flask import Blueprint, request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User, Bonus, Referral
from extensions import limiter  
import secrets, string, re, bleach
from sqlalchemy.exc import IntegrityError
import logging

bp = Blueprint("auth", __name__, url_prefix="")


def hash_otp(otp: str) -> str:
    """Hash OTP securely"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(otp.encode(), salt).decode()

def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Verify OTP against stored hash"""
    return bcrypt.checkpw(otp.encode(), otp_hash.encode())
# Validation helpers
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    phone = phone.strip()

    match = re.match(r'^(\+256|256|0)?(7\d{8})$', phone)
    if match:
        return '+256' + match.group(2)

    return None

def validate_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    return True, None

@bp.route("/api/signup", methods=["POST"])
@limiter.limit("5 per minute; 20 per day")  # Rate limiting
def signup():
    logger = current_app.logger
    
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid request"}), 400

        # Sanitize and extract input
        full_name = bleach.clean(data.get("fullName", "").strip(), tags=[], strip=True)
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        password = data.get("password", "")
        referral_code = data.get("referralCode", "").strip().upper() or None

        # Validate input
        if not all([full_name, email, phone, password]):
            return jsonify({"error": "All fields are required"}), 400
        
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400
        
        if not validate_phone(phone):
            return jsonify({"error": "Invalid phone number"}), 400
        
        is_valid, error = validate_password_strength(password)
        if not is_valid:
            return jsonify({"error": error}), 400

        # Check for existing user (generic error to prevent enumeration)
        if User.query.filter((User.email == email) | (User.phone == phone)).first():
            return jsonify({"error": "Registration failed. Please try different credentials."}), 400

        # Resolve referrer
        referrer = None
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if not referrer:
                return jsonify({"error": "Invalid referral code"}), 400
            if referrer.phone == phone:
                return jsonify({"error": "Cannot use your own referral code"}), 400
        else:
            # Use system referrer from config
            system_referrer_id = current_app.config.get('SYSTEM_REFERRER_CODE')
            if system_referrer_id:
                referrer = User.query.get(system_referrer_id)

        def generate_code(length=8):
            chars = string.ascii_uppercase + string.digits
            return ''.join(secrets.choice(chars) for _ in range(length))

        # Atomic transaction for user creation
        try:
            new_user = User(
                username=full_name,
                email=email,
                phone=phone,
                referral_code=generate_code(),
                referred_by=referrer.id if referrer else None,
                network_depth=0,
                direct_referrals_count=0,
                total_network_size=0
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.flush()  # Get ID

            # Create signup bonus
            signup_bonus = Bonus(
                user_id=new_user.id,
                type="signup",
                amount=5000,
                status="active"
            )
            db.session.add(signup_bonus)

            # Handle referral relationship
            if referrer:
                referral = Referral.query.filter_by(
                    referrer_id=referrer.id,
                    referred_email=email,
                    status="pending"
                ).first()
                
                if not referral:
                    referral = Referral(
                        referrer_id=referrer.id,
                        referred_email=email
                    )
                    db.session.add(referral)
                
                referral.referred_id = new_user.id
                referral.status = "active"

            db.session.commit()  # Commit user + bonus + referral atomically

        except IntegrityError:
            db.session.rollback()
            # Referral code collision - rare, ask user to retry
            return jsonify({"error": "Registration conflict. Please try again."}), 409
        except Exception as e:
            db.session.rollback()
            logger.error(f"Signup transaction failed: {e}")
            raise

        # Non-critical: Update referral tree (async to avoid blocking)
        if referrer:
            try:
                # For MVP: simple background thread
                import threading
                def _update_tree():
                    try:
                        from bonus.refferral_tree import ReferralTreeHelper
                        ReferralTreeHelper.add_new_user(new_user.id, referrer.id)
                    except Exception as tree_err:
                        logger.error(f"Referral tree update failed: {tree_err}")
                
                thread = threading.Thread(target=_update_tree, daemon=True)
                thread.start()
            except Exception as e:
                logger.warning(f"Failed to queue referral tree update: {e}")
                # Don't fail signup for non-critical tree update

        logger.info(f"Signup successful: user_id={new_user.id}, phone={phone[:7]}***")

        return jsonify({
            "status": "success",
            "message": "Signup successful",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,  # Consider hiding in production
                "phone": new_user.phone,   # Consider hiding in production
                "referral_code": new_user.referral_code
            }
        }), 201

    except Exception as e:
        logger.exception("Signup failed")
        return jsonify({"error": "Registration failed. Please try again."}), 500

 # --------------------------------------------------
 #      2️⃣ Login Route
 # --------------------------------------------------
@bp.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute; 20 per day")
def login():
   
    """
    Authenticate a user.
    Expected JSON:
    {
        "email_or_phone": "",
        "password": ""
    }
     """
    print("Route-HIT: login processing....")
    print("HEADERS:", request.headers)
    print("RAW BODY:", request.data)
    print("JSON PARSED:", request.get_json(silent=True))

    
    data = request.get_json(force=True, silent=True) # or request.form
    email_or_phone = data.get("email_or_phone", "").strip().lower()
    password = data.get("password", "")

    print("Method:", request.method)
    print("Content-Type:", request.headers.get("Content-Type"))
    print("Body:", request.get_data())

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    if not email_or_phone or not password:
        return jsonify({"error": "Email/Phone and password are required"}), 400

    
    user = User.query.filter(
        (User.email == email_or_phone) | (User.phone == email_or_phone)).first()
    print('USER FOUND:', user)

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful",
        "user": user.to_dict()
    }), 200

#-----------------------------------------------------------------------------------------------------
@bp.route("/api/logout", methods=["POST"])
def logout():
    """
    Destroy User session
    """
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

# --------------------------------------------------
# 4️⃣ Check Session (for frontend auto-login)
# --------------------------------------------------
@bp.route("/session", methods=["GET"])
def check_session():
    """Returns current logged-in user data if authenticated"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 200

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": user.to_dict()
    }), 200


@bp.route('/api/request-verification', methods=['POST'])
def request_verification():
    """Handle verification request"""
    
    print("=" * 50)
    print("STEP 1: REQUEST VERIFICATION HIT")
    print("=" * 50)

    try:
        # ✅ 1. Get user from session
        user_id = session.get("user_id")
        print(f"STEP 2: User ID from session: {user_id}")
        
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        # ✅ 2. Fetch user
        user = User.query.get(user_id)
        print(f"STEP 3: User found: {user}")
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        user_phone = user.phone
        phone = validate_phone(user_phone)
        print(f"STEP 4: Phone number: {phone}")
        
        # ✅ 3. Check if already verified
        if user.is_verified == 'verified':
            print("STEP 5: User already verified")
            return jsonify({"message": "User already verified"}), 200
       
        # ✅ 4. Rate limiting
        print("STEP 6: Checking rate limiting...")
        recent = OTPRequest.query.filter_by(
            user_id=user_id,
            purpose="profile_verification"
        ).order_by(OTPRequest.created_at.desc()).first()
        
        if recent and (datetime.utcnow() - recent.created_at).seconds < 60:
            print(f"STEP 7: Rate limited - last request was {(datetime.utcnow() - recent.created_at).seconds} seconds ago")
            return jsonify({"error": "Wait before requesting another OTP"}), 429
        
        print("STEP 7: Rate limit check passed")

        # ✅ 5. Generate OTP
        otp = str(random.randint(100000, 999999))
        print(f"STEP 8: Generated OTP: {otp}")
        print(f"STEP 8a: OTP type: {type(otp)}")
        print(f"STEP 8b: OTP length: {len(otp)}")
        
        # ✅ 6. Hash OTP
        otp_hash = hash_otp(otp)
        print(f"STEP 9: OTP Hash: {otp_hash}")
        
        # ✅ 7. Store OTP
        print("STEP 10: Creating OTP record...")
        otp_record = OTPRequest(
            user_id=user_id,
            phone=phone,
            otp_hash=otp_hash,
            purpose="profile_verification",
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        db.session.add(otp_record)
        db.session.commit()
        print(f"STEP 11: OTP record saved with ID: {otp_record.id}")
        
        # ✅ 8. Send SMS
        print("STEP 12: Preparing to send SMS...")
        print(f"STEP 12a: Phone: {phone}")
        print(f"STEP 12b: OTP to send: {otp}")
        
        try:
            print("STEP 13: Calling send_sms function...")
            result = send_sms(phone, f"FINICASHI: Your verification code is {otp}")
            print(f"STEP 14: send_sms returned: {result}")
            
        except Exception as sms_error:
            print(f"STEP 15: SMS ERROR - {type(sms_error).__name__}: {str(sms_error)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to send OTP: {str(sms_error)}"}), 500

        print("STEP 16: All steps completed successfully!")
        return jsonify({
            "message": "Verification OTP sent successfully",
            "status": "pending"
        })

    except Exception as e:
        print(f"ERROR at STEP: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500
#=====================================================

@bp.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    print("VERIFY OTP HIT: Processing...")

    try:
        # ✅ 1. Get user from session
        user_id = session.get("user_id")
        print("USER:", user_id)
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401

        # ✅ 2. Get request data
        data = request.get_json()
        print("DATA RECEIVED:", data)
        otp_input = data.get("otp")

        if not otp_input:
            return jsonify({"error": "OTP is required"}), 400

        # ✅ 3. Fetch latest OTP
        otp_record = OTPRequest.query.filter_by(
            user_id=user_id,
            purpose="profile_verification",
            is_used=False
        ).order_by(OTPRequest.created_at.desc()).first()

        if not otp_record:
            return jsonify({"error": "No OTP request found"}), 404

        # ✅ 4. Check expiry
        if datetime.utcnow() > otp_record.expires_at:
            return jsonify({"error": "OTP has expired"}), 400

        # ✅ 5. Check attempts
        MAX_ATTEMPTS = 5
        if otp_record.attempts >= MAX_ATTEMPTS:
            return jsonify({"error": "Too many attempts. Request a new OTP"}), 403

        # ✅ 6. Verify OTP
        if not verify_otp_hash(otp_input, otp_record.otp_hash):
            otp_record.attempts += 1
            db.session.commit()

            return jsonify({
                "error": "Invalid OTP",
                "attempts_left": MAX_ATTEMPTS - otp_record.attempts
            }), 400

        # ✅ 7. SUCCESS
        otp_record.is_used = True

        user = User.query.get(user_id)
        user.is_verified = True
        user.verification_status = "verified"

        db.session.commit()

        return jsonify({
            "message": "Verification successful",
            "status": "verified"
        }), 200

    except Exception as e:
        print("VERIFY OTP ERROR:", str(e))
        return jsonify({"error": "Internal server error"}), 500

