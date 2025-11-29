
from flask import Blueprint, jsonify, session, render_template, redirect, url_for,g, current_app
from models import User, db, Package, Wallet, ReferralBonus
from decimal import Decimal, ROUND_DOWN
from flask import session, jsonify, current_app
from datetime import date, datetime
from models import Bonus



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

# #====================================================================================================
# #======================================================================================================
from flask import jsonify, request, current_app

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, and_, or_
import logging

logger = logging.getLogger(__name__)
#=========================================================================
#=======================================================================


@bp.route('/api/user/total-earnings', methods=['GET'])
def get_current_user_total_earnings():
    """
    Calculate total earnings and referral statistics for the currently logged-in user
    """
    print("🎯 EARNINGS ENDPOINT HIT - WITH REFERRAL STATS")
    
    # Use session authentication like your other routes
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({
            "error": "Authentication required",
            "message": "Please log in to access this endpoint"
        }), 401
    
    try:
        from models import User, Wallet, ReferralBonus, Bonus, Transaction, Referral, db
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        print(f"✅ Processing earnings for user: {user.username}")
        
        now = datetime.now(timezone.utc)
        
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        totals = {
            'today': Decimal('0.00'),
            'this_week': Decimal('0.00'),
            'this_month': Decimal('0.00'),
            'breakdown': {
                'referral_bonus': Decimal('0.00'),
                'signup_bonus': Decimal('0.00'),
                'available_balance': Decimal('0.00'),
                'wallet_balance': Decimal('0.00')
            }
        }

        # =========================================================================
        # 1. CALCULATE REFERRAL STATISTICS
        # =========================================================================
        
        # Total direct referrals (users who signed up using this user's referral code)
        total_direct_referrals = db.session.query(
            func.count(Referral.id)
        ).filter(
            Referral.referrer_id == user_id,
            Referral.status == 'active'
        ).scalar() or 0

        # Active referrals (referred users who are active)
        active_referrals = db.session.query(
            func.count(Referral.id)
        ).filter(
            Referral.referrer_id == user_id,
            Referral.status == 'active',
            Referral.referred_id.isnot(None)
        ).scalar() or 0

        # Total network size (from User model)
        total_network_size = user.total_network_size or 0

        # =========================================================================
        # 2. CALCULATE LIFETIME EARNINGS
        # =========================================================================
        
        # Lifetime referral bonuses (all time, not just active)
        lifetime_referral_bonus_raw = db.session.query(
            func.coalesce(func.sum(ReferralBonus.bonus_amount), 0.00)
        ).filter(
            ReferralBonus.user_id == user_id
            # Remove status filter to get ALL historical bonuses
        ).scalar() or 0.00

        # Lifetime signup bonuses (all time)
        lifetime_signup_bonus = db.session.query(
            func.coalesce(func.sum(Bonus.amount), Decimal('0.00'))
        ).filter(
            Bonus.user_id == user_id,
            Bonus.type == 'signup'
            # Remove status filter to get ALL historical bonuses
        ).scalar() or Decimal('0.00')

        # Convert to Decimal for calculation
        lifetime_referral_bonus = Decimal(str(lifetime_referral_bonus_raw))
        
        # Total lifetime earnings (all bonuses ever earned)
        lifetime_earnings = (lifetime_referral_bonus + lifetime_signup_bonus).quantize(Decimal('0.01'), ROUND_HALF_UP)

        # =========================================================================
        # 3. CALCULATE CURRENT PERIOD EARNINGS (existing logic)
        # =========================================================================

        # Current period referral bonuses
        referral_today_raw = db.session.query(
            func.coalesce(func.sum(ReferralBonus.bonus_amount), 0.00)
        ).filter(
            ReferralBonus.user_id == user_id,
            ReferralBonus.status == 'active',
            ReferralBonus.created_at >= today_start
        ).scalar() or 0.00
        
        referral_week_raw = db.session.query(
            func.coalesce(func.sum(ReferralBonus.bonus_amount), 0.00)
        ).filter(
            ReferralBonus.user_id == user_id,
            ReferralBonus.status == 'active',
            ReferralBonus.created_at >= week_start
        ).scalar() or 0.00
        
        referral_month_raw = db.session.query(
            func.coalesce(func.sum(ReferralBonus.bonus_amount), 0.00)
        ).filter(
            ReferralBonus.user_id == user_id,
            ReferralBonus.status == 'active',
            ReferralBonus.created_at >= month_start
        ).scalar() or 0.00

        # Convert all referral amounts to Decimal
        referral_today = Decimal(str(referral_today_raw))
        referral_week = Decimal(str(referral_week_raw))
        referral_month = Decimal(str(referral_month_raw))

        # Current period signup bonuses
        signup_today = db.session.query(
            func.coalesce(func.sum(Bonus.amount), Decimal('0.00'))
        ).filter(
            Bonus.user_id == user_id,
            Bonus.type == 'signup',
            Bonus.status == 'active',
            Bonus.created_at >= today_start
        ).scalar() or Decimal('0.00')

        signup_week = db.session.query(
            func.coalesce(func.sum(Bonus.amount), Decimal('0.00'))
        ).filter(
            Bonus.user_id == user_id,
            Bonus.type == 'signup',
            Bonus.status == 'active',
            Bonus.created_at >= week_start
        ).scalar() or Decimal('0.00')

        signup_month = db.session.query(
            func.coalesce(func.sum(Bonus.amount), Decimal('0.00'))
        ).filter(
            Bonus.user_id == user_id,
            Bonus.type == 'signup',
            Bonus.status == 'active',
            Bonus.created_at >= month_start
        ).scalar() or Decimal('0.00')

        # 4. Get current balances (not time-bound)
        available_balance = user.available_balance if user.available_balance else Decimal('0.00')
        wallet_balance = user.wallet.balance if user.wallet else Decimal('0.00')

        # Calculate period totals
        totals['today'] = (referral_today + signup_today).quantize(Decimal('0.01'), ROUND_HALF_UP)
        totals['this_week'] = (referral_week + signup_week).quantize(Decimal('0.01'), ROUND_HALF_UP)
        totals['this_month'] = (referral_month + signup_month).quantize(Decimal('0.01'), ROUND_HALF_UP)

        # Set breakdown (current state)
        referral_total_raw = db.session.query(
            func.coalesce(func.sum(ReferralBonus.bonus_amount), 0.00)
        ).filter(
            ReferralBonus.user_id == user_id,
            ReferralBonus.status == 'active'
        ).scalar() or 0.00
        
        totals['breakdown']['referral_bonus'] = Decimal(str(referral_total_raw)).quantize(Decimal('0.01'), ROUND_HALF_UP)
        totals['breakdown']['signup_bonus'] = db.session.query(
            func.coalesce(func.sum(Bonus.amount), Decimal('0.00'))
        ).filter(
            Bonus.user_id == user_id,
            Bonus.type == 'signup',
            Bonus.status == 'active'
        ).scalar() or Decimal('0.00')
        totals['breakdown']['available_balance'] = available_balance.quantize(Decimal('0.01'), ROUND_HALF_UP)
        totals['breakdown']['wallet_balance'] = wallet_balance.quantize(Decimal('0.01'), ROUND_HALF_UP)

        # =========================================================================
        # 5. PREPARE COMPREHENSIVE RESPONSE
        # =========================================================================

        response_data = {
            "user_id": user_id,
            "username": user.username,
            
            # Current period earnings
            "today": str(totals['today']),
            "this_week": str(totals['this_week']),
            "this_month": str(totals['this_month']),
            
            # Current balances breakdown
            "breakdown": {
                "referral_bonus": str(totals['breakdown']['referral_bonus']),
                "signup_bonus": str(totals['breakdown']['signup_bonus']),
                "available_balance": str(totals['breakdown']['available_balance']),
                "wallet_balance": str(totals['breakdown']['wallet_balance'])
            },
            
            # NEW: Referral statistics
            "referral_stats": {
                "total_direct_referrals": total_direct_referrals,
                "active_referrals": active_referrals,
                "total_network_size": total_network_size,
                "network_depth": user.network_depth or 0,
                "direct_referrals_count": user.direct_referrals_count or 0
            },
            
            # NEW: Lifetime earnings
            "lifetime_earnings": {
                "total": str(lifetime_earnings),
                "breakdown": {
                    "referral_bonus": str(lifetime_referral_bonus),
                    "signup_bonus": str(lifetime_signup_bonus)
                }
            }
        }

        print(f"✅ Comprehensive stats calculated for user {user_id}")
        print(f"   - Direct referrals: {total_direct_referrals}")
        print(f"   - Network size: {total_network_size}")
        print(f"   - Lifetime earnings: {lifetime_earnings}")
        
        logger.info(f"Comprehensive stats calculated for user {user_id}")

        return jsonify(response_data)

    except Exception as e:
        print(f"💥 Error calculating comprehensive stats for user {user_id}: {str(e)}")
        logger.error(f"Error calculating comprehensive stats for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "message": "Unable to calculate statistics at this time"
        }), 500
@bp.route('/api/user/today-bonus')
def get_today_bonus():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    from bonus.daily import DailyBonusProcessor
    print(DailyBonusProcessor)
    processor = DailyBonusProcessor(user_id)
    bonus_summary = processor.run()  # Returns the dict with keys: total_bonus, packages_successful, packages_failed

    return jsonify({
        "success": True,
        "wallet_balance": bonus_summary["wallet_balance"],
        "total_bonus_today": bonus_summary["total_bonus"],
        "processed_packages": bonus_summary["processed_packages"],
        "packages_completed": bonus_summary["packages_successful"],
        "packages_expired": bonus_summary["packages_failed"]
    })


