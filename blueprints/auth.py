
from flask import request, jsonify, session, render_template, Blueprint, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Transaction, Bonus, Referral, Wallet, UserProfile, KycStatus
import re, secrets, string
from utils import validate_email, validate_phone 
from flask import Blueprint, jsonify, request, session
from extensions import db
import logging
import string
import secrets
from flask_login import login_user
import traceback
import logging
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
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

# Validation helpers
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    # Uganda + International
    uganda = r'^(\+256|256|0)7\d{8}$'
    e164 = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(uganda, phone) or re.match(e164, phone))

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
# def validate_email(email):
#     pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
#     return re.match(pattern, email) is not None

# def validate_phone(phone):
#     # Basic phone validation (adjust pattern as needed)
#     pattern = r'^\+?1?\d{9,15}$'
#     return re.match(pattern, phone) is not None



# #===========================================================================
# #      SIGN UP ROUTE.
# #==============================================================================
# @bp.route("/api/signup", methods=["POST",])
# @limiter.limit("5 per minute, 20 per day")
# def signup():
    
#     """
#     Create new user + integrate them into the referral tree.
#     Uses safer validation, atomic transaction, and full tree integration.
#     """
#     print("SIGN-UP ROUTE HIT< PROCESSING REGISTRATION")
#     try:
#         data = request.get_json(silent=True)
        
#         if not data:
#             return jsonify({"error": "Invalid or missing JSON body"}), 400

#         full_name = data.get("fullName", "").strip()
#         email = data.get("email", "").strip().lower()
#         phone = data.get("phone", "").strip()
#         password = data.get("password", "")

#         referral_code = data.get("referralCode", "").strip().upper()
        
#         if not referral_code:
            
#             referral_code = os.getenv("SYSTEM_REFERRER_CODE")  
#             referrer = User.query.filter_by(referral_code=referral_code).first()
#             logger.info(f"No referral code provided, using default referrer: {referrer}")

#             if not referrer:
#                 logger.info(f"No system referrer. Please congigure!")
#                 return jsonify({"Error": "System referrer not configured"}), 500

#         else:
#             referrer = User.query.filter_by(referral_code=referral_code).first()
#             if not referrer:
#                 return jsonify({"error": "Invalid referral Code"}), 400
            
#             if referrer and referrer.phone == phone:
#                 return jsonify({"error": "Cannot use your own referral code"}), 400
#         # -----------------------------------------
#         #  BASIC VALIDATION
#         # -----------------------------------------
#         if not full_name or not phone or not password:
#             return jsonify({"error": "All fields are required"}), 400
        
#         if phone and not validate_phone(phone):
#             return jsonify({"error":"Please Enter a valid phone number"}), 400
        
#         if len(password) < 6:
#             return jsonify({"error": "Password must be at least 6 characters"}), 400

#         # Ensure user does not already exist
#         exists = User.query.filter(
#             (User.email == email) | (User.phone == phone)
#         ).first()

#         if exists:
#             return jsonify({"error": "Email or phone already registered"}), 400

#         # -----------------------------------------
#         #  GENERATE UNIQUE REFERRAL CODE
#         # -----------------------------------------
#         def generate_referral_code(L=8):
#             chars = string.ascii_uppercase + string.digits
#             for _ in range(10):
#                 code = ''.join(secrets.choice(chars) for _ in range(L))
#                 if not User.query.filter_by(referral_code=code).first():
#                     return code
#             # fallback
#             return ''.join(secrets.choice(chars) for _ in range(L))

#         # -----------------------------------------
#         #  BEGIN ATOMIC TRANSACTION
#         # -----------------------------------------
#         with db.session.begin_nested():

#             new_user = User(
#                 username=full_name,
#                 email=email,
#                 phone=phone,
#                 referral_code=generate_referral_code(),
#                 referred_by=referrer.id if referrer else None,
#                 referral_code_used=referral_code if referrer else None,
#                 network_depth=0,
#                 direct_referrals_count=0,
#                 total_network_size=0
#             )
#             new_user.set_password(password)    
           

#             db.session.add(new_user)
#             db.session.flush()  

#             signup_bonus = Bonus(
#                 user_id=new_user.id,
#                 type="signup",
#                 amount=5000,
#                 status="active")  

#             db.session.add(signup_bonus)
           
#             current_app.logger.info(
#                 f"Successfully added bonus {signup_bonus} for {new_user.id}")

            
#             # -------------------------------------
#             #  REFERRAL TREE LOGIC
#             # -------------------------------------
#             from bonus.refferral_tree import ReferralTreeHelper
#             if referrer:
#                 current_app.logger.info(f"Referrer found: {referrer}")
               

#                 added = ReferralTreeHelper.add_new_user(new_user.id, referrer.id)


#                 if not added:
#                     current_app.logger.error(
#                             f"[SIGNUP] Referral tree insertion failed for user {new_user.id}"
#                         )
#                     raise Exception("Referral tree error")
                
#                 # if referrer.direct_referrals_count is None:
#                 #    referrer.direct_referrals_count = 0   
#                 #    referrer.direct_referrals_count += 1

#                 from models import Referral

#                 if referrer:
#                     current_app.logger.info(f"Referrer found: {referrer}")
#                     referral = Referral.query.filter_by(
#                         referrer_id=referrer.id,
#                         referred_email=new_user.email,
#                         status="pending"
#                     ).first()

#                     # If no referral row was created earlier, create one now
#                     if not referral:
#                         current_app.logger.info(f"Referrer NOT found!")
#                         referral = Referral(
#                             referrer_id=referrer.id,
#                             referred_email=new_user.email
#                         )
#                         db.session.add(referral)

#                     referral.referred_id = new_user.id
#                     referral.status = "active"
#                     db.session.commit()

#                     old_status = 'pending'
#                     new_status = 'active'
#                     current_app.logger.info(f"Referrer {referrer} status changed from {old_status} to {new_status}")

#                 else:                
#                     added = ReferralTreeHelper.initialize_standalone_user(new_user.id)
                
#                 if not added:
#                     current_app.logger.error(
#                         f"[SIGNUP] Standalone user initialization failed for user {new_user.id}"
#                     )
#                     raise Exception("Referral tree initialization error")
      
#         db.session.commit()
#         current_app.logger.info('SUCESSFUL REGISTRATION WITH STATUS CHANGE')
      
#         return jsonify({
#             "status": "success",
#             "message": "Signup successful",
#             "user": {
#                 "id": new_user.id,
#                 "username": new_user.username,
#                 "email": new_user.email,
#                 "phone": new_user.phone,
#                 "referral_code": new_user.referral_code
#             }
#         }), 201
        
#     except Exception as e:
#         db.session.rollback()
#         print("\n\n=== SIGNUP ERROR ===")
#         print(str(e))
#         traceback.print_exc()
#         print("=== END ERROR ===\n\n")
#         return jsonify({"error": "Signup failed. Please try again."}), 500
   
# =============================================
# Authentication Blueprint for Signup, Login
# =============================================

 # --------------------------------------------------
 #      2️⃣ Login Route
 # --------------------------------------------------
@bp.route("/api/login", methods=["POST"])
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





