
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


logger = logging.getLogger(__name__)
#==================================================================================================================

bp = Blueprint("auth", __name__, url_prefix="")

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    # Basic phone validation (adjust pattern as needed)
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone) is not None



#===========================================================================
#      SIGN UP ROUTE.
#==============================================================================
@bp.route("/api/signup", methods=["POST",])
def signup():
    
    """
    Create new user + integrate them into the referral tree.
    Uses safer validation, atomic transaction, and full tree integration.
    """
    print("SIGN-UP ROUTE HIT< PROCESSING REGISTRATION")
    try:
        data = request.get_json(silent=True)
        
        if not data:
            return jsonify({"error": "Invalid or missing JSON body"}), 400

        full_name = data.get("fullName", "").strip()
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        password = data.get("password", "")
        referral_code = data.get("referralCode", "").strip().upper()

        # -----------------------------------------
        #  BASIC VALIDATION
        # -----------------------------------------
        if not full_name or not email or not phone or not password:
            return jsonify({"error": "All fields are required"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # Ensure user does not already exist
        exists = User.query.filter(
            (User.email == email) | (User.phone == phone)
        ).first()

        if exists:
            return jsonify({"error": "Email or phone already registered"}), 400

        # -----------------------------------------
        #  HANDLE REFERRAL CODE
        # -----------------------------------------
        referrer = None
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()

            if not referrer:
                A = referral_code 
                referrer = User.query.filter_by(referral_code=A)
                logger.info(f"Referrer is {A}")

            if referrer.phone == phone:
                return jsonify({"error": "Cannot use your own referral code"}), 400

        # -----------------------------------------
        #  GENERATE UNIQUE REFERRAL CODE
        # -----------------------------------------
        def generate_referral_code(L=8):
            chars = string.ascii_uppercase + string.digits
            for _ in range(10):
                code = ''.join(secrets.choice(chars) for _ in range(L))
                if not User.query.filter_by(referral_code=code).first():
                    return code
            # fallback
            return ''.join(secrets.choice(chars) for _ in range(L))

        # -----------------------------------------
        #  BEGIN ATOMIC TRANSACTION
        # -----------------------------------------
        with db.session.begin_nested():

            new_user = User(
                username=full_name,
                email=email,
                phone=phone,
                referral_code=generate_referral_code(),
                referred_by=referrer.id if referrer else None,
                referral_code_used=referral_code if referrer else None,
                network_depth=0,
                direct_referrals_count=0,
                total_network_size=0
            )
            new_user.set_password(password)    
           

            db.session.add(new_user)
            db.session.flush()  

            signup_bonus = Bonus(
                user_id=new_user.id,
                type="signup",
                amount=5000,
                status="active")  

            db.session.add(signup_bonus)
           
            current_app.logger.info(
                f"Successfully added bonus {signup_bonus} for {new_user.id}")

            
            # -------------------------------------
            #  REFERRAL TREE LOGIC
            # -------------------------------------
            from bonus.refferral_tree import ReferralTreeHelper
            if referrer:
                current_app.logger.info(f"Referrer found: {referrer}")
               

                added = ReferralTreeHelper.add_new_user(new_user.id, referrer.id)


                if not added:
                    current_app.logger.error(
                            f"[SIGNUP] Referral tree insertion failed for user {new_user.id}"
                        )
                    raise Exception("Referral tree error")
                
                # if referrer.direct_referrals_count is None:
                #    referrer.direct_referrals_count = 0   
                #    referrer.direct_referrals_count += 1

                from models import Referral

                if referrer:
                    current_app.logger.info(f"Referrer found: {referrer}")
                    referral = Referral.query.filter_by(
                        referrer_id=referrer.id,
                        referred_email=new_user.email,
                        status="pending"
                    ).first()

                    # If no referral row was created earlier, create one now
                    if not referral:
                        current_app.logger.info(f"Referrer NOT found!")
                        referral = Referral(
                            referrer_id=referrer.id,
                            referred_email=new_user.email
                        )
                        db.session.add(referral)

                    referral.referred_id = new_user.id
                    referral.status = "active"
                    db.session.commit()

                    old_status = 'pending'
                    new_status = 'active'
                    current_app.logger.info(f"Referrer {referrer} status changed from {old_status} to {new_status}")

                else:                
                # Initialize standalone user in referral network
                    added = ReferralTreeHelper.initialize_standalone_user(new_user.id)
                
                if not added:
                    current_app.logger.error(
                        f"[SIGNUP] Standalone user initialization failed for user {new_user.id}"
                    )
                    raise Exception("Referral tree initialization error")
                
        # Commit DB if all operations succeeded
        db.session.commit()
        current_app.logger.info('SUCESSFUL REGISTRATION WITH STATUS CHANGE')
        # Success response
        return jsonify({
            "status": "success",
            "message": "Signup successful",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "phone": new_user.phone,
                "referral_code": new_user.referral_code
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print("\n\n=== SIGNUP ERROR ===")
        print(str(e))
        traceback.print_exc()
        print("=== END ERROR ===\n\n")
        return jsonify({"error": "Signup failed. Please try again."}), 500
   
# =============================================
# Authentication Blueprint for Signup, Login
# =============================================

 # --------------------------------------------------
 #      2️⃣ Login Route
 # --------------------------------------------------
@bp.route("/api/login", methods=["POST", "GET"])
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
    
    data = request.get_json()
    email_or_phone = data.get("email_or_phone", "").strip().lower()
    password = data.get("password", "")

    print("Method:", request.method)
    print("Content-Type:", request.headers.get("Content-Type"))
    print("Body:", request.get_data())


    
    if not email_or_phone or not password:
        return jsonify({"error": "Email/Phone and password are required"}), 400

    
    user = User.query.filter(
        (User.email == email_or_phone) | (User.phone == email_or_phone)).first()

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





