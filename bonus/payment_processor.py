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
    
    # Create new package
    new_package = Package(
        user_id=user.id,
        catalog_id=package_catalog.id,
        status='active',
        expires_at=datetime.utcnow() + timedelta(days=package_catalog.duration_days),
        created_at=datetime.utcnow()
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

# # utils/payment_processor.py
# from datetime import datetime, timezone, timedelta
# from decimal import Decimal
# from flask import current_app
# from extensions import db
# from models import Payment, PackageCatalog, Package, User, ReferralBonus, Notification
# from bonus.validation import BonusValidationHelper
# from bonus.bonus_calculation import BonusCalculationHelper

# def create_notification(user_id: int, message: str, notification_type: str = 'bonus') -> None:
#     """Create notification with error handling - fails silently"""
#     try:
#         notification = Notification(
#             user_id=user_id,
#             message=message,
#             notification_type=notification_type,
#             is_read=False,
#             created_at=datetime.utcnow()
#         )
#         db.session.add(notification)
#         db.session.commit()
#     except Exception as e:
#         print(f"⚠️ Notification creation failed (non-critical): {e}")
#         db.session.rollback()  # Rollback only notification, not main transaction
# def process_package_purchase(payment):
#     """
#     Process package purchase and bonuses - reusable for both callback and internal purchases
#     """
#     print("🎯 Starting package and bonus processing...")
    
#     # Package processing logic
#     if not payment.package_catalog_id:
#         print(f"❌ Payment {payment.id} missing package_catalog_id")
#         package_catalog = PackageCatalog.query.filter_by(amount=payment.amount).first()
#         if package_catalog:
#             payment.package_catalog_id = package_catalog.id
#             db.session.commit()
#             print(f"✅ Fixed package_catalog_id: {package_catalog.id}")
#         else:
#             print(f"❌ No package found for amount {payment.amount}")
#             return False, "Missing package catalog"
#     else:
#         package_catalog = PackageCatalog.query.get(payment.package_catalog_id)
    
#     if not package_catalog:
#         print(f"❌ Package catalog not found")
#         return False, "Package catalog not found"
        
#     package = package_catalog.name
#     print(f"✅ Using package: {package}")
    
#     # Check user
#     if not payment.user_id:
#         print(f"❌ Missing user_id")
#         return False, "Missing user"
        
#     user = User.query.get(payment.user_id)
#     if not user:
#         print(f"❌ User {payment.user_id} not found")

#         return False, "User not found"
#     print("SESSION USER REFERRER:", user.referred_by)    
#     print(f"✅ User found: {user.id}")
#     print("SESSION USER REFERRER:", user.referred_by)
#     print(f"✅ Package: {package_catalog.name}, Duration: {package_catalog.duration_days}")
    
#     existing_package = Package.query.filter_by(
#     user_id=user.id,
#     catalog_id=package_catalog.id,
#     status='pending'
#     ).first()
#     print("package already created:", package )
#     if not existing_package: 
#        new_package = existing_package
#     print("Using existing package:", package)                                            
#     try:
#         message = f"✅ Your {package} package has been successfully activated! You're now eligible to earn daily bonuses."
#         create_notification(payment.user_id, message, 'purchase_confirmation')
#     except Exception as e:
#         print(f"⚠️ Failed to create purchase notification: {e}")
    

#     # print("✅ Package created for user")
#     print("SESSION USER REFERRER:", user.referred_by)
    

#     try:
#         print("🔄 Starting 20-level bonus processing...")
#         print("SESSION USER REFERRER:", user.referred_by)
        
#         # Check for existing bonuses using payment.id
#         existing_bonuses = ReferralBonus.query.filter_by(payment_id=payment.id).count()
#         if existing_bonuses > 0:
#             print(f"⚠️ Payment {payment.id} already has {existing_bonuses} bonuses - skipping")
#             return True, "Bonuses already processed"

#         can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
#         print("SESSION USER REFERRER:", user.referred_by)

#         if not can_process:
#             print(f"⚠️ Bonus processing skipped: {process_message}")
#             BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#             return False, f"Bonus processing skipped: {process_message}"
#         else:
#             print("✅ Pre-validation passed, calculating multi-level bonuses...")
#             print("SESSION USER REFERRER:", user.referred_by)
            
#             # 2. Calculate bonuses
#             success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
#             print("SESSION USER REFERRER:", user.referred_by)
#             if not success or not bonus_calculations:
#                 print("SESSION USER REFERRER:", user.referred_by)
#                 print(f"❌ Bonus calculation failed: {calc_message}")
#                 BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#                 print("SESSION USER REFERRER:", user.referred_by)
#                 return False, f"Bonus calculation failed: {calc_message}"
            
#             print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated")
#             # After calculate_all_bonuses_secure returns, BEFORE validation
#             # 3. Validate bonuses
#             valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
            
#             print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
            
#             # 4. Store valid bonuses
#               # 4. Store valid bonuses
#             bonus_ids = []
#             bonus_amounts = {}  # Store amounts separately to avoid SQLAlchemy issues
#             if valid_bonuses:
#                 from bonus.config import generate_security_hash
#                 from decimal import Decimal, InvalidOperation
                
#                 # ⭐ GET PURCHASING USER AND REFERRER ONCE
#                 purchasing_user = User.query.get(payment.user_id)
#                 direct_referrer_id = purchasing_user.referred_by if purchasing_user else None
                
#                 print(f"📌 Purchasing user: {payment.user_id}, Referrer ID: {direct_referrer_id}")
                
#                 for original_data in valid_bonuses:
#                     bonus_data = original_data.copy()
#                     try:
#                         if 'purchase_id' in bonus_data:
#                             bonus_data['payment_id'] = bonus_data.pop('purchase_id')
                        
#                         # ✅ CRITICAL FIX: Ensure referrer_id and referred_id are present
#                         if 'referrer_id' not in bonus_data or bonus_data['referrer_id'] is None:
#                             bonus_data['referrer_id'] = direct_referrer_id
#                             print(f"  ➕ Added missing referrer_id: {direct_referrer_id}")
                        
#                         if 'referred_id' not in bonus_data or bonus_data['referred_id'] is None:
#                             bonus_data['referred_id'] = payment.user_id
#                             print(f"  ➕ Added missing referred_id: {payment.user_id}")
                        
#                         # Ensure type is set
#                         if 'type' not in bonus_data:
#                             bonus_data['type'] = 'referral_bonus'
                        
#                         # Convert amount to Decimal
#                         raw_amount = bonus_data.get('bonus_amount') or bonus_data.get('amount') or 0
                        
#                         try:
#                             if isinstance(raw_amount, Decimal):
#                                 bonus_amount = raw_amount
#                             elif isinstance(raw_amount, (int, float)):
#                                 bonus_amount = Decimal(str(raw_amount))
#                             else:
#                                 bonus_amount = Decimal(str(raw_amount).strip())
#                         except (InvalidOperation, ValueError) as e:
#                             print(f"⚠️ Invalid bonus amount format: {raw_amount}, using 0")
#                             bonus_amount = Decimal('0')
                        
#                         bonus_data['bonus_amount'] = bonus_amount
#                         if 'amount' in bonus_data:
#                             print(f"  ➕ Removing 'amount' key (value: {bonus_data['amount']})")
#                             del bonus_data['amount']
                          
#                         else:
#                             print(f"  ✅ 'amount' key not present")
#                         # Create bonus record
#                         bonus = ReferralBonus(**bonus_data)
                        
#                         if not bonus.security_hash:
#                             bonus.security_hash = generate_security_hash(
#                                 bonus.user_id, 
#                                 float(bonus_amount), 
#                                 bonus.payment_id
#                             )
                        
#                         db.session.add(bonus)
#                         db.session.flush()
                        
#                         bonus_ids.append(bonus.id)
#                         bonus_amounts[bonus.id] = bonus_amount
                        
#                         print(f"✅ Created bonus {bonus.id}: user={bonus.user_id}, referrer={bonus_data['referrer_id']}, referred={bonus_data['referred_id']}, amount={bonus_amount}")
                        
#                     except Exception as e:
#                         print(f"⚠️ Error creating bonus record: {e}")
#                         import traceback
#                         traceback.print_exc()
#                         continue
                
#                 # Commit all bonuses at once
#                 db.session.commit()
#                 print(f"💾 Committed {len(bonus_ids)} bonuses to database")
   
#                 # FIX: Use a fresh session to retrieve bonuses and avoid column object issues
#                 from sqlalchemy.orm import Session
#                 # 5. Credit wallets using the stored amounts
#                 credited_count = 0
#                 for bonus_id in bonus_ids:
#                     try:
#                         # Get bonus with fresh query
#                         fresh_bonus = db.session.query(ReferralBonus).get(bonus_id)
                        
#                         if not fresh_bonus:
#                             print(f"⚠️ Bonus {bonus_id} not found")
#                             continue
                        
#                         # ✅ FIXED: Use bonus_amount, not amount
#                         amount_from_bonus = fresh_bonus.bonus_amount
#                         if amount_from_bonus is None:
#                             amount_from_bonus = bonus_amounts.get(bonus_id, 0)
                        
#                         bonus_amount_to_credit = float(amount_from_bonus)
                        
#                         print(f"💰 Crediting {bonus_amount_to_credit} to user {fresh_bonus.user_id}")
                        
#                         # Update bonus status
#                         fresh_bonus.status = 'paid'
#                         fresh_bonus.is_paid_out = True
#                         fresh_bonus.paid_out_at = datetime.utcnow()
                        
#                         # Credit user wallet
#                         user = User.query.get(fresh_bonus.user_id)
#                         if user:
#                             user.available_balance = (user.available_balance or 0) + Decimal(str(bonus_amount_to_credit))
#                             user.actual_balance = (user.actual_balance or 0) + Decimal(str(bonus_amount_to_credit))
                        
#                         db.session.commit()
#                         credited_count += 1
#                         print(f"✅ Successfully credited {bonus_amount_to_credit} to user {fresh_bonus.user_id}")
                        
#                     except Exception as e:
#                         db.session.rollback()
#                         print(f"❌ Failed to credit bonus {bonus_id}: {e}")
#                         import traceback
#                         traceback.print_exc()

#                 if credited_count > 0:
#                     print(f"🎉 Successfully credited {credited_count} out of {len(bonus_ids)} bon0uses")
#                         # Create notification for purchasing user (they earned referral bonuses)
#                     try:
#                         purchasing_user = User.query.get(payment.user_id)
#                         if purchasing_user:
#                             message = f"🎉 Congratulations! You've earned bonuses from {credited_count} referral(s) on your {package} package purchase. Amounts have been credited to your wallet."
#                             create_notification(payment.user_id, message, 'bonus_earning')
                            
#                             # Also notify direct referrer if exists
#                             if purchasing_user.referred_by:
#                                 referrer = User.query.get(purchasing_user.referred_by)
#                                 if referrer:
#                                     referrer_message = f"📢 Your referral (User #{payment.user_id}) just purchased a {package} package! You've earned a referral bonus."
#                                     create_notification(purchasing_user.referred_by, referrer_message, 'referral_earning')
#                     except Exception as e:
#                         print(f"⚠️ Failed to create notifications: {e}")
#                     return True, f"Successfully processed {credited_count} bonuses"
#             else:
#                 print("ℹ️ No valid bonuses to create")
#                 BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#                 # Notify user that no bonuses were generated
#                 try:
#                     message = f"📦 Your {package} package is active, but no referral bonuses were generated. Invite friends to start earning!"
#                     create_notification(payment.user_id, message, 'info')
#                 except Exception as e:
#                     print(f"⚠️ Failed to create notification: {e}")
#                 # ⬆️⬆️⬆️ END NOTIFICATION BLOCK ⬆️⬆️⬆️
#                 return True, "No valid bonuses to create"

#     except Exception as e:
#         # Ensure cleanup on any exception
#         try:
#             BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
#         except:
#             pass
#         current_app.logger.error(f"Multi-level bonus distribution failed: {e}")
#         print(f"❌ Multi-level bonus error: {e}")
#         import traceback
#         traceback.print_exc()
#         return False, f"Bonus processing error: {e}"
    