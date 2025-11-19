# utils/payment_processor.py
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import current_app
from extensions import db
from models import Payment, PackageCatalog, Package, User, ReferralBonus
from bonus.validation import BonusValidationHelper
from bonus.bonus_calculation import BonusCalculationHelper
from bonus.bonus_payment import BonusPaymentHelper

def process_package_purchase(payment):
    """
    Process package purchase and bonuses - reusable for both callback and internal purchases
    """
    print("🎯 Starting package and bonus processing...")
    
    # Package processing logic
    if not payment.package_catalog_id:
        print(f"❌ Payment {payment.id} missing package_catalog_id")
        package_catalog = PackageCatalog.query.filter_by(amount=payment.amount).first()
        if package_catalog:
            payment.package_catalog_id = package_catalog.id
            db.session.commit()
            print(f"✅ Fixed package_catalog_id: {package_catalog.id}")
        else:
            print(f"❌ No package found for amount {payment.amount}")
            return False, "Missing package catalog"
    else:
        package_catalog = PackageCatalog.query.get(payment.package_catalog_id)
    
    if not package_catalog:
        print(f"❌ Package catalog not found")
        return False, "Package catalog not found"
        
    package = package_catalog.name
    print(f"✅ Using package: {package}")
    
    # Check user
    if not payment.user_id:
        print(f"❌ Missing user_id")
        return False, "Missing user"
        
    user = User.query.get(payment.user_id)
    if not user:
        print(f"❌ User {payment.user_id} not found")
        return False, "User not found"
        
    print(f"✅ User found: {user.id}")
    print(f"✅ Package: {package_catalog.name}, Duration: {package_catalog.duration_days}")
    
    # Create user package
    new_package = Package(
        user_id=user.id,
        catalog_id=package_catalog.id,
        package=package_catalog.name,
        type="purchased",
        status='active',
        activated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=package_catalog.duration_days)
    )
    db.session.add(new_package)
    db.session.commit()
    print("✅ Package created for user")

    # Process bonuses
    try:
        print("🔄 Starting 20-level bonus processing...")
        
        # Check for existing bonuses using payment.id
        existing_bonuses = ReferralBonus.query.filter_by(payment_id=payment.id).count()
        if existing_bonuses > 0:
            print(f"⚠️ Payment {payment.id} already has {existing_bonuses} bonuses - skipping")
            return True, "Bonuses already processed"

        # 1. Check if we can process bonuses for this purchase
        can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
        
        if not can_process:
            print(f"⚠️ Bonus processing skipped: {process_message}")
            BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
            return False, f"Bonus processing skipped: {process_message}"
        else:
            print("✅ Pre-validation passed, calculating multi-level bonuses...")
            
            # 2. Calculate bonuses
            success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            
            if not success or not bonus_calculations:
                print(f"❌ Bonus calculation failed: {calc_message}")
                BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                return False, f"Bonus calculation failed: {calc_message}"
            
            print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated")
            
            # 3. Validate bonuses
            valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
            
            print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
            
            # 4. Store valid bonuses
            bonus_ids = []
            if valid_bonuses:
                for bonus_data in valid_bonuses:
                    bonus = ReferralBonus(**bonus_data)
                    db.session.add(bonus)
                    db.session.flush()
                    bonus_ids.append(bonus.id)
                
                db.session.commit()
                
                # 5. Queue for payout
                for bonus_id in bonus_ids:
                    BonusPaymentHelper.queue_bonus_payout(bonus_id)
                
                total_bonus_amount = sum(Decimal(str(b['amount'])) for b in valid_bonuses)
                print(f"🎉 Successfully created {len(valid_bonuses)} bonus records!")
               
                BonusValidationHelper.cleanup_processing_flag(payment.id, success=True)
                print(f"💰 Total bonus amount: {total_bonus_amount}")
                return True, f"Successfully processed {len(valid_bonuses)} bonuses"
            else:
                print("ℹ️ No valid bonuses to create")
                BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                return True, "No valid bonuses to create"

    except Exception as e:
        # Ensure cleanup on any exception
        try:
            BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
        except:
            pass
        current_app.logger.error(f"Multi-level bonus distribution failed: {e}")
        print(f"❌ Multi-level bonus error: {e}")
        return False, f"Bonus processing error: {e}"