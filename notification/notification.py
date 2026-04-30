# routes/notifications.py

from flask import jsonify, Blueprint, session
from models import Notification, User
from extensions import db

notification_bp = Blueprint("notifications", __name__)


def get_current_user():
    """Helper: get authenticated user safely"""
    user_id = session.get("user_id")
    if not user_id:
        return None

    return User.query.get(user_id)


@notification_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get latest notifications for logged-in user"""

    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        notifications = (
            Notification.query
            .filter_by(user_id=user.id)
            .order_by(Notification.created_at.desc())
            .limit(10)
            .all()
        )

        return jsonify([n.to_dict() for n in notifications]), 200

    except Exception:
        return jsonify({"error": "Failed to fetch notifications"}), 500


@notification_bp.route('/api/notifications/<int:notif_id>/read', methods=['PUT'])
def mark_notification_read(notif_id):
    """Mark notification as read"""

    try:
        user = get_current_user()
        if not user:
            return jsonify({"error": "Unauthorized"}), 401

        notification = Notification.query.get(notif_id)
        if not notification:
            return jsonify({"error": "Notification not found"}), 404

        # 🔐 Security check (VERY IMPORTANT)
        if notification.user_id != user.id:
            return jsonify({"error": "Forbidden"}), 403

        notification.is_read = True
        db.session.commit()

        return jsonify({"success": True}), 200

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Failed to update notification"}), 500