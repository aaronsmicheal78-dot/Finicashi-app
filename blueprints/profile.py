
from flask import Blueprint, jsonify, session, render_template, redirect, url_for,g, current_app
from models import User, db, Package, Wallet, ReferralBonus


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


@bp.route('/api/user//total-earnings', methods=['GET'])
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


from decimal import Decimal, ROUND_DOWN
from flask import session, jsonify, current_app
from datetime import date, datetime
from models import Bonus
from bonus.daily import process_user_daily_bonus

@bp.route('/api/user/today-bonus')
def get_today_bonus():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

   
    bonus_summary = process_user_daily_bonus(user_id)

    return jsonify({
        "success": True,
        "wallet_balance": bonus_summary["wallet_balance"],
        "total_bonus_today": bonus_summary["total_bonus_today"],
        "processed_packages": bonus_summary["processed_packages"],
        "packages_completed": bonus_summary["packages_completed"],
        "packages_expired": bonus_summary["packages_expired"]
    })

@bp.route('/api/user//////////today-bonus', methods=['GET'])
def get_today_bonuss():
    """Automatically process and return today's bonus for the logged-in user"""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not logged in", "has_bonus": False}), 401

        user = User.query.get(user_id)
        if not user or not user.is_active:
            session.clear()
            return jsonify({"error": "User not found or inactive", "has_bonus": False}), 404

        # Automatically process daily bonus for the user
        from bonus.daily import process_user_daily_bonus
        bonus_summary = process_user_daily_bonus(user_id)

        response = {
            "has_bonus": bonus_summary["total_bonus_today"] > 0,
            "bonus_amount": bonus_summary["total_bonus_today"],
            "wallet_balance": bonus_summary["wallet_balance"],
            "packages_processed": bonus_summary["packages_processed"],
            "packages_expired": bonus_summary["packages_expired"],
            "packages_completed": bonus_summary["packages_completed"],
            "processed_packages": bonus_summary["processed_packages"],
            "message": f"Daily bonus processed: {bonus_summary['total_bonus_today']:.2f}" if bonus_summary["total_bonus_today"] > 0 else "No bonus to process today",
            "next_bonus_available": (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        return jsonify(response), 200

    except Exception as e:
        current_app.logger.error(f"Error processing/getting today's bonus: {e}", exc_info=True)
        return jsonify({
            "has_bonus": False,
            "error": "Failed to process bonus",
            "details": str(e)
        }), 500

@bp.route('/api////claim-daily-bonus', methods=['POST'])
def claim_daily_bonuss():
    """
    Claim daily bonus for authenticated user
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401
        from bonus.daily import process_user_daily_bonus
        # Process daily bonus using the enhanced processor
        result = process_user_daily_bonus(user_id)
        
        # Check if processing was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Failed to process daily bonus")
            logger.warning(f"Daily bonus processing failed for user {user_id}: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400

        # Check if any bonus was awarded
        if result["total_bonus_today"] <= 0:
            return jsonify({
                "success": True,
                "message": "No daily bonus available at this time",
                "bonus_amount": 0.0,
                "wallet_balance": result["wallet_balance"],
                "package_summary": {
                    "total_packages": result["packages_processed"] + result["packages_completed"] + 
                                    result["packages_expired"] + result["packages_skipped"],
                    "packages_processed": result["packages_processed"],
                    "packages_completed": result["packages_completed"],
                    "packages_expired": result["packages_expired"],
                    "packages_skipped": result["packages_skipped"]
                },
                "processed_packages": result["processed_packages"],
                "skipped_packages": result.get("skipped_packages", [])
            }), 200

        # Successful bonus claim
        return jsonify({
            "success": True,
            "message": "Daily bonus claimed successfully!",
            "bonus_amount": result["total_bonus_today"],
            "wallet_balance": result["wallet_balance"],
            "package_summary": {
                "total_packages": result["packages_processed"] + result["packages_completed"] + 
                                result["packages_expired"] + result["packages_skipped"],
                "packages_processed": result["packages_processed"],
                "packages_completed": result["packages_completed"],
                "packages_expired": result["packages_expired"],
                "packages_skipped": result["packages_skipped"]
            },
            "processed_packages": result["processed_packages"],
            "skipped_packages": result.get("skipped_packages", [])
        }), 200

    except Exception as e:
        logger.error(f"Unexpected error in claim_daily_bonus route: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred while processing your request"
        }), 500

    
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta
import uuid
import logging
from flask import session, jsonify
from models import Wallet, Transaction

logger = logging.getLogger(__name__)

@bp.route('/api///////claim-daily-bonus', methods=['POST'])
def claim_daily_bonusss():
    """
    Claim daily bonus for active packages using Flask session authentication
    with comprehensive error handling and proper decimal arithmetic.
    """
    db_session = db.session
    
    try:
        # Session-based authentication
        if 'user_id' not in session:
            logger.warning("Unauthorized bonus claim attempt - no user in session")
            return jsonify({"error": "Authentication required"}), 401

        user_id = session['user_id']
        logger.info(f"Daily bonus claim attempt for user {user_id}")

        # Fetch user from database
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User not found in database for session user_id: {user_id}")
            session.clear()  # Clear invalid session
            return jsonify({"error": "User not found"}), 404

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted bonus claim: {user_id}")
            return jsonify({"error": "Account is inactive"}), 403

        # Fetch wallet with error handling
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
    
            wallet = Wallet(user_id=user.id, balance=0)
            db.session.add(wallet)
            db.session.commit()
        print(f"DEBUG: Before update - Wallet balance: {wallet.balance}")
        if not wallet:
            logger.error(f"Wallet not found for user {user_id}")
            return jsonify({"error": "Wallet not found"}), 404

        # Fetch active packages
        packages = Package.query.filter_by(user_id=user_id, status='active').all()
        if not packages:
            logger.info(f"No active packages found for user {user_id}")
            return jsonify({
                "error": "No active packages found",
                "suggestion": "Please purchase a package to start earning daily bonuses"
            }), 400

        # Check if user already claimed bonus today
        today = datetime.utcnow().date()
        already_claimed = Bonus.query.filter(
            Bonus.user_id == user_id,
            Bonus.type == "daily",
            db.func.date(Bonus.created_at) == today
        ).first()

        if already_claimed:
            logger.info(f"User {user_id} already claimed daily bonus today")
            # Calculate next available time (next day)
            next_claim_time = (datetime.utcnow() + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            return jsonify({
                "error": "Daily bonus already claimed today",
                "next_available": next_claim_time.isoformat(),
                "next_available_human": next_claim_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            }), 400

        # Initialize bonus calculation
        total_bonus_today = Decimal("0.00")
        now = datetime.utcnow()
        packages_updated = []
        expired_packages = []
        completed_packages = []

        # Calculate bonus for each package
        for pkg in packages:
            try:
                # Validate package data
                if not pkg.package_amount or pkg.package_amount <= Decimal("0"):
                    logger.warning(f"Invalid package amount for package {pkg.id}")
                    continue

                # Check package expiry (60 days from activation)
                if pkg.activated_at:
                    expiry_date = pkg.activated_at + timedelta(days=60)
                else:
                    expiry_date = pkg.created_at + timedelta(days=60)
                    
                if now > expiry_date:
                    logger.info(f"Package {pkg.id} expired for user {user_id}")
                    pkg.status = "expired"
                    expired_packages.append({
                        "package_id": pkg.id,
                        "package_name": pkg.package,
                        "expired_at": expiry_date.isoformat()
                    })
                    db_session.add(pkg)
                    continue

                # Calculate daily bonus (2.5%)
                try:
                    daily_bonus_raw = Decimal(str(pkg.package_amount)) * Decimal("0.025")
                    daily_bonus = daily_bonus_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Bonus calculation error for package {pkg.id}: {e}")
                    continue

                # Calculate maximum payout (75% of package amount)
                try:
                    max_payout = Decimal(str(pkg.package_amount)) * Decimal("0.75")
                    current_total_paid = Decimal(str(pkg.total_bonus_paid or "0"))
                    remaining_limit = max_payout - current_total_paid
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Payout calculation error for package {pkg.id}: {e}")
                    continue

                # Skip if remaining limit is zero or negative
                if remaining_limit <= Decimal("0"):
                    pkg.status = "completed"
                    db_session.add(pkg)
                    completed_packages.append({
                        "package_id": pkg.id,
                        "package_name": pkg.package,
                        "total_paid": float(current_total_paid),
                        "max_payout": float(max_payout)
                    })
                    logger.info(f"Package {pkg.id} reached maximum payout")
                    continue

                # Cap bonus if it exceeds remaining limit
                if daily_bonus > remaining_limit:
                    daily_bonus = remaining_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    logger.info(f"Bonus capped for package {pkg.id}: {daily_bonus}")

                # Validate bonus amount
                if daily_bonus <= Decimal("0"):
                    logger.warning(f"Invalid bonus amount {daily_bonus} for package {pkg.id}")
                    continue

                # Accumulate total bonus
                total_bonus_today += daily_bonus

                # Update package payout tracking
                try:
                    pkg.total_bonus_paid = current_total_paid + daily_bonus
                    
                    # Check if package reached maximum payout after this bonus
                    if pkg.total_bonus_paid >= max_payout:
                        pkg.status = "completed"
                        completed_packages.append({
                            "package_id": pkg.id,
                            "package_name": pkg.package,
                            "total_paid": float(pkg.total_bonus_paid),
                            "max_payout": float(max_payout)
                        })
                        logger.info(f"Package {pkg.id} completed maximum payout")
                    else:
                        packages_updated.append({
                            "package_id": pkg.id,
                            "package_name": pkg.package,
                            "bonus_today": float(daily_bonus),
                            "total_paid": float(pkg.total_bonus_paid),
                            "remaining_limit": float(remaining_limit - daily_bonus)
                        })
                    
                    db_session.add(pkg)
                    
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Error updating package {pkg.id} payout: {e}")
                    continue

            except Exception as pkg_error:
                logger.error(f"Error processing package {pkg.id}: {pkg_error}")
                continue  # Continue with other packages

        # Validate total bonus
        if total_bonus_today <= Decimal("0"):
            logger.info(f"No bonus available for user {user_id}")
            return jsonify({
                "error": "No bonus available to claim today",
                "details": {
                    "expired_packages": expired_packages,
                    "completed_packages": completed_packages,
                    "total_packages_checked": len(packages)
                },
                "suggestion": "All packages are either expired, completed, or have issues"
            }), 400

        max_reasonable_bonus = Decimal("100000.00")  
        if total_bonus_today > max_reasonable_bonus:
            logger.error(f"Suspicious bonus amount {total_bonus_today} for user {user_id}")
            return jsonify({"error": "Bonus calculation error - amount too high"}), 500

       
        min_bonus = Decimal("0.01")
        if total_bonus_today < min_bonus:
            logger.info(f"Bonus too small to process: {total_bonus_today}")
            return jsonify({
                "error": "Bonus amount too small to process",
                "minimum_bonus": float(min_bonus)
            }), 400

        try:
            bonus_record = Bonus(
                user_id=user_id,
                type="daily",
                amount=total_bonus_today,
                status="active",
                created_at=datetime.utcnow()
            )
            db_session.add(bonus_record)
        except Exception as e:
            logger.error(f"Error creating bonus record: {e}")
            return jsonify({"error": "Failed to create bonus record"}), 500

       
        try:
            current_balance = Decimal(str(wallet.balance or "0"))
            new_balance = current_balance + total_bonus_today
            wallet.balance = new_balance
            print(f"DEBUG: After update - Wallet balance: {wallet.balance}")
            wallet.updated_at = datetime.utcnow()
            db_session.add(wallet)
        except (InvalidOperation, TypeError) as e:
            logger.error(f"Error updating wallet balance: {e}")
            return jsonify({"error": "Failed to update wallet balance"}), 500

        # Create transaction record
        try:
            transaction_ref = f"BONUS-{uuid.uuid4().hex[:10].upper()}"
            if not transaction_ref:
               raise Exception("Transaction reference generation failed")
            transaction = Transaction(
                wallet_id=wallet.id,
                type="bonus",
                amount=total_bonus_today,
                status="successful",
                reference=transaction_ref,
                created_at=datetime.utcnow()
            )
            db_session.add(transaction)
        except Exception as e:
            logger.error(f"Error creating transaction record: {e}")
            transaction_ref = "NO-REF"
       
        db_session.commit() 
        logger.info(f"Daily bonus claimed successfully for user {user_id}: {total_bonus_today}")

        response_data = {
            "success": True,
            "message": "Daily bonus claimed successfully!",
            "bonus_amount": float(total_bonus_today),
            "wallet_balance": float(wallet.balance),
            "transaction_reference": transaction_ref,
            "claimed_at": datetime.utcnow().isoformat(),
            "package_summary": {
                "total_packages": len(packages),
                "packages_processed": len(packages_updated),
                "packages_expired": len(expired_packages),
                "packages_completed": len(completed_packages)
            },
            "next_bonus_available": (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        if packages_updated:
            response_data["processed_packages"] = packages_updated
        if expired_packages:
            response_data["expired_packages"] = expired_packages
        if completed_packages:
            response_data["completed_packages"] = completed_packages

        return jsonify(response_data), 200

    except Exception as e:
       
        db_session.rollback()
        user_id = session.get('user_id', 'unknown')
        logger.error(f"Unexpected error in claim_daily_bonus for user {user_id}: {str(e)}", exc_info=True)
        
        return jsonify({
            "success": False,
            "error": "Failed to process bonus claim",
            "details": "Internal server error occurred",
            "support_reference": f"ERR-{uuid.uuid4().hex[:8].upper()}"
        }), 500