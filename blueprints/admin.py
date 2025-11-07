#======================================================================================
#
# THIS IS ADMIN page
#
#=======================================================================================



from flask import render_template, jsonify, request, Blueprint, session, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from extensions import db
from models import User, Payment, Bonus, Withdrawal
from models import PaymentStatus
from functools import wraps

def admin_required(f):
    """
    Decorator to restrict access to admin-only routes.
    - Checks that 'user_id' exists in session.
    - Fetches the user from the database (to get current is_admin status).
    - Aborts with 403 Forbidden if not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Check if user is logged in
        if "user_id" not in session:
            abort(403)  # Forbidden — not logged in

        user_id = session["user_id"]

        # 2. Fetch user from DB (never trust session for roles!)
        user = User.query.get(user_id)
        if not user:
            abort(403)  # User doesn't exist (e.g., deleted)

        # 3. Check admin status
        if user.role != "admin":
            abort(403)  # Not an admin

        # 4. Allow access
        return f(*args, **kwargs)

    return decorated_function


admin_bp = Blueprint('admin', __name__, url_prefix='' )


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("index.html"))
    
    current_user = User.query.get(session["user_id"])
    if not current_user or current_user.role != "admin":  
        abort(403)
    
    return render_template("partials/admin.html")

# @admin_bp.route("/admin/data", methods=["GET"])
# @admin_required
# def admin_data():
#     total_users = User.query.count()
#     active_users = User.query.filter_by(is_active=True).count()
#     verified_users = User.query.filter_by(is_verified=True).count()
#     daily_new_users = User.query.filter(db.func.date(User.created_at) == date.today()).count()

#     total_payments = User.query.count()
#     pending_payments = User.query.filter_by(status="pending").count()
#     completed_payments = User.query.filter_by(status="completed").count()
#     total_bonus = User.query.with_entities(db.func.sum(User.bonus_amount)).scalar() or 0
#     pending_bonus = User.query.with_entities(db.func.sum(User.bonus_amount)).filter(User.bonus_status == "pending").scalar() or 0
#     daily_payouts = User.query.with_entities(db.func.sum(User.withdrawal_amount)).scalar() or 0

#     return jsonify({
#         "total_users": total_users,
#         "active_users": active_users,
#         "verified_users": verified_users,
#         "daily_new_users": daily_new_users,
#         "total_payments": total_payments,
#         "pending_payments": pending_payments,
#         "completed_payments": completed_payments,
#         "total_bonus": total_bonus,
#         "pending_bonus": pending_bonus,
#         "daily_payouts": daily_payouts
#     })
    
# @admin_bp.route("/admin/data", methods=["GET"])
# @admin_required
# def admin_data():
#     total_users = User.query.count()
    
#     user_stats = {
#         "total_users": total_users,
#         "active_users": User.query.filter_by(is_active=True).count(),
#         "verified_users": User.query.filter_by(is_verified=True).count(),
#         "daily_new_users": User.query.filter(db.func.date(User.created_at) == date.today()).count()
#     }
    
#     payment_stats = {
#         "total_payments": User.query.filter_by(User.payment_status.isnot(None)).count(),
#         "pending_payments": User.query.filter_by(payment_status="pending").count(),
#         "completed_payments": User.query.filter_by(payment_status="completed").count(),
#         "total_bonus": User.query.with_entities(db.func.sum(User.bonus_amount)).scalar() or 0,
#         "pending_bonus": User.query.with_entities(db.func.sum(User.bonus_amount)).filter(User.bonus_status=="pending").scalar() or 0,
#         "daily_payouts": User.query.with_entities(db.func.sum(User.withdrawal_amount)).scalar() or 0
#     }
    
#     return jsonify({**user_stats, **payment_stats})

@admin_bp.route("/admin/data", methods=["GET"])
@admin_required
def admin_data():
    today = date.today()

    total_users = User.query.count()
    
    active_users = User.query.filter_by(is_active=True).count()
    verified_users = User.query.filter_by(is_verified=True).count()
    daily_new_users = User.query.filter(db.func.date(User.created_at) == today).count()

    total_payments = Payment.query.count()
    pending_payments = Payment.query.filter_by(status=PaymentStatus.PENDING).count()

    completed_payments = Payment.query.filter_by(status=PaymentStatus.SUCCESS).count()
    total_bonus = Bonus.query.with_entities(db.func.sum(Bonus.amount)).scalar() or 0
    pending_bonus = Bonus.query.filter_by(status="pending").with_entities(db.func.sum(Bonus.amount)).scalar() or 0
    daily_payouts = Withdrawal.query.filter(db.func.date(Withdrawal.created_at) == today).with_entities(db.func.sum(Withdrawal.amount)).scalar() or 0
   # daily_deductions = Withdrawal.query.filter(db.func.date(Withdrawal.created_at) == today).with_entities(db.func.sum(Withdrawal.fee)).scalar() or 0
    #daily_investments = Payment.query.filter(db.func.date(Payment.created_at) == today, Payment.status==PaymentStatus.SUCCESS).with_entities(db.func.sum(Payment.amount)).scalar() or 0
    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "verified_users": verified_users,
        "daily_new_users": daily_new_users,
        "total_payments": total_payments,
        "pending_payments": pending_payments,
        "completed_payments": completed_payments,
        "total_bonus": total_bonus,
        "pending_bonus": pending_bonus,
        "daily_payouts": daily_payouts,
      #  "daily_deductions": daily_deductions,
       # "daily_investments": daily_investments

    })