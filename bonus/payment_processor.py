# utils/payment_processor.py
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import current_app
from extensions import db
from models import Payment, PackageCatalog, Package, User, ReferralBonus
from bonus.validation import BonusValidationHelper
from bonus.bonus_calculation import BonusCalculationHelper





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
    print("package already created:", package )
    if not existing_package: 
       new_package = existing_package
    print("Using existing package:", package)                                            
    

    # print("✅ Package created for user")
    print("SESSION USER REFERRER:", user.referred_by)
    

    try:
        print("🔄 Starting 20-level bonus processing...")
        print("SESSION USER REFERRER:", user.referred_by)
        
        # Check for existing bonuses using payment.id
        existing_bonuses = ReferralBonus.query.filter_by(payment_id=payment.id).count()
        if existing_bonuses > 0:
            print(f"⚠️ Payment {payment.id} already has {existing_bonuses} bonuses - skipping")
            return True, "Bonuses already processed"

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
            # After calculate_all_bonuses_secure returns, BEFORE validation


           # ✅ ADD THIS DEBUG CODE
            print("\n🔍 DEBUG - Raw bonus_calculations before validation:")
            for i, bonus in enumerate(bonus_calculations):
                print(f"\n  Bonus {i+1}:")
                print(f"    Keys: {list(bonus.keys())}")
                print(f"    user_id: {bonus.get('user_id')}")
                print(f"    referrer_id: {bonus.get('referrer_id')}")
                print(f"    referred_id: {bonus.get('referred_id')}")
                print(f"    level: {bonus.get('level')}")
                print(f"    bonus_amount: {bonus.get('bonus_amount')}")
                print(f"    status: {bonus.get('status')}")
                print(f"    type: {bonus.get('type')}")
                print(f"    security_hash: {bonus.get('security_hash', 'MISSING')[:20] if bonus.get('security_hash') else 'MISSING'}")
                print(f"    payment_id: {bonus.get('payment_id')}")
                
                # Check for missing required fields
                required_fields = ['user_id', 'referrer_id', 'referred_id', 'payment_id', 
                                'bonus_amount', 'level', 'status', 'type', 'security_hash']
                missing = [f for f in required_fields if f not in bonus or bonus.get(f) is None]
                if missing:
                    print(f"    ❌ MISSING FIELDS: {missing}")

                    # 3. Validate bonuses
            valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonus_calculations)
            
            print(f"✅ Valid bonuses: {len(valid_bonuses)}, Invalid: {len(invalid_bonuses)}")
            
            # 4. Store valid bonuses
              # 4. Store valid bonuses
            bonus_ids = []
            bonus_amounts = {}  # Store amounts separately to avoid SQLAlchemy issues
            if valid_bonuses:
                from bonus.config import generate_security_hash
                from decimal import Decimal, InvalidOperation
                
                # ⭐ GET PURCHASING USER AND REFERRER ONCE
                purchasing_user = User.query.get(payment.user_id)
                direct_referrer_id = purchasing_user.referred_by if purchasing_user else None
                
                print(f"📌 Purchasing user: {payment.user_id}, Referrer ID: {direct_referrer_id}")
                
                for original_data in valid_bonuses:
                    bonus_data = original_data.copy()
                    try:
                        if 'purchase_id' in bonus_data:
                            bonus_data['payment_id'] = bonus_data.pop('purchase_id')
                        
                        # ✅ CRITICAL FIX: Ensure referrer_id and referred_id are present
                        if 'referrer_id' not in bonus_data or bonus_data['referrer_id'] is None:
                            bonus_data['referrer_id'] = direct_referrer_id
                            print(f"  ➕ Added missing referrer_id: {direct_referrer_id}")
                        
                        if 'referred_id' not in bonus_data or bonus_data['referred_id'] is None:
                            bonus_data['referred_id'] = payment.user_id
                            print(f"  ➕ Added missing referred_id: {payment.user_id}")
                        
                        # Ensure type is set
                        if 'type' not in bonus_data:
                            bonus_data['type'] = 'referral_bonus'
                        
                        # Convert amount to Decimal
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
                        print(f"  🔍 KEYS BEFORE BONUS CREATION: {list(bonus_data.keys())}")
                        bonus_data['bonus_amount'] = bonus_amount
                        print(f"  🔍 DEBUG - bonus_data keys before creation: {list(bonus_data.keys())}")
                        print(f"  🔍 DEBUG - 'amount' in bonus_data: {'amount' in bonus_data}")
                        if 'amount' in bonus_data:
                            print(f"  ➕ Removing 'amount' key (value: {bonus_data['amount']})")
                            del bonus_data['amount']
                            print(f"  🔍 Keys after removal: {list(bonus_data.keys())}")
                        else:
                            print(f"  ✅ 'amount' key not present")
                        # Create bonus record
                        bonus = ReferralBonus(**bonus_data)
                        
                        if not bonus.security_hash:
                            bonus.security_hash = generate_security_hash(
                                bonus.user_id, 
                                float(bonus_amount), 
                                bonus.payment_id
                            )
                        
                        db.session.add(bonus)
                        db.session.flush()
                        
                        bonus_ids.append(bonus.id)
                        bonus_amounts[bonus.id] = bonus_amount
                        
                        print(f"✅ Created bonus {bonus.id}: user={bonus.user_id}, referrer={bonus_data['referrer_id']}, referred={bonus_data['referred_id']}, amount={bonus_amount}")
                        
                    except Exception as e:
                        print(f"⚠️ Error creating bonus record: {e}")
                        import traceback
                        traceback.print_exc()
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
                        # Get bonus with fresh query
                        fresh_bonus = db.session.query(ReferralBonus).get(bonus_id)
                        
                        if not fresh_bonus:
                            print(f"⚠️ Bonus {bonus_id} not found")
                            continue
                        
                        # ✅ FIXED: Use bonus_amount, not amount
                        amount_from_bonus = fresh_bonus.bonus_amount
                        if amount_from_bonus is None:
                            amount_from_bonus = bonus_amounts.get(bonus_id, 0)
                        
                        bonus_amount_to_credit = float(amount_from_bonus)
                        
                        print(f"💰 Crediting {bonus_amount_to_credit} to user {fresh_bonus.user_id}")
                        
                        # Update bonus status
                        fresh_bonus.status = 'paid'
                        fresh_bonus.is_paid_out = True
                        fresh_bonus.paid_out_at = datetime.utcnow()
                        
                        # Credit user wallet
                        user = User.query.get(fresh_bonus.user_id)
                        if user:
                            user.available_balance = (user.available_balance or 0) + Decimal(str(bonus_amount_to_credit))
                            user.actual_balance = (user.actual_balance or 0) + Decimal(str(bonus_amount_to_credit))
                        
                        db.session.commit()
                        credited_count += 1
                        print(f"✅ Successfully credited {bonus_amount_to_credit} to user {fresh_bonus.user_id}")
                        
                    except Exception as e:
                        db.session.rollback()
                        print(f"❌ Failed to credit bonus {bonus_id}: {e}")
                        import traceback
                        traceback.print_exc()

                if credited_count > 0:
                    print(f"🎉 Successfully credited {credited_count} out of {len(bonus_ids)} bonuses")
                    
                    return True, f"Successfully processed {credited_count} bonuses"
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
    