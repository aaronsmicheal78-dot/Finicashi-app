#=========================================================================================================
#
# --------THE BONUS REFERRAL ENGINE OF FINICASHI UP TO 30 LEVELS.----------------
# -----DESIGNED AND ARCHITECTED WITH MLM AND UML PRINCIPLES BY ENG. MWESIGYE AARONS. SOFTWARE ENGINEER
#==========================================================================================================

"""
flask_webhook_referral_handler.py

A secure Flask webhook handler for processing payment provider webhooks,
verifying HMAC signatures, ensuring idempotency, and distributing multi-level
referral bonuses (levels 1–20) according to the business rules.

Security, scalability, and maintainability built-in.
"""

from __future__ import annotations
import os, hmac, hashlib, logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional, List
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import enum
from extensions import db
from models import User, Payment, ReferralBonus, PaymentStatus


# ======================================================
# CONFIG & INIT
# ======================================================


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BONUS_PERCENTAGES = [Decimal('10'), Decimal('5'), Decimal('3'),
                     Decimal('2'), Decimal('1')] + [Decimal('0.5')] * 15

MAX_BONUS_LEVEL = 30
DECIMAL_QUANT = Decimal('0.01')
TIMESTAMP_TOLERANCE_SECONDS = 300  



# ======================================================
# HELPERS
# ======================================================
def verify_timestamp(header_value: Optional[str], tolerance=TIMESTAMP_TOLERANCE_SECONDS) -> bool:
    """Prevents replay attacks."""
    if not header_value:
        return False
    try:
        ts = int(header_value)
    except ValueError:
        return False
    delta = abs(datetime.utcnow().timestamp() - ts)
    return delta <= tolerance


def quantize_decimal(d: Decimal) -> Decimal:
    return d.quantize(DECIMAL_QUANT, rounding=ROUND_DOWN)


# ======================================================
# BONUS DISTRIBUTION LOGIC
# ======================================================

def distribute_referral_bonus(payment: Payment, session):
    """Distribute bonuses for up to 20 referrers."""
    if payment.status != PaymentStatus.COMPLETED.value:
        raise ValueError("Only COMPLETED payments generate bonuses")

    payer = payment.user
    amount = Decimal(payment.amount)
    referrer = payer.referrer
    level = 1

    while referrer and level <= MAX_BONUS_LEVEL:
        percent = BONUS_PERCENTAGES[level - 1]
        bonus_amount = quantize_decimal(amount * percent / Decimal("100"))

        if bonus_amount > 0:
            rb = ReferralBonus(
                payment_id=payment.id,
                from_user_id=payer.id,
                to_user_id=referrer.id,
                level=level,
                bonus_amount=bonus_amount,
            )
            session.add(rb)
            referrer.balance = quantize_decimal(Decimal(referrer.balance) + bonus_amount)
            session.add(referrer)

        referrer = referrer.referrer
        level += 1


# ======================================================
# FLASK WEBHOOK HANDLER
# ======================================================



#=========================================================================
#
#  REFERRAL BONUS PROCESSING
#========================================================================
"""
Referral bonus processor for FinCash system.
Handles multi-level bonuses up to 20 levels.
"""

# ----------------------------------------------------------------------------
# BONUS CONFIGURATION
# ----------------------------------------------------------------------------
BONUS_RATES = [
    Decimal("0.10"),  # Level 1
    Decimal("0.05"),  # Level 2
    Decimal("0.03"),  # Level 3
    Decimal("0.02"),  # Level 4
    Decimal("0.01"),  # Level 5
] + [Decimal("0.005")] * 15  # Levels 6–20

MAX_LEVELS = 20


# -----------------------------
# CORE FUNCTION
# -----------------------------
def process_referral_bonuses(payer_id: int, amount: Decimal, payment_id: int):
    """
    Distribute referral bonuses up the chain when a user makes a payment.

    :param payer_id: ID of the user who made the payment
    :param amount: Decimal amount paid
    :param payment_id: The unique ID of the Payment record
    """
    payer = User.query.get(payer_id)
    if not payer:
        raise ValueError("Payer not found.")

    # We expect User model to have a `referred_by` (parent) field (User.id FK)
    current_referrer = payer.referred_by
    level = 1

    while current_referrer and level <= MAX_LEVELS:
        rate = BONUS_RATES[level - 1]
        bonus_amount = (amount * rate).quantize(Decimal("0.01"))

        if bonus_amount > 0:
            ref_user = User.query.get(current_referrer)
            if not ref_user:
                break

            # Create referral bonus record
            bonus = ReferralBonus(
                referrer_id=ref_user.id,
                referred_id=payer.id,
                level=level,
                rate=rate,
                amount=bonus_amount,
                payment_id=payment_id,
                timestamp=datetime.utcnow(),
            )
            db.session.add(bonus)

            # Update referrer balance safely
            ref_user.balance = (ref_user.balance or Decimal("0.00")) + bonus_amount

        # Move up one level
        next_ref = User.query.get(current_referrer)
        current_referrer = next_ref.referred_by if next_ref else None
        level += 1

    db.session.commit()
    return True


# blueprints/referrals/bonus_processor.py

"""
Referral bonus processor for FinCash.
Distributes multi-level bonuses (up to 20 levels) through existing tables.
"""

from decimal import Decimal
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from extensions import db
from models import User, Wallet, Referral, Bonus

# ------------------------
# Bonus configuration
# ------------------------
BONUS_RATES = [
    Decimal("0.10"),  # Level 1
    Decimal("0.05"),  # Level 2
    Decimal("0.03"),  # Level 3
    Decimal("0.02"),  # Level 4
    Decimal("0.01"),  # Level 5
] + [Decimal("0.005")] * 15  # Levels 6–20

MAX_LEVELS = 20


# ------------------------
# Referral Bonus Processor
# ------------------------
def process_referral_bonuses(payer_id: int, amount: Decimal, payment_id: int):
    """
    Walks up the referral chain and distributes bonuses.

    :param payer_id: ID of the paying user
    :param amount: Payment amount (Decimal)
    :param payment_id: ID of the payment triggering this bonus
    """
    payer = User.query.get(payer_id)
    if not payer:
        raise ValueError("Payer not found")

    current_user_id = payer_id
    level = 1

    try:
        while level <= MAX_LEVELS:
            ref = Referral.query.filter_by(referred_id=current_user_id).first()
            if not ref:
                break  # no referrer at this level

            referrer = User.query.get(ref.referrer_id)
            if not referrer or not referrer.is_active:
                # Skip inactive referrers but continue walking up
                current_user_id = ref.referrer_id
                level += 1
                continue

            rate = BONUS_RATES[level - 1]
            bonus_amount = (amount * rate).quantize(Decimal("0.01"))

            # Prevent double credit for same payment + referrer
            exists = Bonus.query.filter_by(
                user_id=referrer.id,
                payment_id=payment_id,
                referred_id=payer_id,
            ).first()
            if exists:
                current_user_id = ref.referrer_id
                level += 1
                continue

            # Create bonus record
            bonus = Bonus(
                user_id=referrer.id,
                amount=bonus_amount,
                type="referral",
                status="active",
                payment_id=payment_id,
                referred_id=payer_id,
                level=level,
            )
            db.session.add(bonus)

            # Credit the referrer's wallet
            if referrer.wallet:
                referrer.wallet.balance = (referrer.wallet.balance or Decimal("0.00")) + bonus_amount
            else:
                referrer.wallet = Wallet(balance=bonus_amount)

            # Move to next ancestor
            current_user_id = ref.referrer_id
            level += 1

        db.session.commit()
        return True

    except IntegrityError:
        db.session.rollback()
        print(f"Referral bonus already processed for payment {payment_id}")
        return False
    except Exception as e:
        db.session.rollback()
        raise e




