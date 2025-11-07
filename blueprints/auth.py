
from flask import request, jsonify, session, render_template, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Transaction, Bonus
import re, secrets, string
from utils import validate_email, validate_phone 
from flask import Blueprint, jsonify, request, session
from extensions import db
import logging
import string
import secrets
from flask_login import login_user




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
# blueprints/auth.py
# =============================================
# Authentication Blueprint for Signup, Login, Logout
# =============================================
@bp.route("/api/signup", methods=["POST"])
def signup():
    """
    Create a new user account with proper error handling and transactions
    """
    try:
        data = request.get_json()
        
        print(f"✅ Received signup data: {data}")
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400

        # Fix field names to match frontend
        username = data.get("fullName", "").strip()
        email = data.get("email", "").strip().lower()
        phone = data.get("phone", "").strip()
        password = data.get("password", "")

        print(f"✅ Parsed fields - username: '{username}', email: '{email}', phone: '{phone}', password: {'*' * len(password)}")

        # Validation
        if not all([username, email, phone, password]):
            return jsonify({"error": "All fields are required"}), 400

        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # Check for existing user within transaction
        existing_user = User.query.filter(
            (User.email == email) | (User.phone == phone)
        ).first()
        
        if existing_user:
            print(f"❌ User already exists: {existing_user.email} or {existing_user.phone}")
            return jsonify({"error": "Email or phone already exists"}), 400

        print("✅ No existing user found, creating new user...")

        # Generate referral code 
        def generate_referral_code(length=8):
            characters = string.ascii_uppercase + string.digits
            for attempt in range(10):  # Safety limit to prevent infinite loops
                code = ''.join(secrets.choice(characters) for _ in range(length))
                if not User.query.filter_by(referral_code=code).first():
                    return code
            # Fallback if no unique code found after 10 attempts
            return ''.join(secrets.choice(characters) for _ in range(length))

       #  Create user with proper session management
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            referral_code=generate_referral_code()
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

         #offer signup bonus
        signup_bonus = Bonus(
        user_id=new_user.id,
        amount=5000,          
        type="signup",
        status="active")

 
        db.session.add(signup_bonus)
        db.session.commit()

        return jsonify({
            "message": "Signup successful!",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }), 201

    except Exception as e:
        db.session.rollback()            #    Critical for failed transactions
        print(f"❌ Signup error: {str(e)}")
        import traceback
        traceback.print_exc()            #   This will show the full stack trace
        return jsonify({"error": "Internal server error"}), 500

# # --------------------------------------------------
# #      2️⃣ Login Route
# # --------------------------------------------------
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
    data = request.get_json()
    email_or_phone = data.get("email_or_phone", "").strip().lower()
    password = data.get("password", "")

    # ✅ Validate input
    if not email_or_phone or not password:
        return jsonify({"error": "Email/Phone and password are required"}), 400

    # ✅ Find user by email or phone
    user = User.query.filter(
        (User.email == email_or_phone) | (User.phone == email_or_phone)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    # ✅ Set session
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




