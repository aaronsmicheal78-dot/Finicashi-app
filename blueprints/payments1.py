from flask import Blueprint, request, jsonify, session
from models import db, Transaction, User
from decimal import Decimal, ROUND_DOWN

bp = Blueprint('cash', __name__)




# ----------------------------
# Endpoint: Cash In
# ----------------------------
@bp.route('/api/cashin', methods=['POST'])
def cash_in():
    data = request.get_json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    pack = data.get('pack')
    phone = data.get('phone')

    # Validation
    if not all([user_id, amount, phone, pack]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        amount = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    except:
        return jsonify({"error": "Invalid amount format"}), 400

    if amount < Decimal('10000'):
        return jsonify({"error": "Minimum deposit is UGX 10,000"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Update balance
    try:
        user.balance += amount
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Cash In failed"}), 500

    return jsonify({
        "message": f"Cash In successful: UGX {amount}",
        "balance": float(user.balance)
    })

# ----------------------------
# Endpoint: Cash Out
# ----------------------------
@bp.route('/api/cashout', methods=['POST'])
def cash_out():
    user = session.get("user_id")
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    user_id = data.get('user_id')
    amount = data.get('amount')
    pack = data.get('pack')
    phone = data.get('phone')

    # Validation
    if not all([user_id, amount, phone, pack]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        amount = Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    except:
        return jsonify({"error": "Invalid amount format"}), 400

    if amount < Decimal('10000'):
        return jsonify({"error": "Minimum withdrawal is UGX 10,000"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # Update balance
    try:
        user.balance -= amount
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Cash Out failed"}), 500

    return jsonify({
        "message": f"Withdrawal request submitted: UGX {amount}",
        "balance": float(user.balance)
    })




