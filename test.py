
import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from models import User, Transaction, Package
from blueprints.withdraw_helpers import WithdrawalConfig, WithdrawalValidator
from extensions import db
from sqlalchemy import func

def test_check_mature_wallet_balance_for_user_16(app_context):
    """Test to check mature wallet balance for user ID 16"""
    
    # Get user with ID 16
    user = User.query.get(16)
    
    if not user:
        print(f"User with ID 16 not found")
        return None
    
    # Call the method
    mature_balance = WithdrawalValidator._get_mature_wallet_balance(user)
    
    print(f"\n{'='*50}")
    print(f"Results for User ID: {user.id}")
    print(f"{'='*50}")
    print(f"Wallet Balance: {user.wallet.balance if user.wallet else 0}")
    print(f"Mature Wallet Balance: {mature_balance}")
    print(f"{'='*50}\n")
    
    return mature_balance

# Alternative: Direct test without calling the method
def test_direct_calculation_for_user_16(app_context):
    """Calculate mature balance directly for user 16"""
    
    user = User.query.get(16)
    
    if not user:
        print("User 16 not found")
        return None
    
    hold_cutoff = datetime.now(timezone.utc) - timedelta(
        hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS
    )
    
    valid_credit_types = ['credit', 'bonus_credit', 'referral_bonus', 'refund']
    
    # Calculate mature total from transactions
    mature_total = db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0'))).filter(
        Transaction.type.in_(valid_credit_types),
        Transaction.user_id == user.id,
        Transaction.status == 'completed',
        Transaction.created_at < hold_cutoff
    ).scalar()
    
    mature_total = Decimal(str(mature_total or 0))
    wallet_balance = Decimal(str(user.wallet.balance if user.wallet else 0))
    mature_balance = min(mature_total, wallet_balance)
    
    print(f"\n{'='*50}")
    print(f"DETAILED ANALYSIS FOR USER {user.id}")
    print(f"{'='*50}")
    print(f"Hold Cutoff Time: {hold_cutoff}")
    print(f"Wallet Balance: {wallet_balance}")
    print(f"Mature Total (from transactions): {mature_total}")
    print(f"Final Mature Balance: {mature_balance}")
    
    # Show individual transactions
    transactions = Transaction.query.filter(
        Transaction.user_id == user.id,
        Transaction.type.in_(valid_credit_types),
        Transaction.status == 'completed'
    ).all()
    
    print(f"\nRelevant Transactions:")
    print(f"{'ID':<5} {'Type':<20} {'Amount':<10} {'Status':<12} {'Created At'}")
    print(f"{'-'*60}")
    
    for tx in transactions:
        mature_status = "MATURE" if tx.created_at < hold_cutoff else "HOLDING"
        print(f"{tx.id:<5} {tx.type:<20} {tx.amount:<10} {tx.status:<12} "
              f"{tx.created_at.strftime('%Y-%m-%d %H:%M')} [{mature_status}]")
    
    print(f"{'='*50}\n")
    
    return {
        'user_id': user.id,
        'wallet_balance': wallet_balance,
        'mature_total': mature_total,
        'mature_balance': mature_balance
    }

# Simple test script (no pytest required)
def simple_check():
    """Simple function to check user 16's mature balance"""
    from app import create_app
    app = create_app()
    
    with app.app_context():
        # user = User.query.get(16)
        # hold_cutoff = datetime.now(timezone.utc) - timedelta(hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS)

        # print(f"Hold cutoff time: {hold_cutoff}")
        # print(f"\nAll user transactions:")

        # transactions = Transaction.query.filter_by(user_id=user.id).all()

        # for tx in transactions:
        #     is_mature = tx.created_at < hold_cutoff
        #     is_valid_type = tx.type in ['credit', 'bonus_credit', 'referral_bonus', 'refund']
        #     is_completed = tx.status == 'completed'
            
        #     print(f"Type: {tx.type:20} Amount: {tx.amount:10} Status: {tx.status:10} "
        #         f"Created: {tx.created_at.strftime('%Y-%m-%d %H:%M')} "
        #         f"Mature: {is_mature} ValidType: {is_valid_type} Completed: {is_completed}")
        #     print(f"  -> Would count: {is_mature and is_valid_type and is_completed}")
        # transaction = Transaction.query.filter_by(user_id=16, type='bonus_credit').first()
        # mature_time = transaction.created_at + timedelta(hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS)

        # print(f"Transaction created: {transaction.created_at}")
        # print(f"Will become mature at: {mature_time}")
        # print(f"Time remaining: {mature_time - datetime.now(timezone.utc)}")
        # # user = User.query.get(16)


        # transaction = Transaction.query.filter_by(user_id=16, type='bonus_credit').first()

        # # Get the actual hold_cutoff used in the query
        # hold_cutoff = datetime.now(timezone.utc) - timedelta(hours=WithdrawalConfig.WALLET_HOLD_PERIOD_HOURS)

        # print(f"=== TIMEZONE DEBUG ===")
        # print(f"Transaction.created_at: {transaction.created_at}")
        # print(f"Transaction.created_at tzinfo: {transaction.created_at.tzinfo}")
        # print(f"Current UTC: {datetime.now(timezone.utc)}")
        # print(f"Hold cutoff: {hold_cutoff}")
        # print(f"Is transaction < cutoff? {transaction.created_at < hold_cutoff}")
        # print(f"Raw comparison: {transaction.created_at} < {hold_cutoff}")

        # # Check what the database query actually returns
        # from sqlalchemy import text

        # # Direct SQL query to see what's happening
        # sql_check = text("""
        #     SELECT 
        #         created_at,
        #         created_at < (NOW() - INTERVAL '24 hours') as is_mature
        #     FROM transactions 
        #     WHERE user_id = 16 AND type = 'bonus_credit'
        # """)

        # result = db.session.execute(sql_check).first()
        # print(f"\n=== DATABASE DIRECT CHECK ===")
        # print(f"Database created_at: {result[0]}")
        # print(f"Database says is_mature: {result[1]}")

        # # Now test the actual maturity query
        # valid_credit_types = ['credit', 'bonus_credit', 'referral_bonus', 'refund']
        # mature_result = db.session.query(
        #     func.sum(Transaction.amount)
        # ).filter(
        #     Transaction.type.in_(valid_credit_types),
        #     Transaction.user_id == user.id,
        #     Transaction.status == 'completed',
        #     Transaction.created_at < hold_cutoff
        # ).first()

        # print(f"\n=== QUERY RESULT ===")
        # print(f"Mature sum from query: {mature_result[0]}")

        user = User.query.get(16)
        package = Package.query.filter_by(user_id=16).first()

        print(f"Package for {user} activated_at: {package.activated_at}")
        print(f"Package for {user} activated_at tzinfo: {package.activated_at.tzinfo}")
        print(f"Package for {user} created_at: {package.created_at}")
        print(f"Package for {user} created_at tzinfo: {package.created_at.tzinfo}")

        from datetime import datetime, timezone
        print(f"Current UTC (aware): {datetime.now(timezone.utc)}")
        print(f"Current UTC (naive): {datetime.utcnow()}")
        from datetime import datetime, timedelta, timezone
        from models import Bonus

    
        activated_at_utc = package.activated_at  # This is aware
        current_utc = datetime.now(timezone.utc)

        first_bonus_time = activated_at_utc + timedelta(hours=24)

        print(f"Activated: {activated_at_utc}")
        print(f"First bonus time: {first_bonus_time}")
        print(f"Current UTC: {current_utc}")
        print(f"Is current >= first bonus? {current_utc >= first_bonus_time}")
        print(f"Time difference: {current_utc - first_bonus_time}")

        # Also check if bonus was already paid
        bonus = Bonus.query.filter_by(user_id=16, package_id=package.id, type='daily').first()
        print(f"\nBonus already paid: {bonus is not None}")
        if bonus:
            print(f"Bonus paid at: {bonus.paid_at}")

    

        transaction = Transaction.query.filter_by(user_id=16, type='bonus_credit').first()
        holding_end = transaction.created_at + timedelta(hours=24)
        now = datetime.now(timezone.utc)
        
        print(f"Bonus paid: {transaction.created_at}")
        print(f"Available for withdrawal: {holding_end}")
        print(f"Current time: {now}")
        print(f"Can withdraw now: {now >= holding_end}")
        print(f"Time remaining: {holding_end - now}")
        if datetime.now(timezone.utc) >= datetime(2026, 5, 3, 18, 15, 29, tzinfo=timezone.utc):
            mature_balance = WithdrawalValidator._get_mature_wallet_balance(user)
            print(f"Mature balance should now be: 10000.00")
            print(f"Actual: {mature_balance}")

if __name__ == "__main__":
    simple_check()