from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
import uuid
import logging
from typing import Tuple, Dict, Optional
from sqlalchemy import and_, or_
from models import db, User, Withdrawal, ReferralBonus, Transaction

logger = logging.getLogger(__name__)

# ==========================================================
#                  CONFIGURATION
# ==========================================================
class WithdrawalConfig:
    MIN_WITHDRAWAL = Decimal("5000")
    MAX_WITHDRAWAL = Decimal("1000000")
    HOLD_PERIOD_HOURS = 24
    PROCESSING_FEE_PERCENT = Decimal("1.0")  # 1% fee
    ACTUAL_BALANCE_THRESHOLD = Decimal("10000")
    
    @staticmethod
    def calculate_fee(amount: Decimal) -> Decimal:
        """Calculate processing fee"""
        fee = (amount * WithdrawalConfig.PROCESSING_FEE_PERCENT) / Decimal("100")
        return fee.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

# ==========================================================
#                  EXCEPTIONS
# ==========================================================
class WithdrawalException(Exception):
    """Base withdrawal exception"""
    pass

class InsufficientBalanceError(WithdrawalException):
    pass

class ValidationError(WithdrawalException):
    pass

class BalanceLockedError(WithdrawalException):
    pass

# ==========================================================
#                  BALANCE LOCK MANAGER
# ==========================================================
class BalanceLockManager:
    _locked_users = set()

    @classmethod
    def acquire_lock(cls, user_id: int) -> bool:
        if user_id in cls._locked_users:
            return False
        cls._locked_users.add(user_id)
        return True

    @classmethod
    def release_lock(cls, user_id: int):
        cls._locked_users.discard(user_id)

    @classmethod
    def with_lock(cls, func):
        """Decorator that locks based on first argument `user_id`"""
        def wrapper(user_id, *args, **kwargs):
            if not cls.acquire_lock(user_id):
                raise WithdrawalException("Another withdrawal in progress")
            try:
                return func(user_id, *args, **kwargs)
            finally:
                cls.release_lock(user_id)
        return wrapper



# ==========================================================
#                  WITHDRAWAL VALIDATOR
# ==========================================================
class WithdrawalValidator:
    @staticmethod
    def validate_withdrawal_request(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str]:
        """
        Comprehensive withdrawal validation
        """
        try:
            # Basic validations
            if not phone or len(phone.strip()) < 10:
                return False, "Valid phone number is required"
            
            # Amount validation
            try:
                amount_dec = Decimal(str(amount))
            except:
                return False, "Invalid amount format"
            
            if amount_dec < WithdrawalConfig.MIN_WITHDRAWAL:
                return False, f"Minimum withdrawal is {WithdrawalConfig.MIN_WITHDRAWAL} UGX"
            
            if amount_dec > WithdrawalConfig.MAX_WITHDRAWAL:
                return False, f"Maximum withdrawal is {WithdrawalConfig.MAX_WITHDRAWAL} UGX"
            
            # User validation
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            if not user.is_active:
                return False, "Account is inactive"
            
            # Balance validation
            total_balance = (user.actual_balance or Decimal('0')) 
            if amount_dec > total_balance:
                return False, "Insufficient balance"
            
            # Check if available balance is mature
            if not WithdrawalValidator._is_available_balance_mature(user):
                available_now = WithdrawalValidator._get_mature_available_balance(user)
                if amount_dec > available_now:
                    return False, "Patiently, Your balance is still on hold for 24 hours. Thank you"
            
            # Check for duplicate pending withdrawals
            recent_pending = Withdrawal.query.filter(
                Withdrawal.user_id == user_id,
                Withdrawal.status.in_(['pending', 'processing']),
                Withdrawal.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5)
            ).first()
            
            if recent_pending:
                return False, "You have a pending withdrawal. Please wait for it to complete."
            
            return True, "Validation passed"
            
        except Exception as e:
            logger.error(f"Withdrawal validation error: {e}")
            return False, "Validation failed"

    @staticmethod
    def _is_available_balance_mature(user: User) -> bool:
        """Check if all available balance is mature (24h old)"""
        immature_balance = WithdrawalValidator._get_immature_balance_amount(user)
        return immature_balance == Decimal('0')

    @staticmethod
    def _get_immature_balance_amount(user: User) -> Decimal:
        """Calculate amount of available balance that's not yet mature"""
        hold_cutoff = datetime.now(timezone.utc) - timedelta(hours=WithdrawalConfig.HOLD_PERIOD_HOURS)
        
        # Sum recent referral bonuses
        recent_bonuses = db.session.query(
            db.func.sum(ReferralBonus.amount).label('total')
        ).filter(
            ReferralBonus.user_id == user.id,
            ReferralBonus.created_at >= hold_cutoff,
            ReferralBonus.status == "active"
        ).scalar() or Decimal('0')
        
        # Sum recent transactions that contribute to available balance
        recent_transactions = db.session.query(
            db.func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.user_id == user.id,
            Transaction.type == 'credit',
            Transaction.created_at >= hold_cutoff,
            Transaction.balance_type == 'available'
        ).scalar() or Decimal('0')
        
        return recent_bonuses + recent_transactions

    @staticmethod
    def _get_mature_available_balance(user: User) -> Decimal:
        """Calculate amount of available balance that's mature and withdrawable now"""
        total_available = user.available_balance or Decimal('0')
        immature_amount = WithdrawalValidator._get_immature_balance_amount(user)
        return max(total_available - immature_amount, Decimal('0'))

# ==========================================================
#                  BALANCE MANAGER
# ==========================================================
class BalanceManager:
    @staticmethod
    def process_withdrawal(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Deduct from actual_balance first, then available_balance
        Returns: (success, message, balance_details)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", None

            amount_dec = Decimal(str(amount))
            
            # Get current balances
            actual_balance = user.actual_balance if user.actual_balance is not None else Decimal('0')
            available_balance = user.available_balance if user.available_balance is not None else Decimal('0')
            
            # Calculate mature available balance
            mature_available = WithdrawalValidator._get_mature_available_balance(user)
            
            # Check if total mature balance is sufficient
            total_mature = actual_balance + mature_available
            if amount_dec > total_mature:
                return False, "Insufficient mature balance", None
            
            remaining_amount = amount_dec
            actual_deducted = Decimal('0')
            available_deducted = Decimal('0')
            
            # Strategy: Deduct from actual balance first, then mature available balance
            if actual_balance > 0:
                deduct_from_actual = min(actual_balance, remaining_amount)
                actual_deducted = deduct_from_actual
                user.actual_balance = actual_balance - deduct_from_actual
                remaining_amount -= deduct_from_actual
            
            # Then deduct from mature available balance
            if remaining_amount > 0 and mature_available >= remaining_amount:
                available_deducted = remaining_amount
                user.available_balance = available_balance - remaining_amount
                remaining_amount = Decimal('0')
            
            # Final check
            if remaining_amount > 0:
                # This shouldn't happen due to prior validation, but just in case
                BalanceManager._reverse_deduction(user, actual_deducted, available_deducted)
                return False, "Insufficient balance after processing", None
            
            # Prepare balance details
            balance_details = {
                'actual_balance': user.actual_balance,
                'available_balance': user.available_balance,
                'actual_deducted': actual_deducted,
                'available_deducted': available_deducted,
                'previous_actual': actual_balance,
                'previous_available': available_balance
            }
            
            return True, "Balance processing successful. Enjoy with Finicash", balance_details
            
        except Exception as e:
            logger.error(f"Balance processing error: {e}")
            return False, f"Balance processing failed: {str(e)}", None

    @staticmethod
    def _reverse_deduction(user: User, actual_deducted: Decimal, available_deducted: Decimal):
        """Reverse a balance deduction in case of errors"""
        try:
            if actual_deducted > 0:
                user.actual_balance += actual_deducted
            if available_deducted > 0:
                user.available_balance += available_deducted
        except Exception as e:
            logger.error(f"Failed to reverse deduction: {e}")

    @staticmethod
    def reverse_withdrawal(user_id: int, amount: Decimal, balance_details: Dict):
        """Reverse a withdrawal - refund balances"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            amount_dec = Decimal(str(amount))
            
            # Refund to the same balances they were deducted from
            if balance_details.get('actual_deducted', Decimal('0')) > 0:
                user.actual_balance += balance_details['actual_deducted']
            
            if balance_details.get('available_deducted', Decimal('0')) > 0:
                user.available_balance += balance_details['available_deducted']
            
            db.session.commit()
            logger.info(f"Reversed {amount_dec} for user {user_id}")
            return True, "Balance reversal successful"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reverse withdrawal: {e}")
            return False, f"Reversal failed: {str(e)}"

# ==========================================================
#                  WITHDRAWAL RECORD MANAGER
# ==========================================================
class WithdrawalRecordManager:
    @staticmethod
    def create_withdrawal_record(user_id: int, amount: Decimal, phone: str, 
                               balance_details: Dict) -> Tuple[bool, Optional[Withdrawal], str]:
        """Create withdrawal record in database"""
        try:
            # Calculate net amount after fees
            fee = WithdrawalConfig.calculate_fee(amount)
            net_amount = amount - fee
            
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=amount,
              #  net_amount=net_amount,
                fee=fee,
                phone=phone,
                status="processing",
                external_ref=str(uuid.uuid4()),
                actual_balance_deducted=balance_details.get('actual_deducted', Decimal('0')),
                available_balance_deducted=balance_details.get('available_deducted', Decimal('0')),
               # previous_actual_balance=balance_details.get('previous_actual', Decimal('0')),
              #  previous_available_balance=balance_details.get('previous_available', Decimal('0'))
            )
            
            db.session.add(withdrawal)
            db.session.flush()  # Get ID without committing
            
            return True, withdrawal, "Withdrawal record created"
            
        except Exception as e:
            logger.error(f"Failed to create withdrawal record: {e}")
            return False, None, f"Record creation failed: {str(e)}"

    @staticmethod
    def update_withdrawal_status(withdrawal_id: int, status: str, external_txid: str = None):
        """Update withdrawal status"""
        try:
            withdrawal = Withdrawal.query.get(withdrawal_id)
            if withdrawal:
                withdrawal.status = status
                if external_txid:
                    withdrawal.external_txid = external_txid
                withdrawal.updated_at = datetime.now(timezone.utc)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update withdrawal status: {e}")
            return False

# ==========================================================
#                  NOTIFICATION MANAGER
# ==========================================================
class WithdrawalNotifier:
    @staticmethod
    def notify_user_about_hold(user_id: int, amount: Decimal, reason: str):
        """Notify user about withdrawal hold"""
        try:
            user = User.query.get(user_id)
            if user:
                logger.info(f"[HOLD] User {user.id} - Amount: {amount} - Reason: {reason}")
                # TODO: Integrate with email/SMS service
                # send_sms(user.phone, f"Withdrawal of {amount} UGX is on hold: {reason}")
        except Exception as e:
            logger.error(f"Hold notification failed: {e}")

    @staticmethod
    def notify_instant_withdrawal(user_id: int, amount: Decimal, withdrawal_id: int):
        """Notify about successful withdrawal processing"""
        try:
            user = User.query.get(user_id)
            if user:
                logger.info(f"[INSTANT] User {user.id} withdrew {amount} - ID: {withdrawal_id}")
                # TODO: Integrate with notification service
        except Exception as e:
            logger.error(f"Instant withdrawal notification failed: {e}")

    @staticmethod
    def notify_withdrawal_failure(user_id: int, amount: Decimal, reason: str):
        """Notify about withdrawal failure"""
        try:
            user = User.query.get(user_id)
            if user:
                logger.warning(f"[FAILED] User {user.id} - Amount: {amount} - Reason: {reason}")
        except Exception as e:
            logger.error(f"Failure notification failed: {e}")

# ==========================================================
#                  MAIN WITHDRAWAL PROCESSOR
# ==========================================================
class WithdrawalProcessor:
    """
    Main withdrawal processor with comprehensive error handling and transaction management
    """
    
    @staticmethod
    @BalanceLockManager.with_lock
    def process_withdrawal_request(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Process withdrawal request atomically
        Returns: (success, message, withdrawal_data)
        """
        withdrawal_data = {}
        
        try:
            # Step 1: Validation
            is_valid, validation_msg = WithdrawalValidator.validate_withdrawal_request(user_id, amount, phone)
            if not is_valid:
                if "24" in validation_msg or "hold" in validation_msg.lower():
                    WithdrawalNotifier.notify_user_about_hold(user_id, amount, validation_msg)
                return False, validation_msg, None

            # Step 2: Balance Deduction
            success, balance_msg, balance_details = BalanceManager.process_withdrawal(user_id, amount, phone)
            if not success:
                WithdrawalNotifier.notify_withdrawal_failure(user_id, amount, balance_msg)
                return False, balance_msg, None

            # Step 3: Create Withdrawal Record
            record_success, withdrawal, record_msg = WithdrawalRecordManager.create_withdrawal_record(
                user_id, amount, phone, balance_details
            )
            
            if not record_success:
                # Critical: Reverse balance deduction if record creation fails
                BalanceManager.reverse_withdrawal(user_id, amount, balance_details)
                WithdrawalNotifier.notify_withdrawal_failure(user_id, amount, record_msg)
                return False, "Withdrawal processing failed. Please try again.", None

            # Step 4: Final Commit - SINGLE COMMIT POINT
            db.session.commit()
            
            # Step 5: Notify Success
            WithdrawalNotifier.notify_instant_withdrawal(user_id, amount, withdrawal.id)
            
            withdrawal_data = {
                'withdrawal_id': withdrawal.id,
                'external_ref': withdrawal.external_ref,
                'net_amount': withdrawal.net_amount,
                'fee': withdrawal.fee,
                'balances': {
                    'new_actual_balance': balance_details['actual_balance'],
                    'new_available_balance': balance_details['available_balance']
                }
            }
            
            return True, "Withdrawal request submitted successfully", withdrawal_data

        except Exception as e:
            # COMPREHENSIVE ERROR HANDLING
            db.session.rollback()
            logger.error(f"Withdrawal processing failed for user {user_id}: {e}")
            
            # Attempt to reverse any partial changes
            try:
                if 'balance_details' in locals():
                    BalanceManager.reverse_withdrawal(user_id, amount, balance_details)
            except Exception as reversal_error:
                logger.critical(f"CRITICAL: Failed to reverse withdrawal for user {user_id}: {reversal_error}")
            
            WithdrawalNotifier.notify_withdrawal_failure(user_id, amount, str(e))
            return False, "Withdrawal processing failed. Please try again.", None

        finally:
            # Ensure lock is released (handled by decorator)
            pass

    @staticmethod
    def complete_withdrawal(withdrawal_id: int, external_txid: str = None) -> bool:
        """Mark withdrawal as completed"""
        return WithdrawalRecordManager.update_withdrawal_status(
            withdrawal_id, "completed", external_txid
        )

    @staticmethod
    def fail_withdrawal(withdrawal_id: int, user_id: int, amount: Decimal, 
                       balance_details: Dict) -> bool:
        """Mark withdrawal as failed and reverse balances"""
        try:
            # Reverse balances first
            success, msg = BalanceManager.reverse_withdrawal(user_id, amount, balance_details)
            if success:
                # Then update withdrawal status
                return WithdrawalRecordManager.update_withdrawal_status(withdrawal_id, "failed")
            return False
        except Exception as e:
            logger.error(f"Failed to process withdrawal failure: {e}")
            return False

# ==========================================================
#                  QUERY HELPERS
# ==========================================================
class WithdrawalQueryHelper:
    @staticmethod
    def get_user_withdrawals(user_id: int, limit: int = 10):
        """Get user's withdrawal history"""
        return Withdrawal.query.filter_by(user_id=user_id)\
                              .order_by(Withdrawal.created_at.desc())\
                              .limit(limit)\
                              .all()
    
    @staticmethod
    def get_pending_withdrawals():
        """Get all pending withdrawals for processing"""
        return Withdrawal.query.filter(
            Withdrawal.status.in_(['pending', 'processing'])
        ).all()
    
    @staticmethod
    def get_withdrawal_by_ref(external_ref: str):
        """Find withdrawal by external reference"""
        return Withdrawal.query.filter_by(external_ref=external_ref).first()

# ==========================================================
#                  USAGE EXAMPLE
# ==========================================================
"""
# Example usage in your route:

@app.route('/withdraw', methods=['POST'])
def withdraw():
    try:
        user_id = get_current_user_id()  # Your auth helper
        amount = request.json.get('amount')
        phone = request.json.get('phone')
        
        success, message, withdrawal_data = WithdrawalProcessor.process_withdrawal_request(
            user_id, Decimal(amount), phone
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'withdrawal_id': withdrawal_data['withdrawal_id'],
                'external_ref': withdrawal_data['external_ref'],
                'net_amount': str(withdrawal_data['net_amount'])
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Withdrawal route error: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500
"""