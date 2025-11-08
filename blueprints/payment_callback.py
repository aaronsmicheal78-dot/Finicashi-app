from flask import Blueprint, request, jsonify
from models import db, User
from models import Withdrawal

bp = Blueprint("withdraw_callback", __name__, url_prefix="/withdraw")

@bp.route("/pay", methods=["POST"])
def marzpay_callback():
    """
    Receives MarzPay callback after withdrawal attempt.
    Expected JSON: {
        "reference": "uuid or withdraw_id",
        "status": "success" | "failed",
        "transaction_id": "some-id",
        "amount": 1000,
        "phone_number": "+2567xxxxxxx"
    }
    """

    if not request.is_json:
        return jsonify({"error": "Invalid content type"}), 400

    data = request.get_json()

    reference = data.get("reference")
    status = data.get("status")
    transaction_id = data.get("transaction_id")

    if not reference or not status:
        return jsonify({"error": "Missing required fields"}), 400

    # Find the withdrawal record
    withdraw_record = Withdrawal.query.filter_by(id=reference).first()
    if not withdraw_record:
        return jsonify({"error": "Withdrawal reference not found"}), 404

    # Skip if already finalized
    if withdraw_record.status in ("success", "failed"):
        return jsonify({"message": "Already processed"}), 200

    # Update status
    if status.lower() == "success":
        withdraw_record.status = "success"
    else:
        # If failed, refund user balance
        withdraw_record.status = "failed"
        user = User.query.get(withdraw_record.user_id)
        if user:
            user.balance += withdraw_record.amount

    # Optionally store transaction ID for tracking
    withdraw_record.transaction_id = transaction_id if hasattr(withdraw_record, "transaction_id") else None

    db.session.commit()

    return jsonify({
        "message": f"Withdrawal {status} processed successfully",
        "reference": reference
    }), 200
