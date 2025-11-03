#======================================================================================
#
# THIS IS ADMIN page
#
#=======================================================================================



from flask import render_template, jsonify, request, Blueprint, session, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from extensions import db
from models import User
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


@admin_bp.route("/admin/data")
@admin_required
def admin_data():
    total_users = User.query.count()  # Efficient for most cases; use func.count() for huge tables
    return jsonify({
        "total_users": User.query.count(),
    "total_active_users": User.query.filter_by(is_active=True).count(),
    "verified_users": User.query.filter_by(is_verified=True).count()

    })
# #---------- MAIN DASHBOARD PAGE ----------
# @bp.route('/admin')
# @login_required
# def dashboard():
#     if not current_user.is_admin:
#         return "Access denied", 403
#     if "user_id" not in session:
#         return "Acess denied", 403
#     return render_template('admin/dashboard.html')

# # ---------- API: TOTAL STATS ----------
# @bp.route('/api/overview')
# @login_required
# def overview():
#     if not current_user.is_admin:
#         return jsonify({"error": "unauthorized"}), 403

#     total_users = User.query.count()
#     total_balance = db.session.query(db.func.sum(User.balance)).scalar() or 0
#     total_bonuses = db.session.query(db.func.sum(Bonus.amount)).scalar() or 0
#     total_revenue = (
#         db.session.query(db.func.sum(Investment.amount)).scalar() or 0
#     )

#     return jsonify({
#         "total_users": total_users,
#         "total_balance": total_balance,
#         "total_bonuses": total_bonuses,
#         "total_revenue": total_revenue
#     })


# # ---------- API: DAILY STATS ----------
# @bp.route('/api/daily')
# @login_required
# def daily():
#     if not current_user.is_admin:
#         return jsonify({"error": "unauthorized"}), 403

#     today = date.today()
#     daily_new_users = User.query.filter(db.func.date(User.created_at) == today).count()
#     daily_payouts = db.session.query(db.func.sum(Payout.amount)).filter(
#         db.func.date(Payout.created_at) == today
#     ).scalar() or 0
#     daily_investments = db.session.query(db.func.sum(Investment.amount)).filter(
#         db.func.date(Investment.created_at) == today
#     ).scalar() or 0

#     return jsonify({
#         "daily_new_users": daily_new_users,
#         "daily_payouts": daily_payouts,
#         "daily_investments": daily_investments
#     })


# # ---------- API: SEARCH USER ----------
# @bp.route('/api/user/search')
# @login_required
# def search_user():
#     if not current_user.is_admin:
#         return jsonify({"error": "unauthorized"}), 403

#     query = request.args.get('q', '').strip()
#     if not query:
#         return jsonify([])

#     results = User.query.filter(
#         (User.username.ilike(f'%{query}%')) | (User.email.ilike(f'%{query}%'))
#     ).all()

#     return jsonify([
#         {"id": u.id, "username": u.username, "email": u.email, "balance": u.balance}
#         for u in results
#     ])
