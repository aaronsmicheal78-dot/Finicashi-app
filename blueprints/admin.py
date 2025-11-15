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
from models import PaymentStatus
from functools import wraps
from sqlalchemy import or_

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
#     ------------------------ADMIN SEARCH FUNCTIONALITY---------------------------------------
#-----------DASHBOARD COMPLETE SEARCH SYSTEM FOR USERS, BALANCES, AND PAYMENTS-----------------
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
                    User.id == int(query),
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
        # Search in Bonus model
        bonuses_query = Bonus.query.filter(
            or_(
                Bonus.type.ilike(f'%{query}%'),
                Bonus.status.ilike(f'%{query}%')
            )
        ).limit(50).all()

        # Search in ReferralBonus model
        referral_bonuses_query = ReferralBonus.query.filter(
            or_(
                ReferralBonus.type.ilike(f'%{query}%'),
                ReferralBonus.status.ilike(f'%{query}%')
            )
        ).limit(50).all()

        all_bonuses = list(bonuses_query) + list(referral_bonuses_query)
        
        return [bonus_to_search_dict(bonus) for bonus in all_bonuses]
    except Exception as e:
        print(f"Error searching bonuses: {e}")
        return []


# Helper functions to serialize search results
def user_to_search_dict(user):
    """Serialize user for search results"""
    return {
        'type': 'user',
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'balance': float(user.balance or 0),
        'referral_code': user.referral_code,
        'is_active': user.is_active,
        'is_verified': user.is_verified,
        'member_since': user.member_since.isoformat() if user.member_since else None,
        'wallet_balance': float(user.wallet.balance) if user.wallet else 0
    }


def payment_to_search_dict(payment):
    """Serialize payment for search results"""
    return {
        'type': 'payment',
        'id': payment.id,
        'reference': payment.reference,
        'external_ref': payment.external_ref,
        'amount': float(payment.amount or  0),
        'currency': payment.currency,
        'status': payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
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
        'bonus_type': bonus.type,
        'status': bonus.status,
        'created_at': bonus.created_at.isoformat() if hasattr(bonus, 'created_at') and bonus.created_at else None
    }

    # Add specific fields for ReferralBonus
    if hasattr(bonus, 'referred_id'):
        bonus_data['referred_id'] = bonus.referred_id
        bonus_data['level'] = bonus.level
        bonus_data['bonus_type'] = 'referral'

    return bonus_data