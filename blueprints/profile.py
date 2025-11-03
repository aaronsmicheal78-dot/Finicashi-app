
from flask import Blueprint, jsonify, session, render_template, redirect, url_for,g
from models import User

bp = Blueprint('profile',__name__, url_prefix="")

# ----------------------------------------------------------------------------------
# 1️⃣ JAVASCRIPT GETS THIS DATA TO DYNAMICALLY UPDATE/ LOAD USER DATA
# ----------------------------------------------------------------------------------
@bp.route("/user/profile", methods=["GET"])
def get_user_profile():
  
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict()), 200

#==========================================================================
# THIS IS THE PROFILE PAGE FOR USERS

@bp.route("/profile")
def my_profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    user = User.query.get_or_404(session["user_id"])
    return render_template("partials/profile.html", user=user, is_admin_view=False)



#===================================================================================









