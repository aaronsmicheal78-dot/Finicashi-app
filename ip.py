# debug_bonuses.py
import sys
sys.path.append('/path/to/your/app')  # Add your app path

from app import create_app
from extensions import db
from models import ReferralBonus

app = create_app()

with app.app_context():
    print("=== DEBUGGING BONUSES FOR PAYMENT 15 ===\n")
    
    # Count bonuses
    count = ReferralBonus.query.filter_by(payment_id=15).count()
    print(f"✓ Total bonuses for payment 15: {count}\n")
    
    if count == 0:
        print("❌ NO BONUSES CREATED for payment 15!")
        print("This means your validation is failing BEFORE database insert.")
        print("Check the validation output in your logs.")
    else:
        # Get all bonuses
        bonuses = ReferralBonus.query.filter_by(payment_id=15).all()
        
        print(f"Found {len(bonuses)} bonuses:\n")
        
        for bonus in bonuses:
            print(f"--- Bonus ID: {bonus.id} ---")
            print(f"  Created at: {bonus.created_at}")
            print(f"  User ID (recipient): {bonus.user_id}")
            print(f"  Referrer ID (sponsor): {bonus.referrer_id}")
            print(f"  Referred ID (purchaser): {bonus.referred_id}")
            print(f"  Level: {bonus.level}")
            print(f"  Amount: {bonus.bonus_amount}")
            print(f"  Status: {bonus.status}")
            print(f"  Type: {bonus.type}")
            print(f"  Security hash: {'✓ Present' if bonus.security_hash else '✗ MISSING'}")
            
            # Check for NULLs
            if bonus.referrer_id is None:
                print("  ❌ REFERRER_ID IS NULL!")
            if bonus.referred_id is None:
                print("  ❌ REFERRED_ID IS NULL!")
            if bonus.status is None:
                print("  ❌ STATUS IS NULL!")
            if bonus.type is None:
                print("  ❌ TYPE IS NULL!")
            print()
        
        # Summary
        null_count = ReferralBonus.query.filter_by(payment_id=15).filter(
            (ReferralBonus.referrer_id == None) | 
            (ReferralBonus.referred_id == None) |
            (ReferralBonus.status == None) |
            (ReferralBonus.type == None) |
            (ReferralBonus.security_hash == None)
        ).count()
        
        if null_count > 0:
            print(f"❌ {null_count} bonuses have NULL required fields")
        else:
            print("✅ ALL bonuses have valid required fields!")