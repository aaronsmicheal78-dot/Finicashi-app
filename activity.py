from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import or_, and_
from datetime import datetime
import math

activity_bp = Blueprint('activity', __name__)

# Your existing mapping functions
def map_transaction_to_activity(transaction):
    """Map Transaction model to activity format"""
    type_mapping = {
        'deposit': 'deposit',
        'withdrawal': 'withdraw', 
        'bonus': 'bonus',
        'referral': 'bonus',
        'package': 'deposit'
    }
    
    activity_type = type_mapping.get(transaction.type, 'deposit')
    
    title_mapping = {
        'deposit': 'Funds Deposit',
        'withdrawal': 'Withdrawal',
        'bonus': 'Bonus Credit', 
        'referral': 'Referral Bonus',
        'package': 'Package Investment'
    }
    
    title = title_mapping.get(transaction.type, 'Transaction')
    
    return {
        'type': activity_type,
        'title': title,
        'timestamp': transaction.created_at.isoformat() if transaction.created_at else None,
        'amount': float(transaction.amount) if transaction.amount else 0.0,
        'currency': 'UGX'
    }

def map_payment_to_activity(payment):
    """Map Payment model to activity format"""
    if payment.payment_type == 'package':
        activity_type = 'deposit'
        title = f'Package Purchase - {payment.package_catalog.name if payment.package_catalog else "Investment"}'
    else:
        activity_type = 'deposit'
        title = 'Payment Deposit'
    
    return {
        'type': activity_type,
        'title': title,
        'timestamp': payment.created_at.isoformat() if payment.created_at else None,
        'amount': float(payment.amount) if payment.amount else 0.0,
        'currency': payment.currency or 'UGX'
    }

def map_withdrawal_to_activity(withdrawal):
    """Map Withdrawal model to activity format"""
    return {
        'type': 'withdraw',
        'title': 'Withdrawal Request',
        'timestamp': withdrawal.created_at.isoformat() if withdrawal.created_at else None,
        'amount': float(withdrawal.amount) if withdrawal.amount else 0.0,
        'currency': 'UGX'
    }

def map_bonus_to_activity(bonus):
    """Map Bonus model to activity format"""
    return {
        'type': 'bonus',
        'title': f'{bonus.type.title()} Bonus' if bonus.type else 'Bonus',
        'timestamp': bonus.created_at.isoformat() if bonus.created_at else None,
        'amount': float(bonus.amount) if bonus.amount else 0.0,
        'currency': 'UGX'
    }

def map_referral_bonus_to_activity(referral_bonus):
    """Map ReferralBonus model to activity format"""
    level_text = f" (Level {referral_bonus.level})" if referral_bonus.level else ""
    return {
        'type': 'bonus',
        'title': f'Referral Bonus{level_text}',
        'timestamp': referral_bonus.created_at.isoformat() if referral_bonus.created_at else None,
        'amount': float(referral_bonus.bonus_amount) if referral_bonus.bonus_amount else 0.0,
        'currency': 'UGX'
    }

@activity_bp.route('/api/recent_activity', methods=['GET'])
def get_recent_activity():
    """
    Get recent activities for ALL users (general activity feed)
    """
    print("GENERAL RECENT ACTIVITY ENDPOINT HIT")
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 
                                   current_app.config.get('DEFAULT_PAGE_SIZE', 20), 
                                   type=int)
        
        # Validate pagination
        if page < 1:
            return jsonify({'error': 'Page must be greater than 0'}), 400
            
        max_page_size = current_app.config.get('MAX_PAGE_SIZE', 100)
        if page_size < 1 or page_size > max_page_size:
            return jsonify({
                'error': f'Page size must be between 1 and {max_page_size}'
            }), 400
        
        offset = (page - 1) * page_size
        
        # Import models
        from models import Transaction, Payment, Withdrawal, Bonus, ReferralBonus
        
        all_activities = []
        
        # 1. Get all transactions
        transactions = Transaction.query.filter(
            Transaction.type.in_(['deposit', 'withdrawal', 'bonus', 'referral', 'package'])
        ).order_by(Transaction.created_at.desc()).limit(100).all()
        
        for transaction in transactions:
            activity = map_transaction_to_activity(transaction)
            if activity:
                all_activities.append(activity)
        
        # 2. Get all payments
        payments = Payment.query.filter(
            Payment.status.in_(['completed'])
        ).order_by(Payment.created_at.desc()).limit(100).all()
        
        for payment in payments:
            activity = map_payment_to_activity(payment)
            if activity:
                all_activities.append(activity)
        
        # 3. Get all withdrawals
        withdrawals = Withdrawal.query.filter(
            Withdrawal.status.in_(['completed', 'pending', 'processed'])
        ).order_by(Withdrawal.created_at.desc()).limit(100).all()
        
        for withdrawal in withdrawals:
            activity = map_withdrawal_to_activity(withdrawal)
            if activity:
                all_activities.append(activity)
        
        # 4. Get all bonuses
        bonuses = Bonus.query.filter(
            Bonus.status.in_(['active', 'paid'])
        ).order_by(Bonus.created_at.desc()).limit(100).all()
        
        for bonus in bonuses:
            activity = map_bonus_to_activity(bonus)
            if activity:
                all_activities.append(activity)
        
        # 5. Get all referral bonuses
        referral_bonuses = ReferralBonus.query.filter(
            ReferralBonus.status.in_(['active', 'paid'])
        ).order_by(ReferralBonus.created_at.desc()).limit(100).all()
        
        for referral_bonus in referral_bonuses:
            activity = map_referral_bonus_to_activity(referral_bonus)
            if activity:
                all_activities.append(activity)
        
        # Sort by timestamp (most recent first)
        all_activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        # Apply pagination
        total_items = len(all_activities)
        start_idx = offset
        end_idx = offset + page_size
        paginated_activities = all_activities[start_idx:end_idx]
        
        total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        
        response = {
            'activities': paginated_activities,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        print(f"Returning {len(paginated_activities)} activities")
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching recent activities: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# Keep this route separate for user-specific activities
@activity_bp.route('/api/recent_activity/<int:user_id>', methods=['GET'])
def get_user_recent_activity(user_id):
    """
    Get recent activities for a SPECIFIC user
    """
    print(f"USER RECENT ACTIVITY ENDPOINT HIT for user_id: {user_id}")
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 
                                   current_app.config.get('DEFAULT_PAGE_SIZE', 20), 
                                   type=int)
        
        # Validate pagination
        if page < 1:
            return jsonify({'error': 'Page must be greater than 0'}), 400
            
        max_page_size = current_app.config.get('MAX_PAGE_SIZE', 100)
        if page_size < 1 or page_size > max_page_size:
            return jsonify({
                'error': f'Page size must be between 1 and {max_page_size}'
            }), 400
        
        offset = (page - 1) * page_size
        
        # Import models
        from models import Transaction, Payment, Withdrawal, Bonus, ReferralBonus, Wallet
        
        all_activities = []
        
        # 1. Get user's wallet transactions
        user_wallet = Wallet.query.filter_by(user_id=user_id).first()
        if user_wallet:
            transactions = Transaction.query.filter_by(wallet_id=user_wallet.id).filter(
                Transaction.type.in_(['deposit', 'withdrawal', 'bonus', 'referral', 'package'])
            ).order_by(Transaction.created_at.desc()).limit(100).all()
            
            for transaction in transactions:
                activity = map_transaction_to_activity(transaction)
                if activity:
                    all_activities.append(activity)
        
        # 2. Get user's payments
        payments = Payment.query.filter_by(user_id=user_id).filter(
            Payment.status.in_(['completed'])
        ).order_by(Payment.created_at.desc()).limit(100).all()
        
        for payment in payments:
            activity = map_payment_to_activity(payment)
            if activity:
                all_activities.append(activity)
        
        # 3. Get user's withdrawals
        withdrawals = Withdrawal.query.filter_by(user_id=user_id).filter(
            Withdrawal.status.in_(['completed', 'pending', 'processed'])
        ).order_by(Withdrawal.created_at.desc()).limit(100).all()
        
        for withdrawal in withdrawals:
            activity = map_withdrawal_to_activity(withdrawal)
            if activity:
                all_activities.append(activity)
        
        # 4. Get user's bonuses
        bonuses = Bonus.query.filter_by(user_id=user_id).filter(
            Bonus.status.in_(['active', 'paid'])
        ).order_by(Bonus.created_at.desc()).limit(100).all()
        
        for bonus in bonuses:
            activity = map_bonus_to_activity(bonus)
            if activity:
                all_activities.append(activity)
        
        # 5. Get user's referral bonuses
        referral_bonuses = ReferralBonus.query.filter_by(user_id=user_id).filter(
            ReferralBonus.status.in_(['active', 'paid'])
        ).order_by(ReferralBonus.created_at.desc()).limit(100).all()
        
        for referral_bonus in referral_bonuses:
            activity = map_referral_bonus_to_activity(referral_bonus)
            if activity:
                all_activities.append(activity)
        
        # Sort by timestamp
        all_activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
        # Apply pagination
        total_items = len(all_activities)
        start_idx = offset
        end_idx = offset + page_size
        paginated_activities = all_activities[start_idx:end_idx]
        
        total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        
        response = {
            'activities': paginated_activities,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        print(f"Returning {len(paginated_activities)} activities for user {user_id}")
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching user activities: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
#  from flask import Blueprint, request, jsonify, current_app
# from sqlalchemy import or_, and_
# from datetime import datetime
# import math

# activity_bp = Blueprint('activity', __name__)

# def map_transaction_to_activity(transaction):
#     """Map Transaction model to activity format"""
#     type_mapping = {
#         'deposit': 'deposit',
#         'withdrawal': 'withdraw', 
#         'bonus': 'bonus',
#         'referral': 'bonus',
#         'package': 'deposit'  # Package purchases can be considered deposits
#     }
    
#     activity_type = type_mapping.get(transaction.type, 'deposit')
    
#     # Create descriptive title based on transaction type
#     title_mapping = {
#         'deposit': 'Funds Deposit',
#         'withdrawal': 'Withdrawal',
#         'bonus': 'Bonus Credit', 
#         'referral': 'Referral Bonus',
#         'package': 'Package Investment'
#     }
    
#     title = title_mapping.get(transaction.type, 'Transaction')
    
#     return {
#         'type': activity_type,
#         'title': title,
#         'timestamp': transaction.created_at.isoformat() if transaction.created_at else None,
#         'amount': float(transaction.amount) if transaction.amount else 0.0,
#         'currency': 'UGX'  # Default currency from your models
#     }

# def map_payment_to_activity(payment):
#     """Map Payment model to activity format"""
#     if payment.payment_type == 'package':
#         activity_type = 'deposit'
#         title = f'Package Purchase - {payment.package_catalog.name if payment.package_catalog else "Investment"}'
#     else:
#         activity_type = 'deposit'
#         title = 'Payment Deposit'
    
#     return {
#         'type': activity_type,
#         'title': title,
#         'timestamp': payment.created_at.isoformat() if payment.created_at else None,
#         'amount': float(payment.amount) if payment.amount else 0.0,
#         'currency': payment.currency or 'UGX'
#     }

# def map_withdrawal_to_activity(withdrawal):
#     """Map Withdrawal model to activity format"""
#     return {
#         'type': 'withdraw',
#         'title': 'Withdrawal Request',
#         'timestamp': withdrawal.created_at.isoformat() if withdrawal.created_at else None,
#         'amount': float(withdrawal.amount) if withdrawal.amount else 0.0,
#         'currency': 'UGX'
#     }

# def map_bonus_to_activity(bonus):
#     """Map Bonus model to activity format"""
#     return {
#         'type': 'bonus',
#         'title': f'{bonus.type.title()} Bonus' if bonus.type else 'Bonus',
#         'timestamp': bonus.created_at.isoformat() if bonus.created_at else None,
#         'amount': float(bonus.amount) if bonus.amount else 0.0,
#         'currency': 'UGX'
#     }

# def map_referral_bonus_to_activity(referral_bonus):
#     """Map ReferralBonus model to activity format"""
#     level_text = f" (Level {referral_bonus.level})" if referral_bonus.level else ""
#     return {
#         'type': 'bonus',
#         'title': f'Referral Bonus{level_text}',
#         'timestamp': referral_bonus.created_at.isoformat() if referral_bonus.created_at else None,
#         'amount': float(referral_bonus.bonus_amount) if referral_bonus.bonus_amount else 0.0,
#         'currency': 'UGX'
#     }
# #=================================================================================================
# @activity_bp.route('/api/recent_activity', methods=['GET'])
# def get_recent_activity():
#     """
#     Get recent activities for all users (admin view) or current user
#     """
#     print("GENERAL RECENT ACTIVITY HIT: processing....")
#     try:
#         page = request.args.get('page', 1, type=int)
#         page_size = request.args.get('page_size', 
#                                    current_app.config.get('DEFAULT_PAGE_SIZE', 20), 
#                                    type=int)
        
#         # Validate pagination
#         if page < 1:
#             return jsonify({'error': 'Page must be greater than 0'}), 400
            
#         max_page_size = current_app.config.get('MAX_PAGE_SIZE', 100)
#         if page_size < 1 or page_size > max_page_size:
#             return jsonify({
#                 'error': f'Page size must be between 1 and {max_page_size}'
#             }), 400
        
#         offset = (page - 1) * page_size
        
#         # Import models
#         from models import Transaction, Payment, Withdrawal, Bonus, ReferralBonus
        
#         all_activities = []
        
#         # 1. Get all transactions (limit for performance)
#         transactions = Transaction.query.filter(
#             Transaction.type.in_(['deposit', 'withdrawal', 'bonus', 'referral', 'package'])
#         ).order_by(Transaction.created_at.desc()).limit(100).all()
        
#         for transaction in transactions:
#             activity = map_transaction_to_activity(transaction)
#             if activity:
#                 all_activities.append(activity)
        
#         # 2. Get all payments
#         payments = Payment.query.filter(
#             Payment.status.in_(['completed'])
#         ).order_by(Payment.created_at.desc()).limit(100).all()
        
#         for payment in payments:
#             activity = map_payment_to_activity(payment)
#             if activity:
#                 all_activities.append(activity)
        
#         # 3. Get all withdrawals
#         withdrawals = Withdrawal.query.filter(
#             Withdrawal.status.in_(['completed', 'pending', 'processed'])
#         ).order_by(Withdrawal.created_at.desc()).limit(100).all()
        
#         for withdrawal in withdrawals:
#             activity = map_withdrawal_to_activity(withdrawal)
#             if activity:
#                 all_activities.append(activity)
        
#         # 4. Get all bonuses
#         bonuses = Bonus.query.filter(
#             Bonus.status.in_(['active', 'paid'])
#         ).order_by(Bonus.created_at.desc()).limit(100).all()
        
#         for bonus in bonuses:
#             activity = map_bonus_to_activity(bonus)
#             if activity:
#                 all_activities.append(activity)
        
#         # 5. Get all referral bonuses
#         referral_bonuses = ReferralBonus.query.filter(
#             ReferralBonus.status.in_(['active', 'paid'])
#         ).order_by(ReferralBonus.created_at.desc()).limit(100).all()
        
#         for referral_bonus in referral_bonuses:
#             activity = map_referral_bonus_to_activity(referral_bonus)
#             if activity:
#                 all_activities.append(activity)
        
#         # Sort by timestamp
#         all_activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)
        
#         # Apply pagination
#         total_items = len(all_activities)
#         start_idx = offset
#         end_idx = offset + page_size
#         paginated_activities = all_activities[start_idx:end_idx]
        
#         total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
        
#         response = {
#             'activities': paginated_activities,
#             'pagination': {
#                 'page': page,
#                 'page_size': page_size,
#                 'total_items': total_items,
#                 'total_pages': total_pages,
#                 'has_next': page < total_pages,
#                 'has_prev': page > 1
#             }
#         }
       
#         return jsonify(response)
        
#     except Exception as e:
#         current_app.logger.error(f"Error fetching recent activities: {str(e)}")
#         return jsonify({'error': 'Internal server error'}), 500
# #=======================================================================================================