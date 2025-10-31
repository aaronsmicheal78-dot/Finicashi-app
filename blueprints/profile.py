
from flask import Blueprint, jsonify, session, render_template, redirect, url_for,g
from models import User

bp = Blueprint('profile',__name__, url_prefix="")

# ----------------------------------------------------------------------------------
# 1️⃣ Get user profile (used by JS loadUserData)
# ----------------------------------------------------------------------------------
@bp.route("/user/profile", methods=["GET"])
def get_user_profile():
    # Assuming user_id is stored in session after login
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict()), 200

#====================================================================================
# @bp.route("/profile/<int:user_id>")
# def profile(user_id):
#         if not g.user:
#             return redirect(url_for("auth.login"))  # Use blueprint route name

#         if g.user.id != user_id:
#             return "Access denied", 403

#         return render_template("partials/profile.html", user=g.user)

# -----------------------------------------------------------------------------
#       Endpoint: Get User Profile
# -------------------------------------------------------------------------------
# @bp.route('/api/user/profile/<int:user_id>', methods=['GET'])
# def get_profile(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         return jsonify({"error": "User not found"}), 404
#     return jsonify(user.to_dict()), 200

#==========================================================================

@bp.route("/profile/<int:user_id>")
def profile_page(user_id):
    if "user_id" not in session:
        return redirect(url_for("index.login"))
    return render_template("partials/profile.html", user_id=user_id)
