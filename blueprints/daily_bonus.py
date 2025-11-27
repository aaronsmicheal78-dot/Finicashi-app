from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from flask import current_app
from extensions import db
from models import Package, Bonus, Wallet

DAILY_RATE = Decimal("0.05")  # 5% daily bonus
TOTAL_LIMIT = Decimal("0.75")  # 75% total payout limit


class DailyBonusManager:
    """
    Handles daily bonus package creation and processing separately from referral system.
    This ONLY deals with creating packages and daily bonus logic.
    """
    
    @staticmethod
    def create_package_from_payment(payment):
        """
        Create a package for daily bonus processing after successful payment.
        This should be called after payment is completed.
        """
        try:
            user = payment.user
            amount = Decimal(str(payment.amount))
            
          
            package = Package(
                user_id=user.id,
                amount=amount,
                original_amount=amount,
                daily_bonus_rate=DAILY_RATE,
                total_bonus_paid=Decimal("0"),
                status="active",
                purchase_date=datetime.utcnow(),
                payment_id=payment.id,
                created_at=datetime.utcnow()
            )
            
            db.session.add(package)
            db.session.flush() 
            print(f"Package created twice: {package}")
            
            current_app.logger.info(
                f"Daily bonus package created: ID {package.id}, "
                f"User {user.id}, Amount ${amount}"
            )
            
            return package, "Package created successfully for daily bonuses"
            
        except Exception as e:
            current_app.logger.error(f"Failed to create daily bonus package: {e}")
            return None, f"Package creation failed: {str(e)}"
    
    @staticmethod
    def process_daily_bonuses():
        """
        Process daily 5% bonuses for all active packages.
        This runs separately (cron job) and pays out until 75% total.
        """
        processed_count = 0
        completed_count = 0
        total_payout = Decimal("0")
        
        try:
            packages = Package.query.filter_by(status="active").all()

            if not packages:
                current_app.logger.info("No active packages for daily bonuses.")
                return {
                    "processed": 0,
                    "completed": 0,
                    "total_payout": 0
                }

            current_app.logger.info(f"Processing daily bonuses for {len(packages)} packages.")

            for package in packages:
                try:
                    result = DailyBonusManager._apply_daily_bonus(package)
                    if result["processed"]:
                        processed_count += 1
                        total_payout += result["payout_amount"]
                    if result["completed"]:
                        completed_count += 1
                        
                except Exception as e:
                    current_app.logger.error(f"Daily bonus failed for package {package.id}: {e}")
                    continue

            db.session.commit()
            
            current_app.logger.info(
                f"Daily bonuses completed. Processed: {processed_count}, "
                f"Completed: {completed_count}, Payout: ${total_payout}"
            )

            return {
                "processed": processed_count,
                "completed": completed_count,
                "total_payout": float(total_payout)
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Daily bonus processing failed: {e}")
            raise
    
    @staticmethod
    def _apply_daily_bonus(package):
        """Apply daily 5% bonus to a package and add to user's wallet."""
        try:
            package_amount = Decimal(str(package.amount))
            total_paid_so_far = Decimal(str(package.total_bonus_paid or "0"))
            
            total_payout_limit = package_amount * TOTAL_LIMIT

            if total_paid_so_far >= total_payout_limit:
                package.status = "completed"
                return {"processed": False, "completed": True, "payout_amount": Decimal("0")}

            daily_bonus = package_amount * DAILY_RATE

           
            remaining_allowance = total_payout_limit - total_paid_so_far
            
            if daily_bonus > remaining_allowance:
                todays_payout = remaining_allowance
                will_complete = True
            else:
                todays_payout = daily_bonus
                will_complete = (total_paid_so_far + todays_payout) >= total_payout_limit

            
            todays_payout = todays_payout.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            
          
            if todays_payout <= Decimal('0'):
                return {"processed": False, "completed": False, "payout_amount": Decimal("0")}

           
            new_total_paid = total_paid_so_far + todays_payout
            package.total_bonus_paid = new_total_paid

      
            if will_complete:
                package.status = "completed"
                current_app.logger.info(f"Package {package.id} reached 75% limit, marking completed")

         
            wallet_updated = DailyBonusManager._add_to_wallet(package.user_id, todays_payout)
            if not wallet_updated:
                raise Exception(f"Failed to update wallet for user {package.user_id}")

           
            DailyBonusManager._log_daily_bonus(package, todays_payout)

            current_app.logger.info(
                f"Package {package.id}: Daily bonus ${todays_payout}, "
                f"Total: ${new_total_paid}/${total_payout_limit}"
            )

            return {
                "processed": True, 
                "completed": will_complete,
                "payout_amount": todays_payout
            }

        except Exception as e:
            current_app.logger.error(f"Error applying daily bonus to package {package.id}: {e}")
            return {"processed": False, "completed": False, "payout_amount": Decimal("0")}
    
    @staticmethod
    def _add_to_wallet(user_id, amount):
        """Add bonus amount to user's wallet balance."""
        try:
            bonus_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
            
           
            wallet = Wallet.query.filter_by(user_id=user_id).first()
            
            if not wallet:
              
                wallet = Wallet(user_id=user_id, balance=bonus_amount)
                db.session.add(wallet)
                current_app.logger.info(f"Created new wallet for user {user_id}")
            else:
               
                old_balance = Decimal(str(wallet.balance))
                new_balance = old_balance + bonus_amount
                wallet.balance = new_balance
                current_app.logger.debug(f"Updated wallet for user {user_id}")
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to update wallet for user {user_id}: {e}")
            return False
    
    @staticmethod
    def _log_daily_bonus(package, amount):
        """Log daily bonus transaction."""
        try:
            bonus_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
            
            bonus = Bonus(
                user_id=package.user_id,
                package_id=package.id,
                amount=bonus_amount,
                created_at=datetime.utcnow(),
                status="paid",
                bonus_type="daily"  # Differentiate from referral bonuses
            )
            db.session.add(bonus)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to log daily bonus for package {package.id}: {e}")
            return False
    
    @staticmethod
    def get_user_active_packages(user_id):
        """Get all active packages for a user."""
        return Package.query.filter_by(user_id=user_id, status="active").all()
    
    @staticmethod
    def get_package_progress(package_id):
        """Get progress of a specific package."""
        package = Package.query.get(package_id)
        if not package:
            return None
            
        package_amount = Decimal(str(package.amount))
        total_paid = Decimal(str(package.total_bonus_paid or "0"))
        total_limit = package_amount * TOTAL_LIMIT
        
        return {
            "package_id": package.id,
            "amount": package_amount,
            "total_paid": total_paid,
            "total_limit": total_limit,
            "progress_percent": (total_paid / total_limit * 100).quantize(Decimal('0.01')),
            "remaining": total_limit - total_paid,
            "status": package.status
        }