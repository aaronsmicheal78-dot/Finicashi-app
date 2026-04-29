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
    MAX_WITHDRAWAL = Decimal("100000")
    WALLET_HOLD_PERIOD_HOURS = 24  # Wallet balance 24-hour hold
    PROCESSING_FEE_PERCENT = Decimal("5.0")  
    
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
        Comprehensive withdrawal validation with virtual unified balance
        """
        try:
            # 1️⃣ Basic phone validation
            if not phone or len(phone.strip()) < 10:
                return False, "Valid phone number is required"
            
            # 2️⃣ Amount validation
            try:
                amount_dec = Decimal(str(amount))
            except Exception:
                return False, "Invalid amount format"

            if amount_dec < WithdrawalConfig.MIN_WITHDRAWAL:
                return False, f"Minimum withdrawal is {WithdrawalConfig.MIN_WITHDRAWAL} UGX"
            
            if amount_dec > WithdrawalConfig.MAX_WITHDRAWAL:
                return False, f"Maximum withdrawal is {WithdrawalConfig.MAX_WITHDRAWAL} UGX"
            
            # 3️⃣ User validation
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            if not user.is_verified:
                return False, "User not verified"
            
            if not user.is_active:
                return False, "Account is inactive"
            
            # 4️⃣ Virtual Unified Balance validation
            actual_balance = Decimal(str(user.actual_balance or 0))
            wallet = user.wallet
            wallet_balance = Decimal(str(wallet.balance)) if wallet and wallet.balance else Decimal("0")
            if not wallet:
               logger.warning(f"User {user.id} has no wallet record. Defaulting balance to 0.")

            print(f"YOUR Wallet {user} is {wallet_balance}")
            
            # Check total balance sufficiency
            total_balance = actual_balance + wallet_balance
            if amount_dec > total_balance:
                return False, "Insufficient balance"
            
            # 5️⃣ Wallet balance maturity check (24-hour hold)
            if not WithdrawalValidator._is_wallet_balance_mature(user, amount_dec, actual_balance):
                mature_wallet = WithdrawalValidator._get_mature_wallet_balance(user)
                available_total = actual_balance + mature_wallet
                if amount_dec > available_total:
                    return False, "Patiently, Some wallet funds are still on hold for 24 hours. Thank you"
            
            # 6️⃣ Duplicate pending withdrawals check
            five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            recent_pending = Withdrawal.query.filter(
                Withdrawal.user_id == user_id,
                Withdrawal.status.in_(['pending', 'processing']),
                Withdrawal.created_at >= five_minutes_ago
            ).first()
            
            if recent_pending:
                return False, "You have a pending withdrawal. Please wait for it to complete."
            
            # ✅ Passed all checks
            return True, "Validation passed"
        
        except Exception as e:
            logger.error(f"Withdrawal validation error: {e}")
            return False, "Validation failed"

    @staticmethod
    def _is_wallet_balance_mature(user: User, withdrawal_amount: Decimal, actual_balance: Decimal) -> bool:
        """
        Check if required wallet balance portion is mature.
        Only check wallet balance if actual_balance is insufficient.
        Safely handles users without wallets.
        """

        # If actual balance covers withdrawal → no wallet needed
        if withdrawal_amount <= actual_balance:
            return True

        wallet = getattr(user, "wallet", None)

        # If user has NO wallet at all → wallet funds = 0 → not mature
        if wallet is None:
            logger.warning(f"User {user.id} has no wallet record. Wallet maturity = 0.")
            return False

        # Get mature portion safely
        mature_wallet = WithdrawalValidator._get_mature_wallet_balance(user)

        if mature_wallet is None:
            mature_wallet = Decimal("0")

        wallet_needed = withdrawal_amount - actual_balance

        return wallet_needed <= mature_wallet


    @staticmethod
    def _get_mature_wallet_balance(user: User) -> Decimal:
        """
        Calculate mature wallet balance (funds older than 24 hours).
        Fully safe version: handles missing wallet, null balances, and missing transactions.
        """

        hold_cutoff = datetime.now(timezone.utc) - timedelta(hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS)

        # 1️⃣ Mature referral bonuses
        mature_bonuses = db.session.query(
            db.func.sum(ReferralBonus.amount).label('total')
        ).filter(
            ReferralBonus.user_id == user.id,
            ReferralBonus.created_at < hold_cutoff,
            ReferralBonus.status == "active"
        ).scalar() or Decimal('0')

        mature_bonuses = Decimal(str(mature_bonuses))

        # 2️⃣ Mature credit transactions
        mature_transactions = db.session.query(
            db.func.sum(Transaction.amount).label('total')
        ).filter(
          #  Transaction.user_id == user.id,
            Transaction.type == 'credit',
            Transaction.created_at < hold_cutoff,
            # Transaction.balance_type == 'wallet',  # if used
        ).scalar() or Decimal('0')

        mature_transactions = Decimal(str(mature_transactions))

        # 3️⃣ Safe wallet retrieval
        wallet = getattr(user, "wallet", None)

        if wallet is None or wallet.balance is None:
            logger.warning(f"User {user.id} has no wallet record or wallet.balance is None. Mature wallet = 0.")
            total_wallet = Decimal("0")
        else:
            total_wallet = Decimal(str(wallet.balance))

        # 4️⃣ Final mature amount (cannot exceed actual wallet balance)
        mature_total = mature_bonuses + mature_transactions

        return min(mature_total, total_wallet)


# ==========================================================
#                  BALANCE MANAGER (VIRTUAL UNIFIED)
# ==========================================================
class BalanceManager:
    @staticmethod
    def process_withdrawal(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Virtual Unified Balance: Deduct from actual_balance first, then wallet_balance
        Returns: (success, message, balance_details)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found", None

            amount_dec = Decimal(str(amount))
            
            # Get current balances as Decimal
            actual_balance = Decimal(str(user.actual_balance or '0'))
            wallet_balance = Decimal(str(user.wallet.balance if user.wallet else '0'))
            
            # Check total balance sufficiency
            total_balance = actual_balance + wallet_balance
            if amount_dec > total_balance:
                return False, "Insufficient balance", None
            
            remaining_amount = amount_dec
            actual_deducted = Decimal('0')
            wallet_deducted = Decimal('0')
            
            # PHASE 1: Deduct from actual balance first (user's real money)
            if actual_balance > 0:
                deduct_from_actual = min(actual_balance, remaining_amount)
                actual_deducted = deduct_from_actual
                user.actual_balance = actual_balance - deduct_from_actual
                remaining_amount -= deduct_from_actual
            
            # PHASE 2: Deduct from wallet balance (system money)
            if remaining_amount > 0 and wallet_balance >= remaining_amount:
                wallet_deducted = remaining_amount
                user.wallet.balance = wallet_balance - remaining_amount
                remaining_amount = Decimal('0')
            
            # Safety check - should never happen due to prior validation
            if remaining_amount > 0:
                # Reverse deduction in case of error
                BalanceManager._reverse_deduction(user, actual_deducted, wallet_deducted)
                return False, "Insufficient balance after processing", None
            
            balance_details = {
                'actual_balance': user.actual_balance,
                'wallet_balance': user.wallet.balance if user.wallet else Decimal('0'),
                'actual_deducted': actual_deducted,
                'wallet_deducted': wallet_deducted
              #  'previous_actual': actual_balance,
               # 'previous_wallet': wallet_balance
            }
            
            return True, "Balance processing successful. Enjoy with Finicash", balance_details
            
        except Exception as e:
            logger.error(f"Balance processing error: {e}")
            return False, f"Balance processing failed: {str(e)}", None

    @staticmethod
    def _reverse_deduction(user: User, actual_deducted: Decimal, wallet_deducted: Decimal):
        """Reverse a balance deduction in case of errors"""
        try:
            if actual_deducted > 0:
                user.actual_balance += actual_deducted
            if wallet_deducted > 0:
                user.wallet.balance += wallet_deducted
        except Exception as e:
            logger.error(f"Failed to reverse deduction: {e}")

    @staticmethod
    def reverse_withdrawal(user_id: int, amount: Decimal, balance_details: Dict):
        """Reverse a withdrawal - refund to correct balance types"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Refund to the same balances they were deducted from
            if balance_details.get('actual_deducted', Decimal('0')) > 0:
                user.actual_balance += balance_details['actual_deducted']
            
            if balance_details.get('wallet_deducted', Decimal('0')) > 0:
                user.wallet.balance += balance_details['wallet_deducted']
            
            db.session.commit()
            logger.info(f"Reversed {amount} for user {user_id}")
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
        """Create withdrawal record with virtual unified balance tracking"""
        try:
            # Calculate net amount after fees
            fee = WithdrawalConfig.calculate_fee(amount)
            net_amount = amount - fee
            reference = str(uuid.uuid4())
            
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=amount,
                net_amount=str(net_amount),
                fee=fee,
                phone=phone,
                status="pending",
                reference=reference,
                external_ref=None,
                actual_balance_deducted=balance_details.get('actual_deducted', Decimal('0')),
                wallet_balance_deducted=balance_details.get('wallet_deducted', Decimal('0'))
              #  previous_actual_balance=balance_details.get('previous_actual', Decimal('0')),
              #  previous_wallet_balance=balance_details.get('previous_wallet', Decimal('0'))
            )
            
            db.session.add(withdrawal)
            db.session.commit()
            
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
    Main withdrawal processor with Virtual Unified Balance
    """
    
    @staticmethod
    @BalanceLockManager.with_lock
    def process_withdrawal_request(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Process withdrawal request with virtual unified balance
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

            # Step 2: Virtual Unified Balance Deduction
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

            # Step 4: Final Commit
            db.session.commit()
            
            # Step 5: Notify Success
            WithdrawalNotifier.notify_instant_withdrawal(user_id, amount, withdrawal.id)
            
            # Step 6: Prepare response data
            withdrawal_data = {
                'withdrawal_id': withdrawal.id,
                'reference': withdrawal.reference,
                'net_amount': str(withdrawal.net_amount),
                'fee': withdrawal.fee,
                'balances': {
                    'new_actual_balance': balance_details['actual_balance'],
                    'new_wallet_balance': balance_details['wallet_balance'],
                    'actual_deducted': balance_details['actual_deducted'],
                    'wallet_deducted': balance_details['wallet_deducted']
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
    def get_withdrawal_by_ref(reference: str):
        """Find withdrawal by reference"""
        return Withdrawal.query.filter_by(reference=reference).first()



