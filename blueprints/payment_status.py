from flask import Blueprint, session, jsonify
from blueprints.payments import bp, PACKAGE_MAP, Payment

bp = Blueprint('payment_status', __name__, url_prefix="")

# -------------------------------------------------------
# GET /api/payment/status/<reference>
# Returns the latest status for a payment
# -------------------------------------------------------

@bp.route("/status/<string:reference>", methods=["GET"])
def payment_status(reference):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    payment = Payment.query.filter_by(reference=reference, user_id=user_id).first()
    if not payment:
        return jsonify({"error": "Payment not found"}), 404

    return jsonify({
        "reference": payment.reference,
        "status": payment.status.value,
        "amount": payment.amount,
        "package": PACKAGE_MAP.get(payment.amount, "Unknown")
    }), 200
