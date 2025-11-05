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


@admin_bp.route("/admin/data", methods=["GET"])
@admin_required
def admin_data():
    total_users = User.query.count()  # Efficient for most cases; use func.count() for huge tables
    return jsonify({
        "total_users": User.query.count(),
        "active_users": User.query.filter_by(is_active=True).count(),
        "verified_users": User.query.filter_by(is_verified=True).count()


     })

   