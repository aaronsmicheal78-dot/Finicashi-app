import logging
from decimal import Decimal, ROUND_DOWN
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models import User, PaymentStatus, ReferralBonus

logger = logging.getLogger(__name__)

# ======================================================
# CONSTANTS
# ======================================================
BONUS_PERCENTAGES = [
    Decimal('10'), Decimal('5'), Decimal('3'), Decimal('2'), Decimal('1')  # Levels 1-5
] + [Decimal('0.5')] * 15  # Levels 6-20

MAX_BONUS_LEVEL = 20
MIN_PAYMENT_FOR_BONUS = Decimal('1.00')
MAX_TOTAL_BONUS_PERCENT = Decimal('25.0')
MIN_BONUS_AMOUNT = Decimal('0.01')
DECIMAL_QUANT = Decimal('0.01')
TIMESTAMP_TOLERANCE_SECONDS = 300

# ======================================================
# HELPER FUNCTIONS (THAT WERE MISSING)
# ======================================================
def quantize_decimal(d: Decimal) -> Decimal:
    """Quantize decimal to 2 decimal places"""
    return d.quantize(DECIMAL_QUANT, rounding=ROUND_DOWN)

def verify_timestamp(header_value: Optional[str], tolerance: int = TIMESTAMP_TOLERANCE_SECONDS) -> bool:
    """Prevents replay attacks."""
    if not header_value:
        return False
    try:
        ts = int(header_value)
    except ValueError:
        return False
    delta = abs(datetime.utcnow().timestamp() - ts)
    return delta <= tolerance

def get_referrer_id(user_id: int, session: Session) -> Optional[int]:
    """Get the referrer ID for a given user"""
    
    user = session.query(User).filter(User.id == user_id).first()
    return user.referrer_id if user and user.referrer_id else None

def validate_referral_chain(user_id: int, potential_referrer_id: int, session: Session) -> bool:
    """Prevent cycles, self-referral, and ensure valid chain"""
    if user_id == potential_referrer_id:
        return False
    
    # Check for cycles by traversing upward
    current = potential_referrer_id
    visited = set()
    while current:
        if current in visited:
            return False  # Cycle detected
        if current == user_id:
            return False  # Self in chain
        visited.add(current)
        # Get next referrer
        current = get_referrer_id(current, session)
        if current is None:
            break  # Reached top of chain
    return True

def should_process_bonus(payment) -> bool:
    """Comprehensive bonus eligibility check"""
    
    
    return (
        payment.status == PaymentStatus.COMPLETED.value and
        Decimal(payment.amount) >= MIN_PAYMENT_FOR_BONUS and
        payment.user_id is not None and
        hasattr(payment, 'user') and payment.user is not None
    )

# ======================================================
# MAIN BONUS DISTRIBUTION FUNCTION (FIXED)
# ======================================================
def distribute_referral_bonus(payment, session: Session):
    """Distribute bonuses with comprehensive error handling and validation"""
    
    if not should_process_bonus(payment):
        logger.warning(f"Bonus not eligible for payment {payment.id}")
        return
    
    payer = payment.user
    amount = Decimal(payment.amount)
    total_bonus_distributed = Decimal('0')
    
    # Check if payer has a referrer at all
    if not payer.referrer_id:
        logger.info(f"User {payer.id} has no referrer, no bonuses to distribute")
        return
    
    referrer = payer.referrer
    level = 1
    processed_users = {payer.id}  # Prevent cycles
    
    try:
        while (referrer and 
               level <= MAX_BONUS_LEVEL and 
               total_bonus_distributed / amount * 100 < MAX_TOTAL_BONUS_PERCENT):
            
            # Validate this specific link in the chain
            if referrer.id in processed_users:
                logger.error(f"Cycle detected in referral chain for payment {payment.id} at level {level}")
                break
                
            processed_users.add(referrer.id)
            
            # Calculate bonus
            percent = BONUS_PERCENTAGES[level - 1]  # Safe because we fixed the array size
            bonus_amount = quantize_decimal(amount * percent / Decimal("100"))
            
            # Apply minimum bonus threshold
            if bonus_amount >= MIN_BONUS_AMOUNT:
                # Check total bonus cap
                potential_total = total_bonus_distributed + bonus_amount
                if potential_total / amount * 100 > MAX_TOTAL_BONUS_PERCENT:
                    bonus_amount = quantize_decimal((amount * MAX_TOTAL_BONUS_PERCENT / 100) - total_bonus_distributed)
                    if bonus_amount < MIN_BONUS_AMOUNT:
                        break
                
                # Create bonus record
             
                rb = ReferralBonus(
                    payment_id=payment.id,
                    from_user_id=payer.id,
                    to_user_id=referrer.id,
                    level=level,
                    bonus_amount=bonus_amount,
                    bonus_percentage=percent
                )
                session.add(rb)
                
                # Update balance
                referrer.balance = quantize_decimal(Decimal(referrer.balance) + bonus_amount)
                session.add(referrer)
                
                total_bonus_distributed += bonus_amount
                
                logger.info(f"Distributed level {level} bonus: {bonus_amount} to user {referrer.id}")
            else:
                logger.debug(f"Bonus amount {bonus_amount} below minimum threshold for level {level}")
            
            # Move to next referrer
            referrer = referrer.referrer
            level += 1
        
        logger.info(f"Total bonus distributed for payment {payment.id}: {total_bonus_distributed} across {level-1} levels")
        
    except IndexError as e:
        logger.error(f"Bonus percentage array index error for level {level}: {str(e)}")
        session.rollback()
        raise
    except Exception as e:
        logger.error(f"Error distributing bonus for payment {payment.id}: {str(e)}")
        session.rollback()
        raise

# ======================================================
# ADDITIONAL SAFETY FUNCTIONS
# ======================================================
def validate_bonus_configuration():
    """Validate that bonus configuration is consistent"""
    if len(BONUS_PERCENTAGES) != MAX_BONUS_LEVEL:
        raise ValueError(f"Bonus percentages array size {len(BONUS_PERCENTAGES)} doesn't match MAX_BONUS_LEVEL {MAX_BONUS_LEVEL}")
    
    total_possible_bonus = sum(BONUS_PERCENTAGES)
    if total_possible_bonus > Decimal('100'):
        logger.warning(f"Total possible bonus percentage {total_possible_bonus}% exceeds 100%")
    
    logger.info(f"Bonus configuration validated: {MAX_BONUS_LEVEL} levels, total possible: {total_possible_bonus}%")

def check_referral_chain_integrity(user_id: int, session: Session) -> bool:
    """Check if a user's referral chain is valid"""
    current = user_id
    visited = set()
    
    while current:
        if current in visited:
            return False
        visited.add(current)
        current = get_referrer_id(current, session)
    
    return True

# Initialize validation on module import
validate_bonus_configuration()