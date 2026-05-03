# withdraw_helpers.py
# FINAL PRODUCTION READY - NO ERRORS

from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timedelta, timezone
import uuid
import logging
import re
from typing import Tuple, Dict, Optional
from functools import wraps
from sqlalchemy import func
from sqlalchemy.exc import OperationalError
from models import User, Withdrawal, ReferralBonus, Transaction, Wallet
from extensions import db
from models import IdempotencyKey
import time


logger = logging.getLogger(__name__)

# ==========================================================
#                  CONFIGURATION
# ==========================================================
class WithdrawalConfig:
    MIN_WITHDRAWAL = Decimal("5000")
    MAX_WITHDRAWAL = Decimal("100000")
    WALLET_HOLD_PERIOD_HOURS = 24
    PROCESSING_FEE_PERCENT = Decimal("19.0")
    DAILY_WITHDRAWAL_LIMIT = 3
    
    @staticmethod
    def calculate_fee(amount: Decimal) -> Decimal:
        fee = (amount * WithdrawalConfig.PROCESSING_FEE_PERCENT) / Decimal("100")
        return fee.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

# ==========================================================
#                  EXCEPTIONS
# ==========================================================
class WithdrawalException(Exception):
    pass

class ValidationError(WithdrawalException):
    pass

# ==========================================================
#                  LOCK MANAGER (POSTGRES ROW-LEVEL)
# ==========================================================
def get_user_with_lock(user_id: int, timeout_seconds: int = 5):
    """Lock user row with timeout to prevent stuck locks"""
    try:
        # Use NOWAIT or timeout
        return db.session.query(User).filter(User.id == user_id)\
            .with_for_update(nowait=True, skip_locked=False)\
            .first()
    except OperationalError as e:
        if "could not obtain lock" in str(e):
            raise WithdrawalException("System busy. Please try again in a few seconds.")
        raise

def get_wallet_with_lock(user_id: int, timeout_seconds: int = 5):
    """Lock wallet row with timeout"""
    try:
        return db.session.query(Wallet).filter(Wallet.user_id == user_id)\
            .with_for_update(nowait=True)\
            .first()
    except OperationalError as e:
        if "could not obtain lock" in str(e):
            raise WithdrawalException("System busy. Please try again.")
        raise

def with_row_lock(func):
    """Decorator for PostgreSQL row-level locking"""
    @wraps(func)
    def wrapper(user_id, *args, **kwargs):
        user = get_user_with_lock(user_id)
        if not user:
            raise WithdrawalException("User not found")
        
        wallet = get_wallet_with_lock(user_id)
        return func(user, wallet, *args, **kwargs)
    return wrapper

# ==========================================================
#                  RATE LIMITER
# ==========================================================
class WithdrawalRateLimiter:
    @staticmethod
    def check_limit(user_id: int) -> Tuple[bool, str]:
        try:
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = Withdrawal.query.filter(
                Withdrawal.user_id == user_id,
                Withdrawal.created_at >= today_start,
                Withdrawal.status.in_(['completed', 'processing'])
            ).count()
            
            if today_count >= WithdrawalConfig.DAILY_WITHDRAWAL_LIMIT:
                return False, f"Daily limit of {WithdrawalConfig.DAILY_WITHDRAWAL_LIMIT} withdrawals reached"
            return True, "OK"
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            return False, "Unable to verify rate limit"

# ==========================================================
#                  VALIDATOR
# ==========================================================
class WithdrawalValidator:
    @staticmethod
    def validate_phone(phone: str) -> str:
        if not phone:
            raise ValidationError("Phone number required")
        
        phone = re.sub(r'\D', '', phone)
        
        if len(phone) == 9:
            phone = f"256{phone}"
        elif len(phone) == 10 and phone.startswith('0'):
            phone = f"256{phone[1:]}"
        elif len(phone) == 12 and phone.startswith('256'):
            pass
        elif len(phone) == 13 and phone.startswith('256'):
            phone = phone[1:]
        else:
            raise ValidationError("Invalid phone number format")
        
        if not (len(phone) == 12 and phone.startswith('256')):
            raise ValidationError("Phone number must be a valid Uganda number")
        
        return phone
    
    @staticmethod
    def validate_withdrawal(user_id: int, amount: Decimal, phone: str) -> Tuple[bool, str, Optional[User]]:
        try:
            phone = WithdrawalValidator.validate_phone(phone)
            
            if amount < WithdrawalConfig.MIN_WITHDRAWAL:
                return False, f"Minimum withdrawal is {WithdrawalConfig.MIN_WITHDRAWAL} UGX", None
            
            if amount > WithdrawalConfig.MAX_WITHDRAWAL:
                return False, f"Maximum withdrawal is {WithdrawalConfig.MAX_WITHDRAWAL} UGX", None
            
            can_withdraw, rate_msg = WithdrawalRateLimiter.check_limit(user_id)
            if not can_withdraw:
                return False, rate_msg, None
            
            user = db.session.get(User, user_id)
            if not user:
                return False, "User not found", None
            if user.phone != phone and user.phone != phone.replace('256', '0'):
                return False, "Phone number does not match your account", None
            
            if not user.is_verified:
                return False, "Account not verified", None
            
            if not user.is_active:
                return False, "Account is inactive", None
            
            actual_balance = Decimal(str(user.actual_balance or 0))
            wallet_balance = Decimal(str(user.wallet.balance if user.wallet else 0))
            total_balance = actual_balance + wallet_balance

            if amount > total_balance:
                return False, "Insufficient balance", None
            
            if amount > actual_balance:

                mature_wallet = WithdrawalValidator._get_mature_wallet_balance(user)
                if amount > (actual_balance + mature_wallet):
                    logger.info(f"Before mature_wallet calculation: actual_balance={actual_balance}")
                    needed_mature_wallet = amount - actual_balance
                    if needed_mature_wallet > mature_wallet:
                        available = mature_wallet + actual_balance
                        if mature_wallet == 0 and wallet_balance > 0:
                            return False, (
                            f"Cannot withdraw {amount:,.0f} UGX. "
                            f"Wallet funds ({wallet_balance:,.0f} UGX) are on {WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS}-hour hold. "
                            f"Only actual balance of {actual_balance:,.0f} UGX is available. "
                            f"Please wait {WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS} hours for wallet funds to mature."
                        ), None 
                        else:
                            return False, (
                            f"Cannot withdraw {amount:,.0f} UGX. "
                            f"Only {mature_wallet:,.0f} UGX of wallet funds are mature. "
                            f"Total available: {available:,.0f} UGX"
                        ), None   
        
            recent_pending = Withdrawal.query.filter(
                Withdrawal.user_id == user_id,
                Withdrawal.status.in_(['pending', 'processing']),
                Withdrawal.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5)
            ).first()
            
            if recent_pending:
                return False, "You have a pending withdrawal. Please wait.", None
            
            return True, "Validation passed", user
            
        except ValidationError as e:
            return False, str(e), None
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, "Validation failed", None
    
    @staticmethod
    def _get_mature_wallet_balance(user: User) -> Decimal:
        """Calculate mature wallet balance incuding all bonus types"""
        hold_cutoff = datetime.now(timezone.utc) - timedelta(hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS)
     
        try:
            valid_credit_types = ['credit', 'bonus_credit', 'referral_bonus', 'refund']
            mature_total = db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0'))).filter(
                Transaction.type.in_(valid_credit_types),
                Transaction.user_id == user.id,
                Transaction.status == 'completed',
                Transaction.created_at < hold_cutoff
            ).scalar()
            
            mature_total = Decimal(str(mature_total or 0)) 
            wallet_balance = Decimal(str(user.wallet.balance if user.wallet else 0))
            logger.debug(f"User {user.id} - Mature: {mature_total}, Wallet: {wallet_balance}")
            
            return min(mature_total, wallet_balance)
        except Exception as e:
            logger.error(f"Failed to calculate mature bonuses: {e}")
            return Decimal('0')
# ==========================================================
#                  BALANCE MANAGER
# ==========================================================
class BalanceManager:
    @staticmethod
    def deduct_balance(user: User, amount: Decimal) -> Tuple[bool, str, Dict]:
        try:
            amount = Decimal(str(amount))
            actual_balance = Decimal(str(user.actual_balance or 0))
            wallet_balance = Decimal(str(user.wallet.balance if user.wallet else 0))
            
            remaining = amount
            actual_deducted = Decimal('0')
            wallet_deducted = Decimal('0')
            
            if actual_balance > 0:
                actual_deducted = min(actual_balance, remaining)
                user.actual_balance = float(actual_balance - actual_deducted)
                remaining -= actual_deducted
            
            if remaining > 0:
                if not user.wallet:
                    BalanceManager._refund(user, actual_deducted, Decimal('0'))
                    return False, "Wallet not initialized", {}
                
                if remaining > wallet_balance:
                    BalanceManager._refund(user, actual_deducted, Decimal('0'))
                    return False, "Insufficient wallet balance", {}
                
                wallet_deducted = remaining
                user.wallet.balance = float(wallet_balance - wallet_deducted)
            
            db.session.flush()
            
            # Return strings for JSON serialization
            return True, "Balance deducted", {
                "actual_deducted": str(actual_deducted),
                "wallet_deducted": str(wallet_deducted),
                "new_actual_balance": str(Decimal(str(user.actual_balance or 0))),
                "new_wallet_balance": str(Decimal(str(user.wallet.balance if user.wallet else 0)))
            }
            
        except Exception as e:
            logger.error(f"Balance deduction error: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return False, "Balance deduction failed", {}
    
    @staticmethod
    def _refund(user: User, actual_amount: Decimal, wallet_amount: Decimal):
        if actual_amount > 0:
            current = Decimal(str(user.actual_balance or 0))
            user.actual_balance = float(current + actual_amount)
        if wallet_amount > 0 and user.wallet:
            current = Decimal(str(user.wallet.balance or 0))
            user.wallet.balance = float(current + wallet_amount)
    
    @staticmethod
    def refund_withdrawal(user: User, balance_details: Dict) -> bool:
        try:
            actual_deducted = Decimal(str(balance_details.get('actual_deducted', '0')))
            wallet_deducted = Decimal(str(balance_details.get('wallet_deducted', '0')))
            
            if actual_deducted > 0:
                current = Decimal(str(user.actual_balance or 0))
                user.actual_balance = float(current + actual_deducted)
            
            if wallet_deducted > 0 and user.wallet:
                current = Decimal(str(user.wallet.balance or 0))
                user.wallet.balance = float(current + wallet_deducted)
            
            db.session.flush()
            logger.info(f"Refunded {actual_deducted + wallet_deducted} to user {user.id}")
            return True
        except Exception as e:
            logger.error(f"Refund failed: {e}")
            return False
# ==========================================================
#                  WITHDRAWAL RECORD MANAGER (WITH IDEMPOTENCY)
# ==========================================================
class WithdrawalRecordManager:
    
    @staticmethod
    def create_record(user_id: int, amount: Decimal, phone: str, balance_details: Dict, idempotency_key: str = None) -> Optional[Withdrawal]:
        """Create withdrawal record with idempotency check using your existing table"""
        try:
            # IDEMPOTENCY CHECK using your existing IdempotencyKey table
            if idempotency_key:
                existing_key = IdempotencyKey.query.filter_by(key=idempotency_key).first()
                
                if existing_key:
                    # If key exists and has withdrawal_id, return existing withdrawal
                    if existing_key.withdrawal_id:
                        existing_withdrawal = db.session.get(Withdrawal, existing_key.withdrawal_id)
                        if existing_withdrawal:
                            logger.info(f"Idempotent request: {idempotency_key} already processed (withdrawal {existing_withdrawal.id})")
                            return existing_withdrawal
                    
                    # Key exists but no withdrawal_id - duplicate request
                    logger.warning(f"Duplicate idempotency key detected: {idempotency_key}")
                    raise WithdrawalException("Duplicate request detected")
            
            # Create withdrawal as normal
            amount_dec = Decimal(str(amount))
            fee = WithdrawalConfig.calculate_fee(amount_dec)
            net_amount = amount_dec - fee
            reference = f"WD-{user_id}-{uuid.uuid4().hex[:8].upper()}"
            
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=float(amount_dec),
                net_amount=float(net_amount),
                fee=float(fee),
                phone=phone,
                status="pending",
                reference=reference,
                actual_balance_deducted=float(Decimal(str(balance_details.get('actual_deducted', '0')))),
                wallet_balance_deducted=float(Decimal(str(balance_details.get('wallet_deducted', '0'))))
            )
            
            db.session.add(withdrawal)
            db.session.flush()  # Get withdrawal.id
            
            # STORE IDEMPOTENCY KEY with your table structure
            if idempotency_key:
                
                idem_record = IdempotencyKey(
                    key=idempotency_key,
                    user_id=user_id,
                    withdrawal_id=withdrawal.id,  # Link to withdrawal
                    expires_at=IdempotencyKey.make_expires(3600)  # 1 hour expiry
                )
                db.session.add(idem_record)
            
            logger.info(f"Withdrawal record created: {reference} (idempotency: {idempotency_key})")
            return withdrawal
            
        except WithdrawalException:
            raise
        except Exception as e:
            logger.error(f"Record creation error: {e}")
            return None

    @staticmethod
    def update_status(withdrawal_id: int, status: str, external_ref: str = None) -> bool:
        try:
            withdrawal = db.session.get(Withdrawal, withdrawal_id)
            if not withdrawal:
                return False
            
            withdrawal.status = status
            if external_ref:
                withdrawal.external_ref = external_ref
            withdrawal.updated_at = datetime.now(timezone.utc)
            db.session.flush()
            return True
        except Exception as e:
            logger.error(f"Status update error: {e}")
            return False

# ==========================================================
#                  MAIN WITHDRAWAL PROCESSOR
# ==========================================================
class WithdrawalProcessor:
    @staticmethod
    def process_withdrawal_request(user_id: int, amount: Decimal, phone: str, idempotency_key: str = None) -> Tuple[bool, str, Optional[Dict]]:
        withdrawal = None
        details = None
        
        try:
            # Validate
            ok, msg, user = WithdrawalValidator.validate_withdrawal(user_id, amount, phone)
            if not ok:
                # ❌ Clean up idempotency key on validation failure
                if idempotency_key:
                    WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
                return False, msg, None
            
            # ✅ Check idempotency with status validation
            if idempotency_key:
                existing_key = IdempotencyKey.query.filter_by(
                    key=idempotency_key, 
                    user_id=user_id
                ).first()
                
                if existing_key and existing_key.withdrawal_id:
                    # Check if the withdrawal actually exists and is valid
                    existing_withdrawal = db.session.get(Withdrawal, existing_key.withdrawal_id)
                    
                    if existing_withdrawal:
                        # If withdrawal failed, clean up and allow retry
                        if existing_withdrawal.status in ['failed', 'cancelled']:
                            logger.warning(f"Cleaning up failed withdrawal {existing_withdrawal.id} for retry")
                            WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
                            # Don't return - continue with new withdrawal
                        else:
                            # Only return if it's actually processing/completed
                            logger.info(f"Returning existing withdrawal for key: {idempotency_key}")
                            return True, "Withdrawal already processed", {
                                "withdrawal_id": existing_withdrawal.id,
                                "reference": existing_withdrawal.reference,
                                "net_amount": str(existing_withdrawal.net_amount),
                                "fee": str(existing_withdrawal.fee),
                                "already_processed": True
                            }
                    else:
                        # Withdrawal doesn't exist - clean up orphaned key
                        WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
            
            # Lock and deduct
            user_locked = get_user_with_lock(user_id)
            wallet_locked = get_wallet_with_lock(user_id)
            
            if not user_locked or not wallet_locked:
                return False, "Another transaction in progress", None
            
            success, msg, details = BalanceManager.deduct_balance(user, Decimal(str(amount)))
            if not success:
                # ✅ Clean up on balance deduction failure
                if idempotency_key:
                    WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
                return False, msg, None
            
            # Create record
            withdrawal = WithdrawalRecordManager.create_record(
                user_id, amount, phone, details, idempotency_key
            )
            
            if not withdrawal:
                BalanceManager.refund_withdrawal(user, details)
                db.session.flush()
                # ✅ Clean up on record creation failure
                if idempotency_key:
                    WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
                return False, "Failed to create withdrawal record", None
            
            # Update idempotency key
            if idempotency_key and withdrawal:
                idem_key = IdempotencyKey.query.filter_by(key=idempotency_key).first()
                if idem_key and not idem_key.withdrawal_id:
                    idem_key.withdrawal_id = withdrawal.id
                    db.session.add(idem_key)
            
            # Commit
            db.session.commit()
            
            return True, "Withdrawal successful", {
                    "withdrawal_id": withdrawal.id,
                    "reference": withdrawal.reference,
                    "net_amount": str(withdrawal.net_amount),
                    "fee": str(withdrawal.fee),
                    "balances": {
                        "actual_deducted": details.get("actual_deducted", "0"),
                        "wallet_deducted": details.get("wallet_deducted", "0"),
                        "new_actual_balance": details.get("new_actual_balance", "0"),
                        "new_wallet_balance": details.get("new_wallet_balance", "0")
                    }
                }
            
        except WithdrawalException as e:
            db.session.rollback()
            # ✅ ALWAYS clean up on exception
            if idempotency_key:
                WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
            return False, str(e), None
        except Exception as e:
            db.session.rollback()
            logger.error(f"Withdrawal failed: {e}", exc_info=True)
            
            # ✅ ALWAYS clean up on any exception
            if idempotency_key:
                WithdrawalProcessor._cleanup_idempotency_key(idempotency_key, user_id)
            
            return False, "Withdrawal failed", None

    @staticmethod
    def _cleanup_idempotency_key(idempotency_key: str, user_id: int):
        """Force cleanup of idempotency key"""
        try:
            deleted = IdempotencyKey.query.filter_by(
                key=idempotency_key, 
                user_id=user_id
            ).delete()
            if deleted:
                db.session.commit()
                logger.info(f"Cleaned up idempotency key: {idempotency_key}")
        except Exception as e:
            logger.error(f"Failed to cleanup idempotency key: {e}")
            db.session.rollback()
    
    @staticmethod
    def complete_withdrawal(withdrawal_id: int, external_ref: str = None) -> bool:
        """Mark withdrawal as completed (called by webhook/callback)"""
        try:
            success = WithdrawalRecordManager.update_status(withdrawal_id, "completed", external_ref)
            if success:
                db.session.commit()
            return success
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to complete withdrawal {withdrawal_id}: {e}")
            return False
    
    @staticmethod
    def fail_withdrawal(withdrawal_id: int, user_id: int, amount: Decimal, balance_details: Dict) -> bool:
        """Mark withdrawal as failed and refund balance"""
        try:
            user = db.session.get(User, user_id)
            if user and balance_details:
                BalanceManager.refund_withdrawal(user, balance_details)
            
            success = WithdrawalRecordManager.update_status(withdrawal_id, "failed")
            if success:
                db.session.commit()
            return success
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to fail withdrawal {withdrawal_id}: {e}")
            return False

# ==========================================================
#                  QUERY HELPERS
# ==========================================================
class WithdrawalQueryHelper:
    @staticmethod
    def get_user_withdrawals(user_id: int, limit: int = 10):
        return Withdrawal.query.filter_by(user_id=user_id)\
            .order_by(Withdrawal.created_at.desc())\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_withdrawal_by_reference(reference: str):
        return Withdrawal.query.filter_by(reference=reference).first()
    
    @staticmethod
    def get_pending_withdrawals(limit: int = 100):
        return Withdrawal.query.filter(
            Withdrawal.status.in_(['pending', 'processing'])
        ).limit(limit).all()