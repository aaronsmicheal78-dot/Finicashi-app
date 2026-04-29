from decimal import Decimal
from models import ReferralBonus
from extensions import db
from flask import current_app
import sys

# Create a test version of the function with detailed logging
def test_bonus_already_exists(purchase_id, ancestor_id, level, bonus_amount):
    print(f"=== TESTING VALIDATOR ===")
    print(f"Inputs: purchase_id={purchase_id}, ancestor_id={ancestor_id}, level={level}, bonus_amount={bonus_amount}")
    
    try:
        print("Attempting db.session.rollback()...")
        try:
            db.session.rollback()
            print("  Rollback successful")
        except Exception as e:
            print(f"  Rollback failed: {e}")
    
        # Ensure Decimal
        if not isinstance(bonus_amount, Decimal):
            bonus_amount = Decimal(str(bonus_amount))
            print(f"Converted bonus_amount to Decimal: {bonus_amount}")
    
        print(f"Querying database...")
        existing = ReferralBonus.query.filter(
            ReferralBonus.payment_id == purchase_id,
            ReferralBonus.user_id == ancestor_id, 
            ReferralBonus.level == level,
            ReferralBonus.bonus_amount == bonus_amount
        ).first()
        
        print(f"Query result: {existing}")
        
        if existing:
            print(f"Found existing bonus: ID={existing.id}, Status={existing.status}")
            return True, existing.status
        else:
            print("No existing bonus found")
            return False, None
            
    except Exception as e:
        print(f"EXCEPTION CAUGHT: {e}")
        import traceback
        traceback.print_exc()
        return False, None  # Return False on error

# Test it
exists, status = test_bonus_already_exists(28, 3, 1, 5000.0)
print(f"\nFinal result: exists={exists}, status={status}")