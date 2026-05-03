# utils/payment_processor.py
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Tuple, Dict, Any, Optional
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from models import Payment, PackageCatalog, Package, User, ReferralBonus, Notification
from bonus.validation import BonusValidationHelper
from bonus.bonus_calculation import BonusCalculationHelper

logger = logging.getLogger(__name__)

class PaymentProcessorError(Exception):
    """Custom exception for payment processing errors"""
    pass

def safe_rollback():
    """Safely rollback database transaction"""
    try:
        if db.session.is_active:
            db.session.rollback()
            logger.debug("Transaction rolled back")
    except Exception as e:
        logger.error(f"Rollback failed: {e}")

def create_notification(user_id: int, message: str, notification_type: str = 'bonus') -> bool:
    """Create notification with proper error handling"""
    try:
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type=notification_type,
            is_read=False,
            created_at=datetime.utcnow()
        )
        db.session.add(notification)
        db.session.commit()
        logger.debug(f"Notification created for user {user_id}")
        return True
    except Exception as e:
        logger.warning(f"Notification creation failed: {e}")
        safe_rollback()
        return False

def validate_purchase(payment: Payment) -> Tuple[Optional[PackageCatalog], Optional[User]]:
    """Validate payment and return package and user"""
    # Validate payment amount
    if not payment or not payment.amount or payment.amount <= 0:
        logger.error(f"Invalid payment: {payment.id if payment else 'None'}")
        return None, None
    
    # Get or fix package catalog
    if not payment.package_catalog_id:
        package_catalog = PackageCatalog.query.filter_by(amount=payment.amount).first()
        if not package_catalog:
            logger.error(f"No package found for amount {payment.amount}")
            return None, None
        payment.package_catalog_id = package_catalog.id
        db.session.commit()
        logger.info(f"Fixed package_catalog_id: {package_catalog.id}")
    else:
        package_catalog = PackageCatalog.query.get(payment.package_catalog_id)
    
    if not package_catalog:
        logger.error(f"Package catalog not found for payment {payment.id}")
        return None, None
    
    # Validate user
    if not payment.user_id:
        logger.error(f"Payment {payment.id} has no user_id")
        return None, None
    
    user = User.query.get(payment.user_id)
    if not user:
        logger.error(f"User {payment.user_id} not found")
        return None, None
    
    logger.info(f"Validated purchase: User {user.id}, Package {package_catalog.name}")
    return package_catalog, user

def has_existing_bonuses(payment: Payment) -> bool:
    """Check if bonuses already processed for this payment"""
    existing_count = ReferralBonus.query.filter_by(payment_id=payment.id).count()
    if existing_count > 0:
        logger.warning(f"Payment {payment.id} already has {existing_count} bonuses")
        return True
    return False

def create_user_package(user: User, package_catalog: PackageCatalog) -> Optional[Package]:
    """Create or retrieve user package"""
    existing_package = Package.query.filter_by(
        user_id=user.id,
        catalog_id=package_catalog.id,
        status='active'
    ).first()
    
    if existing_package:
        logger.info(f"Using existing package for user {user.id}")
        return existing_package
    now_aware = datetime.now(timezone.utc)
    # Create new package
    new_package = Package(
        user_id=user.id,
        catalog_id=package_catalog.id,
        status='active',
        expires_at=now_aware + timedelta(days=package_catalog.duration_days),
        created_at=now_aware
    )
    
    db.session.add(new_package)
    db.session.commit()
    logger.info(f"Created new package for user {user.id}")
    return new_package

def credit_bonus_safely(bonus_id: int, amount: Decimal) -> bool:
    """Credit a single bonus to user wallet with safe transaction"""
    try:
        bonus = db.session.get(ReferralBonus, bonus_id)
        if not bonus:
            logger.error(f"Bonus {bonus_id} not found")
            return False
        
        user = User.query.get(bonus.user_id)
        if not user:
            logger.error(f"User {bonus.user_id} not found for bonus {bonus_id}")
            return False
        
        # Credit wallet (keep as Decimal)
        user.available_balance = (user.available_balance or Decimal('0')) + amount
        user.actual_balance = (user.actual_balance or Decimal('0')) + amount
        
        # Update bonus status
        bonus.status = 'paid'
        bonus.is_paid_out = True
        bonus.paid_out_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"Credited {amount} to user {user.id} from bonus {bonus_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to credit bonus {bonus_id}: {e}")
        safe_rollback()
        return False

def send_purchase_notifications(user: User, package_catalog: PackageCatalog, credited_count: int):
    """Send all relevant notifications"""
    # Notify purchasing user
    package_name = package_catalog.name
    message = f"✅ Your {package_name} package has been activated!"
    create_notification(user.id, message, 'purchase_confirmation')
    
    if credited_count > 0:
        bonus_message = f"🎉 You earned {credited_count} referral bonus(es) from your {package_name} purchase!"
        create_notification(user.id, bonus_message, 'bonus_earning')
    
    # Notify referrer if exists
    if user.referred_by:
        referrer_message = f"📢 Your referral (User #{user.id}) purchased a {package_name} package!"
        create_notification(user.referred_by, referrer_message, 'referral_earning')

def process_referral_bonuses(payment: Payment, user: User, package_catalog: PackageCatalog) -> Dict[str, Any]:
    """Process all referral bonuses for this purchase"""
    result = {
        'credited_count': 0,
        'total_amount': Decimal('0'),
        'bonus_ids': []
    }
    
    # Validate processing eligibility
    can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
    if not can_process:
        logger.warning(f"Bonus processing skipped: {process_message}")
        BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
        return result
    
    # Calculate bonuses
    success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
    if not success or not bonus_calculations:
        logger.error(f"Bonus calculation failed: {calc_message}")
        BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
        return result
    
    logger.info(f"Calculated {len(bonus_calculations)} potential bonuses")
    
    # Validate bonuses
    valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
    logger.info(f"Valid: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
    
    if not valid_bonuses:
        logger.info("No valid bonuses to create")
        BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
        create_notification(user.id, 
            f"📦 Your {package_catalog.name} package is active. Invite friends to earn bonuses!",
            'info')
        return result
    
    # Store bonuses
    direct_referrer_id = user.referred_by if user else None
    
    for bonus_data in valid_bonuses:
        try:
            # Prepare bonus data
            bonus_data['payment_id'] = bonus_data.pop('purchase_id', None)
            bonus_data['referrer_id'] = bonus_data.get('referrer_id') or direct_referrer_id
            bonus_data['referred_id'] = bonus_data.get('referred_id') or payment.user_id
            bonus_data['type'] = bonus_data.get('type', 'referral_bonus')
            
            # Ensure amount is Decimal
            raw_amount = bonus_data.get('bonus_amount') or bonus_data.get('amount', 0)
            bonus_amount = Decimal(str(raw_amount)) if raw_amount else Decimal('0')
            bonus_data['bonus_amount'] = bonus_amount
            bonus_data.pop('amount', None)
            
            # Create bonus
            bonus = ReferralBonus(**bonus_data)
            db.session.add(bonus)
            db.session.flush()
            
            result['bonus_ids'].append(bonus.id)
            result['total_amount'] += bonus_amount
            
            logger.debug(f"Created bonus {bonus.id} for user {bonus.user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create bonus record: {e}", exc_info=True)
            continue
    
    # Commit all bonuses
    try:
        db.session.commit()
        logger.info(f"Committed {len(result['bonus_ids'])} bonuses")
    except SQLAlchemyError as e:
        logger.error(f"Failed to commit bonuses: {e}")
        safe_rollback()
        return result
    
    # Credit wallets
    for bonus_id in result['bonus_ids']:
        if credit_bonus_safely(bonus_id, result['total_amount'] / len(result['bonus_ids'])):
            result['credited_count'] += 1
    
    # Clean up processing flag on success
    if result['credited_count'] > 0:
        BonusValidationHelper.cleanup_processing_flag(payment.id, success=True)
    
    return result

def process_package_purchase(payment: Payment) -> Tuple[bool, str]:
    """
    Process package purchase and bonuses - Production ready
    
    Args:
        payment: Payment object to process
    
    Returns:
        Tuple[bool, str]: (success, message)
    """
    logger.info(f"Starting package processing for payment {payment.id}")
    
    try:
        # 1. Validate purchase
        package_catalog, user = validate_purchase(payment)
        if not package_catalog or not user:
            return False, "Purchase validation failed"
        
        # 2. Check for duplicate processing
        if has_existing_bonuses(payment):
            return True, "Already processed"
        
        # 3. Process referral bonuses
        bonus_result = process_referral_bonuses(payment, user, package_catalog)
        
        # 4. Create or update user package
        user_package = create_user_package(user, package_catalog)
        if not user_package:
            logger.warning(f"Failed to create package for user {user.id}")
        
        # 5. Send notifications
        send_purchase_notifications(user, package_catalog, bonus_result['credited_count'])
        
        success_message = f"Successfully processed {bonus_result['credited_count']} bonuses totaling {bonus_result['total_amount']}"
        logger.info(success_message)
        return True, success_message
        
    except Exception as e:
        logger.exception(f"Package purchase processing failed for payment {payment.id if payment else 'None'}")
        safe_rollback()
        return False, f"Processing error: {str(e)}"
