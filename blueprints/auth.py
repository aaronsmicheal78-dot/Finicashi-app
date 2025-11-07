
from flask import Flask, request, jsonify, session, render_template, Blueprint
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Transaction, Bonus
import re, secrets, string
from utils import validate_email, validate_phone 
from flask import Blueprint, jsonify, request, session
from extensions import db
import logging
import string
import secrets




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
# --------------------------------------------------
# 1️⃣ Signup Route
# # --------------------------------------------------
# @bp.route("/api/signup", methods=["POST"])
# def signup():
#     """
#     Create a new user account.
#     Expected JSON:
#     {
#         "FullName": "",
#         "email": "",
#         "phone": "",
#         "password": ""
#     }
#     """
#     data = request.get_json()

#     username = data.get("fullName", "").strip()
#     email = data.get("email", "").strip().lower()
#     phone = data.get("phone", "").strip()
#     password = data.get("password", "")

#     # ✅ Validation checks
#     if not all([username, email, phone, password]):
#         return jsonify({"error": "All fields are required"}), 400

#     if User.query.filter((User.email == email) | (User.phone == phone)).first():
#         return jsonify({"error": "Email or phone already exists"}), 400

#     # ✅ Create user
#     new_user = User(
#         username=username,
#         email=email,
#         phone=phone,
#     )
#     new_user.set_password(password)

#     #generate a random 8-character alphanumeric referral code
#     def generate_referral_code(length=8):
#         characters = string.ascii_uppercase + string.digits
#         while True:
#             code = ''.join(secrets.choice(characters) for _ in range(length))
#             # Ensure uniqueness
#             if not User.query.filter_by(referral_code=code).first():
#                 return code

#     # Generate a unique referral code
#     referral_code = generate_referral_code()
#     new_user.referral_code = referral_code

#     # Build a referral link
#     base_url = "https://finicashi.com/referral"
#     referral_link = f"{base_url}/{username}/{referral_code}"
#     # we store referral_link in DB if you have a separate field
#     new_user.referral_link = referral_link

#     db.session.add(new_user)
#     db.session.commit()

#   

#     session["user_id"] = new_user.id  # auto-login after signup
#      # Include referral link in response
#     user_data = new_user.to_dict()
#     user_data["referralLink"] = referral_link  # dynamic referral link

#     return jsonify({
#         "message": "Signup successful!",
#         "user": new_user.to_dict()
#     }), 201

# @bp.route("/api/signup", methods=["POST"])
# def signup():
#     try:
#        data = request.get_json()
        
#        print(f"✅ Received signup data: {data}")
        
#         # DEBUG: Show all existing users
#     except:
#         all_users = User.query.all()
#         print("📋 ALL EXISTING USERS IN DATABASE:")
#         for user in all_users:
#             print(f"   - ID: {user.id}, Email: {user.email}, Phone: {user.phone}")
        
#         # Rest of your code...
# # --------------------------------------------------
# # 2️⃣ Login Route
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

# @bp.route("/api/signup", methods=["POST"])
# def signup():
#     """
#     Create a new user account with proper error handling and transactions
#     """
#     try:
#         data = request.get_json()
        
#         print(f"✅ Received signup data: {data}")
        
#         if not data:
#             return jsonify({"error": "No JSON data received"}), 400

#         # Fix field names to match frontend
#         username = data.get("fullName", "").strip()
#         email = data.get("email", "").strip().lower()
#         phone = data.get("phone", "").strip()
#         password = data.get("password", "")

#         print(f"✅ Parsed fields - username: '{username}', email: '{email}', phone: '{phone}', password: {'*' * len(password)}")

#         # Validation
#         if not all([username, email, phone, password]):
#             return jsonify({"error": "All fields are required"}), 400

#         if len(password) < 6:
#             return jsonify({"error": "Password must be at least 6 characters"}), 400

#         # Check for existing user within transaction
#         existing_user = User.query.filter(
#             (User.email == email) | (User.phone == phone)
#         ).first()
        
#         if existing_user:
#             print(f"❌ User already exists: {existing_user.email} or {existing_user.phone}")
#             return jsonify({"error": "Email or phone already exists"}), 400

#         print("✅ No existing user found, creating new user...")

#         # ✅ ADD THESE IMPORTS AT THE TOP OF YOUR FUNCTION
#         import string
#         import secrets

#         # Generate referral code (complete the function)
#         def generate_referral_code(length=8):
#             characters = string.ascii_uppercase + string.digits
#             for attempt in range(10):  # Safety limit to prevent infinite loops
#                 code = ''.join(secrets.choice(characters) for _ in range(length))
#                 if not User.query.filter_by(referral_code=code).first():
#                     return code
#             # Fallback if no unique code found after 10 attempts
#             return ''.join(secrets.choice(characters) for _ in range(length))

#         # ✅ Create user with proper session management
#         new_user = User(
#             username=username,
#             email=email,
#             phone=phone,
#             referral_code=generate_referral_code()
#         )
#         new_user.set_password(password)

#         print(f"✅ User object created: {new_user}")

#         # Add to session and commit
#         db.session.add(new_user)
#         db.session.commit()

#         print("✅ User saved to database successfully!")

#         return jsonify({
#             "message": "Signup successful!",
#             "user": {
#                 "id": new_user.id,
#                 "username": new_user.username,
#                 "email": new_user.email
#             }
#         }), 201

#     except Exception as e:
#         db.session.rollback()  # Critical for failed transactions
#         print(f"❌ Signup error: {str(e)}")
#         import traceback
#         traceback.print_exc()  # This will show the full stack trace
#         return jsonify({"error": "Internal server error"}), 500
# # --------------------------------------------------
# # 3️⃣------------Logout Route-----------------------
# --------------------------------------------------
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


 # blueprints/profile.py
# =============================================
# Profile API Blueprint (connects to JS)
# =============================================




# --------------------------------------------------
# 2️⃣ Cash In Endpoint
# --------------------------------------------------
@bp.route("/cashin", methods=["POST"])
def cashin():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    amount = float(data.get("amount", 0))
    phone = data.get("phone")
    pack = data.get("pack")

    if amount < 10000:
        return jsonify({"error": "Minimum deposit is UGX 10,000"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 2.9% fee
    fee = round(amount * 0.029, 2)
    total = amount - fee

    # Update user balance (simulate payment success)
    user.balance += total

    # Record transaction
    txn = Transaction(user_id=user.id, type="cashin", amount=amount, fee=fee, phone=phone, status="success")
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "message": f"Deposit of {amount} UGX successful!",
        "balance": user.balance
    }), 200


# --------------------------------------------------
# 3️⃣ Cash Out Endpoint
# --------------------------------------------------
@bp.route("/cashout", methods=["POST"])
def cashout():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    amount = float(data.get("amount", 0))
    phone = data.get("phone")
    pack = data.get("pack")

    if amount < 10000:
        return jsonify({"error": "Minimum withdrawal is UGX 10,000"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # 1% fee
    fee = round(amount * 0.01, 2)
    net = amount - fee

    # Deduct from user balance
    user.balance -= amount

    # Record transaction
    txn = Transaction(user_id=user.id, type="cashout", amount=amount, fee=fee, phone=phone, status="processing")
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "message": f"Withdrawal of {net} UGX initiated successfully!",
        "balance": user.balance
    }), 200

