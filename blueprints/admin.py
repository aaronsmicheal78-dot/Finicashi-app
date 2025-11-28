#======================================================================================
#
# THIS IS ADMIN page
#
#=======================================================================================



from flask import render_template, jsonify, request, Blueprint, session, redirect, url_for, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from extensions import db
from models import User, Payment, Bonus, Withdrawal, ReferralBonus, PackageCatalog, Package
from models import PaymentStatus, Wallet, Transaction
from functools import wraps
from sqlalchemy import or_
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """
    Decorator to restrict access to admin-only routes.
    - Checks that 'user_id' exists in session.
    - Fetches the user from the database (to get current is_admin status).
    - Aborts with 403 Forbidden if not an admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
       
        if "user_id" not in session:
            abort(403)  

        user_id = session["user_id"]

        user = User.query.get(user_id)
        if not user:
            abort(403)  

        
        if user.role != "admin":
            abort(403)  

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
    today = date.today()

    total_users = User.query.count()
    
    active_users = User.query.filter_by(is_active=True).count()
    verified_users = User.query.filter_by(is_verified=True).count()
    daily_new_users = User.query.filter(db.func.date(User.created_at) == today).count()

    total_payments = Payment.query.count()
    pending_payments = Payment.query.filter_by(status=PaymentStatus.PENDING.value).count()

    completed_payments = Payment.query.filter_by(status=PaymentStatus.COMPLETED.value).count()
    total_bonus = Bonus.query.count()
    pending_bonus = Bonus.query.filter_by(status="pending").with_entities(db.func.sum(Bonus.amount)).scalar() or 0
    daily_payouts = Withdrawal.query.filter(db.func.date(Withdrawal.created_at) == today).with_entities(db.func.sum(Withdrawal.amount)).scalar() or 0
    #daily_deductions = Withdrawal.query.filter(db.func.date(Withdrawal.created_at) == today).with_entities(db.func.sum(Withdrawal.fee)).scalar() or 0
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


#============================================================================================================
#
#     ----------------------------ADMIN SEARCH FUNCTIONALITY-------------------------------------------
#-----------DASHBOARD COMPLETE SEARCH SYSTEM FOR USERS, BALANCES, AND PAYMENTS---------------------
#
#============================================================================================================

@admin_bp.route('/admin/search', methods=['GET'])
def admin_search():
    """Admin search across users, payments, and bonuses"""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'users': [],
                'payments': [],
                'bonuses': [],
                'message': 'Please provide a search query'
            }), 400

        # Search across different models  
        users = search_users(query)
        payments = search_payments(query)
        bonuses = search_bonuses(query)

        return jsonify({
            'users': users,
            'payments': payments,
            'bonuses': bonuses,
            'total_results': len(users) + len(payments) + len(bonuses)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def search_users(query):
    """Search users by username, email, phone, referral code, or ID"""
    try:
        # Check if query is numeric (could be user ID)
        if query.isdigit():
            users = User.query.filter(
                or_(
                    User.id == int(query),  # UNCOMMENT THIS
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%'),
                    User.phone.ilike(f'%{query}%'),
                    User.referral_code.ilike(f'%{query}%')
                )
            ).limit(50).all()
        else:
            users = User.query.filter(
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.email.ilike(f'%{query}%'),
                    User.phone.ilike(f'%{query}%'),
                    User.referral_code.ilike(f'%{query}%')
                )
            ).limit(50).all()

        return [user_to_search_dict(user) for user in users]
    except Exception as e:
        print(f"Error searching users: {e}")
        return []

def search_payments(query):
    """Search payments by reference, external_ref, phone, or ID"""
    try:
        # Check if query is numeric (could be payment ID or amount)
        if query.isdigit():
            payments = Payment.query.filter(
                or_(
                    Payment.id == int(query),
                    Payment.reference.ilike(f'%{query}%'),
                    Payment.external_ref.ilike(f'%{query}%'),
                    Payment.phone_number.ilike(f'%{query}%'),
                    Payment.amount == float(query)
                )
            ).limit(50).all()
        else:
            payments = Payment.query.filter(
                or_(
                    Payment.reference.ilike(f'%{query}%'),
                    Payment.external_ref.ilike(f'%{query}%'),
                    Payment.phone_number.ilike(f'%{query}%')
                )
            ).limit(50).all()

        return [payment_to_search_dict(payment) for payment in payments]
    except Exception as e:
        print(f"Error searching payments: {e}")
        return []

def search_bonuses(query):
    """Search bonuses by type, status, or user attributes"""
    try:
        # Search in Bonus model - only one foreign key to User
        bonuses_query = Bonus.query.join(User, Bonus.user_id == User.id).filter(
            or_(
                Bonus.type.ilike(f'%{query}%'),
                Bonus.status.ilike(f'%{query}%'),
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.phone.ilike(f'%{query}%')
            )
        ).limit(50).all()

        # Search in ReferralBonus model - explicitly specify which foreign key to use
        referral_bonuses_query = ReferralBonus.query.join(
            User, ReferralBonus.user_id == User.id  # Explicitly join on user_id (the bonus receiver)
        ).filter(
            or_(
                ReferralBonus.type.ilike(f'%{query}%'),
                ReferralBonus.status.ilike(f'%{query}%'),
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%'),
                User.phone.ilike(f'%{query}%')
            )
        ).limit(50).all()

        all_bonuses = list(bonuses_query) + list(referral_bonuses_query)
        
        return [bonus_to_search_dict(bonus) for bonus in all_bonuses]
    except Exception as e:
        print(f"Error searching bonuses: {e}")
        import traceback
        traceback.print_exc()
        return []

def user_to_search_dict(user):
    """Serialize user for search results - FIXED for your model"""
    return {
        'type': 'user',
        'id': user.id,  
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'actual_balance': float(user.actual_balance or 0), 
        'available_balance': float(user.available_balance or 0),  
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'member_since': user.member_since.isoformat() if user.member_since else None,
        'wallet_balance': float(user.wallet.balance) if user.wallet else 0
    }

def payment_to_search_dict(payment):
    """Serialize payment for search results - FIXED status"""
    return {
        'type': 'payment',
        'id': payment.id,
        'reference': payment.reference,
        'external_ref': payment.external_ref,
        'amount': float(payment.amount or 0),
        'currency': payment.currency,
        'status': payment.status,  
        'phone_number': payment.phone_number,
        'verified': payment.verified,
        'provider': payment.provider,
        'user_id': payment.user_id,
        'created_at': payment.created_at.isoformat() if hasattr(payment, 'created_at') and payment.created_at else None
    }

def bonus_to_search_dict(bonus):
    """Serialize bonus for search results"""
    bonus_data = {
        'type': 'bonus',
        'id': bonus.id,
        'user_id': bonus.user_id,  
        'amount': float(bonus.amount) if bonus.amount else 0,
        'bonus_type': getattr(bonus, 'type', None),  
        'status': bonus.status,
        'created_at': bonus.created_at.isoformat() if hasattr(bonus, 'created_at') and bonus.created_at else None
    }

    # Add specific fields for ReferralBonus
    if hasattr(bonus, 'referred_id'):
        bonus_data['referred_id'] = bonus.referred_id
        bonus_data['level'] = bonus.level
        bonus_data['bonus_type'] = 'referral'

    return bonus_data
#=======================================================================


@admin_bp.route('/api/claim-daily-bonus', methods=['POST'])
def claim_daily_bonus():
    """
    Claim daily bonus for active packages with comprehensive error handling
    and proper decimal arithmetic for financial calculations.
    """
    db_session = db.session
    transaction = None
    
    try:
        user = current_user
        logger.info(f"Daily bonus claim attempt for user {user.id}")

        # Input validation
        if not user or not user.id:
            return jsonify({"error": "Invalid user session"}), 401

        # Fetch wallet with error handling
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        if not wallet:
            logger.error(f"Wallet not found for user {user.id}")
            return jsonify({"error": "Wallet not found"}), 404

        # Fetch active packages
        packages = Package.query.filter_by(user_id=user.id, status='active').all()
        if not packages:
            logger.info(f"No active packages found for user {user.id}")
            return jsonify({"error": "No active packages found"}), 400

        # Check if user already claimed bonus today
        today = datetime.utcnow().date()
        already_claimed = Bonus.query.filter(
            Bonus.user_id == user.id,
            Bonus.type == "daily",
            db.func.date(Bonus.created_at) == today
        ).first()

        if already_claimed:
            logger.info(f"User {user.id} already claimed daily bonus today")
            return jsonify({"error": "Daily bonus already claimed today"}), 400

        # Initialize bonus calculation
        total_bonus_today = Decimal("0.00")
        now = datetime.now(timezone.utc)
        packages_updated = []
        expired_packages = []

        # Calculate bonus for each package
        for pkg in packages:
            try:
                # Validate package data
                if not pkg.amount or pkg.amount <= Decimal("0"):
                    logger.warning(f"Invalid package amount for package {pkg.id}")
                    continue

                # Check package expiry (60 days from creation)
                expiry_date = pkg.created_at + timedelta(days=60)
                if now > expiry_date:
                    logger.info(f"Package {pkg.id} expired for user {user.id}")
                    pkg.status = "expired"
                    expired_packages.append(pkg.id)
                    db_session.add(pkg)
                    continue

                # Calculate daily bonus (2.5%)
                try:
                    daily_bonus_raw = Decimal(str(pkg.amount)) * Decimal("0.025")
                    daily_bonus = daily_bonus_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Bonus calculation error for package {pkg.id}: {e}")
                    continue

                # Calculate maximum payout (75% of package amount)
                try:
                    max_payout = Decimal(str(pkg.amount)) * Decimal("0.75")
                    current_total_paid = Decimal(str(pkg.total_bonus_paid or "0"))
                    remaining_limit = max_payout - current_total_paid
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Payout calculation error for package {pkg.id}: {e}")
                    continue

                # Skip if remaining limit is zero or negative
                if remaining_limit <= Decimal("0"):
                    pkg.status = "completed"
                    db_session.add(pkg)
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
                        logger.info(f"Package {pkg.id} completed maximum payout")
                    
                    db_session.add(pkg)
                    packages_updated.append(pkg.id)
                    
                except (InvalidOperation, TypeError) as e:
                    logger.error(f"Error updating package {pkg.id} payout: {e}")
                    continue

            except Exception as pkg_error:
                logger.error(f"Error processing package {pkg.id}: {pkg_error}")
                continue  # Continue with other packages

        # Validate total bonus
        if total_bonus_today <= Decimal("0"):
            logger.info(f"No bonus available for user {user.id}")
            return jsonify({
                "error": "No bonus available to claim today",
                "details": {
                    "expired_packages": expired_packages,
                    "updated_packages": packages_updated
                }
            }), 400

        # Ensure bonus is reasonable (sanity check)
        max_reasonable_bonus = Decimal("100000.00")  # Set a reasonable maximum
        if total_bonus_today > max_reasonable_bonus:
            logger.error(f"Suspicious bonus amount {total_bonus_today} for user {user.id}")
            return jsonify({"error": "Bonus calculation error"}), 500

        # Create bonus record
        try:
            bonus_record = Bonus(
                user_id=user.id,
                type="daily",
                amount=total_bonus_today,
                status="active"
            )
            db_session.add(bonus_record)
        except Exception as e:
            logger.error(f"Error creating bonus record: {e}")
            return jsonify({"error": "Failed to create bonus record"}), 500

        # Update wallet balance
        try:
            current_balance = Decimal(str(wallet.balance or "0"))
            new_balance = current_balance + total_bonus_today
            wallet.balance = new_balance
            db_session.add(wallet)
        except (InvalidOperation, TypeError) as e:
            logger.error(f"Error updating wallet balance: {e}")
            return jsonify({"error": "Failed to update wallet balance"}), 500

        # Create transaction record
        try:
            transaction_ref = f"BONUS-{uuid.uuid4().hex[:10].upper()}"
            transaction = Transaction(
                wallet_id=wallet.id,
                type="bonus",
                amount=total_bonus_today,
                status="successful",
                reference=transaction_ref
            )
            db_session.add(transaction)
        except Exception as e:
            logger.error(f"Error creating transaction record: {e}")
            return jsonify({"error": "Failed to create transaction record"}), 500

      
        db_session.commit()
        
        logger.info(f"Daily bonus claimed successfully for user {user.id}: {total_bonus_today}")

      
        response_data = {
            "message": "Daily bonus claimed successfully",
            "bonus": float(total_bonus_today),
            "wallet_balance": float(wallet.balance),
            "transaction_ref": transaction_ref,
            "details": {
                "packages_processed": len(packages_updated),
                "packages_expired": len(expired_packages),
                "total_packages": len(packages)
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        # Rollback on any error
        db_session.rollback()
        logger.error(f"Unexpected error in claim_daily_bonus for user {getattr(user, 'id', 'unknown')}: {str(e)}", exc_info=True)
        
        return jsonify({
            "error": "Failed to process bonus claim",
            "details": "Internal server error"
        }), 500