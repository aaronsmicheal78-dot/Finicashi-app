
from flask import Blueprint, jsonify, session, render_template, redirect, url_for,g, current_app
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

@bp.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile and return fresh data"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

#=======================================================================================
#      USER VERIFICATION ENDPOINT
#=======================================================================================
    
@bp.route("/api/user/<int:user_id>/network", methods=["GET"])
def get_user_network(user_id):
    """
    Get user's referral network for verification and debugging
    """
    try:
        from bonus.refferral_tree import ReferralTreeHelper
        
        network_summary = ReferralTreeHelper.get_user_network_summary(user_id)
        
        return jsonify({
            "success": True,
            "network": network_summary
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting network for user {user_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
#=================================================================================
#==========================================================================
#     # EAGER LOADING before update
#     user = User.query.options(
#         db.joinedload(User.wallet),
#         db.joinedload(User.bonuses),
#         db.joinedload(User.packages).joinedload(Package.catalog)
#     ).filter_by(id=user_id).first()

#     if not user:
#         return jsonify({"error": "User not found"}), 404

#     data = request.get_json()
    
#     # Update fields
#     if 'username' in data:
#         user.username = data['username']
#     if 'email' in data:
#         user.email = data['email']
#     if 'phone' in data:
#         user.phone = data['phone']

#     db.session.commit()
    
#     # Return updated user data with eager loading
#     return jsonify(user.to_dict())

# #======================================================================================
# #=====================================================================================
# @bp.route('/api/admin/users', methods=['GET'])
# def get_all_users():
#     """Get all users for admin dashboard (optimized)"""
#     user_id = session.get('user_id')
#     if not user_id:
#         return jsonify({"error": "Unauthorized"}), 401

#     current_user = User.query.get(user_id)
#     if current_user.role != 'admin':
#         return jsonify({"error": "Admin access required"}), 403

#     #  EAGER LOADING for multiple users
#     users = User.query.options(
#         db.joinedload(User.wallet),
#         db.joinedload(User.bonuses),
#         db.joinedload(User.packages).joinedload(Package.catalog)
#     ).all()

#     return jsonify([user.to_dict() for user in users])
# #====================================================================================================
# #======================================================================================================
# @bp.route('/api/user/current', methods=['GET'])
# def get_current_user():
#     """Get current user with all relationships (optimized)"""
#     user_id = session.get('user_id')
#     if not user_id:
#         return jsonify({"error": "Unauthorized"}), 401

#     #  EAGER LOADING - Prevents N+1 queries
#     user = User.query.options(
#         db.joinedload(User.wallet),
#         db.joinedload(User.bonuses),
#         db.joinedload(User.packages).joinedload(Package.catalog)
#     ).filter_by(id=user_id).first()

#     if not user:
#         return jsonify({"error": "User not found"}), 404

#     return jsonify(user.to_dict())
# #=======================================================================================================






