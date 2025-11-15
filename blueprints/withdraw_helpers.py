from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import and_
from models import db, User, Payment, Withdrawal, ReferralBonus
import logging

logger = logging.getLogger(__name__)

class WithdrawalValidator:
    @staticmethod
    def validate_withdrawal_request(user_id, amount, phone):
        """
        Validate withdrawal request against all business rules
        """
        try:
            # Get user with balance information
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Validate amount
            try:
                amount_decimal = Decimal(str(amount))
            except:
                return False, "Invalid amount format"
            
            if amount_decimal < Decimal('5000'):
                return False, "Minimum withdrawal is UGX 5,000"
            
            # Validate phone format
            if not WithdrawalValidator._validate_phone_format(phone):
                return False, "Invalid phone number format. Use format: +2567XXXXXXXX"
            
            # Check sufficient balance
            if not WithdrawalValidator._has_sufficient_balance(user, amount_decimal):
                return False, "Insufficient balance"
            
            # Check available balance holding period
            hold_check, hold_message = WithdrawalValidator._check_available_balance_hold(user, amount_decimal)
            if not hold_check:
                return False, hold_message
            
            return True, "Validation passed"
            
        except Exception as e:
            logger.error(f"Withdrawal validation error: {e}")
            return False, "Validation failed"
    
    @staticmethod
    def _validate_phone_format(phone):
        """Validate Uganda phone number format"""
        import re
        phone_regex = re.compile(r"^\+2567\d{8}$")
        return bool(phone_regex.match(phone))
    
    @staticmethod
    def _has_sufficient_balance(user, amount):
        """Check if user has sufficient total balance"""
        total_balance = (getattr(user, 'actual_balance', 0) + 
                        getattr(user, 'available_balance', 0))
        return total_balance >= float(amount)
    
    @staticmethod
    def _check_available_balance_hold(user, amount):
        """
        Check if withdrawal from available balance respects 24-hour hold period
        Available balance = bonuses + referral bonuses
        """
        actual_balance = getattr(user, 'actual_balance', 0)
        available_balance = getattr(user, 'available_balance', 0)
        
        # If amount can be covered by actual balance only, no hold needed
        if float(amount) <= actual_balance:
            return True, "Instant withdrawal from actual balance"
        
        # Calculate how much we need from available balance
        needed_from_available = float(amount) - actual_balance
        
        if needed_from_available > available_balance:
            return False, "Insufficient available balance"
        
        # Check if available balance components are mature (24 hours old)
        if not WithdrawalValidator._is_available_balance_mature(user):
            return False, "Available balance components must be held for 24 hours before withdrawal"
        
        return True, "Available balance mature for withdrawal"
    
    @staticmethod
    def _is_available_balance_mature(user):
        """
        Check if available balance components (bonuses) are at least 24 hours old
        """
        # Get the most recent bonus/referral transactions
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        
        # Check referral bonuses created in last 24 hours
        recent_referral_bonuses = ReferralBonus.query.filter(
            and_(
                ReferralBonus.user_id == user.id,
                ReferralBonus.created_at >= twenty_four_hours_ago,
                ReferralBonus.status == 'active'  # Assuming bonus is still active
            )
        ).first()
        
        # If any bonuses were created in last 24 hours, available balance is not mature
        if recent_referral_bonuses:
            return False
        
        # Add similar checks for other bonus types if needed
        # recent_other_bonuses = OtherBonus.query.filter(...)
        
        return True


class BalanceManager:
    @staticmethod
    def process_withdrawal(user_id, amount):
        """
        Process withdrawal by deducting from appropriate balances
        Returns: success, message, remaining_balances
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", None
            
            amount_float = float(amount)
            actual_balance = getattr(user, 'actual_balance', 0)
            available_balance = getattr(user, 'available_balance', 0)
            
            # First, try to deduct from actual balance
            remaining_amount = amount_float
            
            if actual_balance > 0:
                if actual_balance >= remaining_amount:
                    # Entire amount from actual balance
                    user.actual_balance = actual_balance - remaining_amount
                    remaining_amount = 0
                else:
                    # Partial from actual balance
                    remaining_amount -= actual_balance
                    user.actual_balance = 0
            
            # Then, deduct remaining from available balance
            if remaining_amount > 0 and available_balance >= remaining_amount:
                user.available_balance = available_balance - remaining_amount
                remaining_amount = 0
            
            if remaining_amount > 0:
                return False, "Insufficient balance after processing", None
            
            # Update user in database
            db.session.commit()
            
            remaining_balances = {
                'actual_balance': user.actual_balance,
                'available_balance': user.available_balance
            }
            
            return True, "Withdrawal processed successfully", remaining_balances
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Balance processing error: {e}")
            return False, f"Balance processing failed: {str(e)}", None


class WithdrawalNotifier:
    @staticmethod
    def notify_user_about_hold(user_id, amount):
        """
        Notify user if withdrawal is delayed due to hold period
        """
        # Implement notification logic (email, SMS, in-app notification)
        user = User.query.get(user_id)
        if user:
            logger.info(f"User {user.id} attempted to withdraw {amount} but available balance is on hold")
            # Add actual notification logic here
            # send_sms(user.phone, f"Withdrawal of {amount} UGX will be processed after 24-hour hold period")
    
    @staticmethod
    def notify_instant_withdrawal(user_id, amount):
        """
        Notify user about instant withdrawal
        """
        user = User.query.get(user_id)
        if user:
            logger.info(f"User {user.id} successfully withdrew {amount} UGX instantly")
            # send_sms(user.phone, f"Withdrawal of {amount} UGX processed instantly")


# Main withdrawal processor
def process_withdrawal_request(user_id, amount, phone, narration="Cash Out"):
    """
    Main function to process withdrawal requests
    """
    # Step 1: Validate request
    is_valid, message = WithdrawalValidator.validate_withdrawal_request(user_id, amount, phone)
    
    if not is_valid:
        # Check if it's a hold period issue
        if "24 hours" in message:
            WithdrawalNotifier.notify_user_about_hold(user_id, amount)
        return False, message
    
    # Step 2: Process balance deduction
    success, process_message, balances = BalanceManager.process_withdrawal(user_id, amount)
    
    if not success:
        return False, process_message
    
    # Step 3: Create withdrawal record
    try:
        import uuid
        withdrawal = Withdrawal(
            user_id=user_id,
            amount=float(amount),
            phone=phone,
            narration=narration,
            status="pending",  # Will be updated by payment provider callback
            transaction_id=str(uuid.uuid4()),
            actual_balance_deducted=float(amount) - (balances['available_balance'] if balances else 0),
            available_balance_deducted=balances['available_balance'] if balances else 0
        )
        
        db.session.add(withdrawal)
        db.session.commit()
        
        # Step 4: Notify user
        WithdrawalNotifier.notify_instant_withdrawal(user_id, amount)
        
        return True, "Withdrawal request submitted successfully"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Withdrawal record creation failed: {e}")
        return False, "Withdrawal processing failed"