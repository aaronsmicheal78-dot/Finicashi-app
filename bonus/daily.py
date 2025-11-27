from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from flask import current_app
from extensions import db
from models import Package, Bonus, Wallet

DAILY_RATE = Decimal("0.05")  # 5% daily bonus
TOTAL_LIMIT = Decimal("0.75")  # 75% total payout limit


def process_daily_bonuses():
    """
    Run daily to apply 5% bonuses to all active user packages.
    Adds bonus to user's wallet and stops when total reaches 75% of package amount.
    """
    processed_count = 0
    completed_count = 0
    total_payout = Decimal("0")
    
    try:
        # Query all active packages
        packages = Package.query.filter_by(status="active").all()

        if not packages:
            current_app.logger.info("No active packages found for bonus processing.")
            return {
                "processed": 0,
                "completed": 0,
                "total_payout": 0,
                "message": "No active packages found"
            }

        current_app.logger.info(f"Starting bonus processing for {len(packages)} active packages.")

        for package in packages:
            try:
                result = apply_daily_bonus_to_package(package)
                if result["processed"]:
                    processed_count += 1
                    total_payout += result["payout_amount"]
                if result["completed"]:
                    completed_count += 1
                    
            except Exception as e:
                current_app.logger.error(f"Failed to process package {package.id}: {e}")
                continue

        db.session.commit()
        
        current_app.logger.info(
            f"Daily bonus processing completed. "
            f"Processed: {processed_count}, Completed: {completed_count}, Total Payout: ${total_payout}"
        )

        return {
            "processed": processed_count,
            "completed": completed_count,
            "total_payout": float(total_payout),
            "total_packages": len(packages)
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bonus processing failed: {e}")
        raise


def apply_daily_bonus_to_package(package):
    """
    Applies 5% daily bonus to a package and adds to user's wallet.
    Stops when total bonus paid reaches 75% of package amount.
    
    Returns: dict with processed, completed flags and payout amount
    """
    # Convert all amounts to Decimal with proper error handling
    try:
        package_amount = Decimal(str(package.amount))
        total_paid_so_far = Decimal(str(package.total_bonus_paid or "0"))
    except (TypeError, ValueError) as e:
        current_app.logger.error(f"Invalid decimal values for package {package.id}: {e}")
        return {"processed": False, "completed": False, "payout_amount": Decimal("0")}

    # Calculate the 75% total payout limit
    total_payout_limit = package_amount * TOTAL_LIMIT

    # Check if package already reached the 75% limit
    if total_paid_so_far >= total_payout_limit:
        package.status = "completed"
        current_app.logger.info(f"Package {package.id} already at 75% limit, marking completed")
        return {"processed": False, "completed": True, "payout_amount": Decimal("0")}

    # Calculate today's 5% bonus
    daily_bonus = package_amount * DAILY_RATE

    # Ensure we don't exceed the 75% total limit
    remaining_allowance = total_payout_limit - total_paid_so_far
    
    if daily_bonus > remaining_allowance:
        # Only pay the remaining amount to exactly reach 75%
        todays_payout = remaining_allowance
        will_complete = True
    else:
        todays_payout = daily_bonus
        will_complete = (total_paid_so_far + todays_payout) >= total_payout_limit

    # Round to avoid tiny decimal discrepancies (2 decimal places for currency)
    todays_payout = todays_payout.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
    # Skip if payout would be zero (due to rounding or limits)
    if todays_payout <= Decimal('0'):
        current_app.logger.info(f"Zero payout for package {package.id}, skipping")
        return {"processed": False, "completed": False, "payout_amount": Decimal("0")}

    # Update package total bonus paid
    new_total_paid = total_paid_so_far + todays_payout
    package.total_bonus_paid = new_total_paid

    # Mark completed if we hit the 75% limit
    if will_complete:
        package.status = "completed"
        current_app.logger.info(f"Package {package.id} reached 75% limit, marking completed")

    # Add bonus to user's wallet
    wallet_updated = add_bonus_to_wallet(package.user_id, todays_payout)
    if not wallet_updated:
        raise Exception(f"Failed to update wallet for user {package.user_id}")

    # Log the bonus transaction
    log_bonus_transaction(package, todays_payout)

    current_app.logger.info(
        f"Package {package.id}: Paid ${todays_payout}, Total: ${new_total_paid}/${total_payout_limit}"
    )

    return {
        "processed": True, 
        "completed": will_complete,
        "payout_amount": todays_payout
    }


def add_bonus_to_wallet(user_id, amount):
    """
    Adds bonus amount to user's wallet balance.
    Uses thread-safe update with row locking to prevent race conditions.
    """
    try:
        # Convert amount to Decimal if not already
        bonus_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        
        # Get or create wallet for user with row lock
        wallet = Wallet.query.filter_by(user_id=user_id).with_for_update().first()
        
        if not wallet:
            # Create new wallet if doesn't exist
            wallet = Wallet(user_id=user_id, balance=bonus_amount)
            db.session.add(wallet)
            current_app.logger.info(f"Created new wallet for user {user_id} with initial balance: ${bonus_amount}")
        else:
            # Update existing wallet balance
            old_balance = Decimal(str(wallet.balance))
            new_balance = old_balance + bonus_amount
            wallet.balance = new_balance
            current_app.logger.debug(f"Updated wallet for user {user_id}: ${old_balance} + ${bonus_amount} = ${new_balance}")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to update wallet for user {user_id}: {e}")
        return False


def log_bonus_transaction(package, amount):
    """
    Logs bonus transaction with proper Decimal handling.
    """
    try:
        # Ensure amount is properly converted to Decimal
        bonus_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
        
        bonus = Bonus(
            user_id=package.user_id,
            package_id=package.id,
            amount=bonus_amount,
            created_at=datetime.utcnow(),
            status="paid",
            type="daily_bonus"
        )
        db.session.add(bonus)
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to log bonus transaction for package {package.id}: {e}")
        return False


def get_package_progress(package):
    """
    Get detailed progress information for a package.
    """
    try:
        package_amount = Decimal(str(package.amount))
        total_paid = Decimal(str(package.total_bonus_paid or "0"))
        
        total_limit = package_amount * TOTAL_LIMIT
        daily_payout = package_amount * DAILY_RATE
        remaining_days = (total_limit - total_paid) / daily_payout if daily_payout > 0 else Decimal("0")
        
        return {
            "package_id": package.id,
            "package_amount": package_amount,
            "total_paid": total_paid,
            "daily_payout": daily_payout,
            "total_limit": total_limit,
            "progress_percent": (total_paid / total_limit * 100).quantize(Decimal('0.01')),
            "remaining_days": remaining_days.quantize(Decimal('0.1')),
            "status": package.status
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting progress for package {package.id}: {e}")
        return None


def calculate_package_completion_days(package):
    """
    Calculate how many days until package reaches 75% completion.
    """
    try:
        package_amount = Decimal(str(package.amount))
        total_paid = Decimal(str(package.total_bonus_paid or "0"))
        
        total_limit = package_amount * TOTAL_LIMIT
        daily_payout = package_amount * DAILY_RATE
        
        if daily_payout <= 0:
            return Decimal("0")
            
        remaining = total_limit - total_paid
        if remaining <= 0:
            return Decimal("0")
            
        days = remaining / daily_payout
        return days.quantize(Decimal('0.1'))
        
    except Exception as e:
        current_app.logger.error(f"Error calculating completion days for package {package.id}: {e}")
        return Decimal("0")


# Admin reporting functions
def get_daily_bonus_report():
    """
    Generate a report of today's bonus payments.
    """
    try:
        today = datetime.utcnow().date()
        today_bonuses = Bonus.query.filter(
            Bonus.created_at >= today,
            Bonus.type == "daily_bonus"
        ).all()
        
        total_payout = Decimal("0")
        package_payouts = {}
        
        for bonus in today_bonuses:
            amount = Decimal(str(bonus.amount))
            total_payout += amount
            
            if bonus.package_id not in package_payouts:
                package_payouts[bonus.package_id] = Decimal("0")
            package_payouts[bonus.package_id] += amount
        
        return {
            "report_date": today,
            "total_packages": len(package_payouts),
            "total_payout": total_payout,
            "package_payouts": package_payouts,
            "transactions": len(today_bonuses)
        }
        
    except Exception as e:
        current_app.logger.error(f"Error generating daily bonus report: {e}")
        return None


def get_user_bonus_summary(user_id):
    """
    Get bonus summary for a specific user.
    """
    try:
        user_packages = Package.query.filter_by(user_id=user_id).all()
        total_invested = Decimal("0")
        total_earned = Decimal("0")
        total_expected = Decimal("0")
        active_packages = 0
        
        for package in user_packages:
            package_amount = Decimal(str(package.amount))
            package_earned = Decimal(str(package.total_bonus_paid or "0"))
            
            total_invested += package_amount
            total_earned += package_earned
            
            if package.status == "active":
                active_packages += 1
                package_expected = package_amount * TOTAL_LIMIT
                total_expected += package_expected
        
        return {
            "user_id": user_id,
            "total_invested": total_invested,
            "total_earned": total_earned,
            "total_expected": total_expected,
            "active_packages": active_packages,
            "completion_percentage": (total_earned / total_expected * 100).quantize(Decimal('0.01')) if total_expected > 0 else Decimal("0")
        }
        
    except Exception as e:
        current_app.logger.error(f"Error getting user bonus summary for user {user_id}: {e}")
        return None
    
    # Process daily bonuses
result = process_daily_bonuses()
print(f"Paid ${result['total_payout']} to {result['processed']} packages")

# Check package progress
package = Package.query.first()
progress = get_package_progress(package)
print(f"Progress: {progress['progress_percent']}%")
print(f"Remaining days: {progress['remaining_days']}")

# Get user summary
user_summary = get_user_bonus_summary(1)
print(f"User earned: ${user_summary['total_earned']}")