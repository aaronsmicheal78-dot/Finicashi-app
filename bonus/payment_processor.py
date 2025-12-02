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
    print("SESSION USER REFERRER:", user.referred_by)    
    print(f"✅ User found: {user.id}")
    print("SESSION USER REFERRER:", user.referred_by)
    print(f"✅ Package: {package_catalog.name}, Duration: {package_catalog.duration_days}")
    
    existing_package = Package.query.filter_by(
    user_id=user.id,
    catalog_id=package_catalog.id,
    status='pending'
    ).first()
   
    if not existing_package:
       from blueprints.payments_helpers import create_user_package   
       new_package = create_user_package(user, package_catalog)
    

    print("✅ Package created for user")
    print("SESSION USER REFERRER:", user.referred_by)
    

    try:
        print("🔄 Starting 20-level bonus processing...")
        print("SESSION USER REFERRER:", user.referred_by)
        
        # Check for existing bonuses using payment.id
        existing_bonuses = ReferralBonus.query.filter_by(payment_id=payment.id).count()
        if existing_bonuses > 0:
            print(f"⚠️ Payment {payment.id} already has {existing_bonuses} bonuses - skipping")
            return True, "Bonuses already processed"

        # 1. Check if we can process bonuses for this purchase
        can_process, process_message, validation_result = BonusValidationHelper.can_process_bonuses(payment.id)
        print("SESSION USER REFERRER:", user.referred_by)

        if not can_process:
            print(f"⚠️ Bonus processing skipped: {process_message}")
            BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
            return False, f"Bonus processing skipped: {process_message}"
        else:
            print("✅ Pre-validation passed, calculating multi-level bonuses...")
            print("SESSION USER REFERRER:", user.referred_by)
            
            # 2. Calculate bonuses
            success, bonus_calculations, calc_message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            print("SESSION USER REFERRER:", user.referred_by)
            if not success or not bonus_calculations:
                print("SESSION USER REFERRER:", user.referred_by)
                print(f"❌ Bonus calculation failed: {calc_message}")
                BonusValidationHelper.cleanup_processing_flag(payment.id, success=False)
                print("SESSION USER REFERRER:", user.referred_by)
                return False, f"Bonus calculation failed: {calc_message}"
            
            print(f"📊 Calculation complete: {len(bonus_calculations)} bonuses calculated")
            
            # 3. Validate bonuses
            valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
            
            print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
            
            # 4. Store valid bonuses
            bonus_ids = []
            bonus_amounts = {}  # Store amounts separately to avoid SQLAlchemy issues
            if valid_bonuses:
                from bonus.config import generate_security_hash
                from decimal import Decimal, InvalidOperation
                
                for original_data in valid_bonuses:
                    bonus_data = original_data.copy()
                #for bonus_data in valid_bonuses:
                    try:
                        if 'purchase_id' in bonus_data:
                            bonus_data['payment_id'] = bonus_data.pop('purchase_id')
                        
                        # Convert amount to Decimal and store it
                        raw_amount = bonus_data.get('bonus_amount') or bonus_data.get('amount') or 0
                        
                        try:
                            if isinstance(raw_amount, Decimal):
                                bonus_amount = raw_amount
                            elif isinstance(raw_amount, (int, float)):
                                bonus_amount = Decimal(str(raw_amount))
                            else:
                                bonus_amount = Decimal(str(raw_amount).strip())
                        except (InvalidOperation, ValueError) as e:
                            print(f"⚠️ Invalid bonus amount format: {raw_amount}, using 0")
                            bonus_amount = Decimal('0')
                        
                        # Store the amount separately
                        bonus_data['bonus_amount'] = bonus_amount
                        
                        # Create bonus record
                        bonus = ReferralBonus(**bonus_data)
                        if not bonus.security_hash:
                            bonus.security_hash = generate_security_hash(
                                bonus.user_id, 
                                float(bonus_amount), 
                                bonus.payment_id
                            )
                        
                        db.session.add(bonus)
                        db.session.flush()  # Flush to get the ID
                        
                        # Store the amount separately to avoid SQLAlchemy column object issues
                        bonus_ids.append(bonus.id)
                        bonus_amounts[bonus.id] = bonus_amount
                        
                        print(f"✅ Created bonus {bonus.id} with amount {bonus_amount}")
                        
                    except Exception as e:
                        print(f"⚠️ Error creating bonus record: {e}")
                        continue
                
                # Commit all bonuses at once
                db.session.commit()
                print(f"💾 Committed {len(bonus_ids)} bonuses to database")
                
                # FIX: Use a fresh session to retrieve bonuses and avoid column object issues
                from sqlalchemy.orm import Session
                
                # 5. Credit wallets using the stored amounts
                credited_count = 0
                for bonus_id in bonus_ids:
                    try:
                        # Get amount from our stored dictionary (not from SQLAlchemy object)
                        amount = bonus_amounts.get(bonus_id)
                        
                        if not amount or amount <= Decimal('0'):
                            print(f"⚠️ Bonus {bonus_id} has invalid amount: {amount}")
                            continue
                        
                        # Get bonus with fresh query to ensure we get actual values
                        fresh_bonus = db.session.query(ReferralBonus).get(bonus_id)
                        
                        if not fresh_bonus:
                            print(f"⚠️ Bonus {bonus_id} not found in fresh query")
                            continue
                        
                        # Verify the amount matches
                        if hasattr(fresh_bonus.bonus_amount, '__clause_element__'):
                            print(f"⚠️ Bonus {bonus_id} still has column object, using stored amount")
                            # Use our stored amount
                            bonus_amount_to_credit = amount
                        else:
                            try:
                                bonus_amount_to_credit = Decimal(str(fresh_bonus.bonus_amount))
                            except:
                                bonus_amount_to_credit = amount
                        
                        print(f"💰 Crediting {bonus_amount_to_credit} to user {fresh_bonus.user_id} (bonus {bonus_id})")
                        
                        # Credit wallet
                        success, msg, tx_id = BonusPaymentHelper._credit_user_wallet_atomic(
                            user_id=fresh_bonus.user_id,
                            amount=bonus_amount_to_credit,
                            bonus_id=fresh_bonus.id
                        )
                        
                        if success:
                            credited_count += 1
                            print(f"✅ Successfully credited {bonus_amount_to_credit} to user {fresh_bonus.user_id}")
                            
                            # Queue for payout
                            try:
                                BonusPaymentHelper.queue_bonus_payout(fresh_bonus.id)
                                print(f"📤 Queued bonus {fresh_bonus.id} for payout")
                            except Exception as e:
                                print(f"⚠️ Failed to queue bonus {fresh_bonus.id} for payout: {e}")
                        else:
                            print(f"❌ Failed to credit bonus {fresh_bonus.id}: {msg}")
                            
                    except Exception as e:
                        print(f"⚠️ Error processing bonus {bonus_id}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Calculate total bonus amount
                total_bonus_amount = sum(bonus_amounts.values())
                
                print(f"🎉 Successfully credited {credited_count} out of {len(bonus_ids)} bonuses")
                print(f"💰 Total bonus amount distributed: {total_bonus_amount}")
                
                # Cleanup processing flag
                BonusValidationHelper.cleanup_processing_flag(payment.id, success=credited_count > 0)
                
                if credited_count > 0:
                    return True, f"Successfully processed {credited_count} bonuses"
                else:
                    return False, "No bonuses were successfully credited"
                
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
        import traceback
        traceback.print_exc()
        return False, f"Bonus processing error: {e}"
    