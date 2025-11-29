

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
import uuid
import logging
from flask import session
from extensions import db
from models import User, Wallet, Package, Bonus, Transaction

logger = logging.getLogger(__name__)

class BonusSecurityError(Exception):
    """Security-related bonus errors"""
    pass

class BonusValidationError(Exception):
    """Bonus validation errors"""
    pass

class DailyBonusProcessor:
    """Secure daily bonus processor with comprehensive validation"""
    
    DAILY_RATE = Decimal("0.05")  # 5%
    MAX_PAYOUT_RATE = Decimal("0.75")  # 75%
    BONUS_COOLDOWN_HOURS = 24
    
    def __init__(self, user_id):
        self.user_id = user_id
    # def run(self):
    #     self.current_time = datetime.utcnow()
    #     self.processed_count = 0
    #     self.errors = []
    def run(self):
        """Entry point for external callers"""
        self.current_time = datetime.utcnow()
        self.processed_count = 0
        self.errors = []

        # call the main processor
        return self.process_user_bonus(self.user_id)

    
    
    def safe_decimal(self, value, field_name: str) -> Decimal:
        """Secure decimal conversion with validation"""
        if value is None:
            raise BonusValidationError(f"{field_name} cannot be None")
        
        try:
            if isinstance(value, (int, float, str)):
                return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
            elif isinstance(value, Decimal):
                return value.quantize(Decimal("0.01"), ROUND_HALF_UP)
            else:
                raise BonusValidationError(f"Invalid type for {field_name}: {type(value)}")
        except (InvalidOperation, ValueError, TypeError) as e:
            raise BonusValidationError(f"Decimal conversion failed for {field_name}: {e}")
    
    def validate_user(self, user: User) -> bool:
        """Comprehensive user validation"""
        if not user:
            raise BonusSecurityError("User not found")
        
        if not user.is_active:
            raise BonusValidationError("User account is inactive")
        
        # if user.is_suspended:
        #     raise BonusSecurityError("User account is suspended")
        
        return True
    
    def validate_package_status(self, package: Package) -> bool:
        """Validate package status and lifecycle"""
        if not package:
            raise BonusValidationError("Package not found")
        
        if package.status != 'active':
            raise BonusValidationError(f"Package status is '{package.status}', not 'active'")
        
        if package.is_bonus_locked:
            raise BonusSecurityError("Package bonus is locked")
        
        # Check activation
        if not package.activated_at:
            raise BonusValidationError("Package not activated")
        
        # Check expiration
        if package.expires_at and self.current_time > package.expires_at:
            package.status = 'expired'
            db.session.add(package)
            raise BonusValidationError("Package has expired")
        
        # Standard 60-day expiration
        standard_expiry = package.activated_at + timedelta(days=60)
        if self.current_time > standard_expiry:
            package.status = 'expired'
            db.session.add(package)
            raise BonusValidationError("Package has expired (60-day limit)")
        
        return True
    
    def validate_bonus_timing(self, package: Package) -> bool:
        """Validate bonus timing and cooldown"""
        # First bonus check
        if not package.last_bonus_date:
            # Allow first bonus 24 hours after activation
            first_bonus_time = package.activated_at + timedelta(hours=24)
            if self.current_time < first_bonus_time:
                raise BonusValidationError("First bonus not yet available (24-hour cooldown)")
            return True
        
        # Subsequent bonuses - check cooldown
        if package.next_bonus_date and self.current_time < package.next_bonus_date:
            time_remaining = package.next_bonus_date - self.current_time
            hours_remaining = time_remaining.total_seconds() / 3600
            raise BonusValidationError(f"Bonus cooldown active. {hours_remaining:.1f} hours remaining")
        
        # Ensure at least 24 hours between bonuses
        if package.last_bonus_date:
            time_since_last = self.current_time - package.last_bonus_date
            if time_since_last < timedelta(hours=24):
                raise BonusSecurityError("Minimum 24 hours between bonuses not met")
        
        return True
    
    def validate_bonus_limits(self, package: Package) -> Tuple[Decimal, Decimal, Decimal]:
        """Validate and calculate bonus limits"""
        package_amount = self.safe_decimal(package.package_amount, "package_amount")
        current_total_paid = self.safe_decimal(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
        
        # Calculate max payout (75% of package)
        max_payout = (package_amount * self.MAX_PAYOUT_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        # Update max_bonus_amount if not set
        if not package.max_bonus_amount or package.max_bonus_amount != max_payout:
            package.max_bonus_amount = max_payout
        
        # Check if max payout reached
        if current_total_paid >= max_payout:
            package.status = 'completed'
            db.session.add(package)
            raise BonusValidationError("Maximum bonus payout reached")
        
        # Calculate daily bonus (5% of package)
        daily_bonus = (package_amount * self.DAILY_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        # Apply remaining limit
        remaining_limit = max_payout - current_total_paid
        if daily_bonus > remaining_limit:
            daily_bonus = remaining_limit
        
        if daily_bonus <= Decimal("0"):
            raise BonusValidationError("No bonus available - limit reached")
        
        return daily_bonus, max_payout, remaining_limit
    
    def update_package_after_bonus(self, package: Package, daily_bonus: Decimal) -> None:
        """Update package after successful bonus payment"""
        try:
            # Update bonus tracking
            package.last_bonus_date = self.current_time
            package.next_bonus_date = self.current_time + timedelta(hours=self.BONUS_COOLDOWN_HOURS)
            package.bonus_count += 1
            package.total_days_paid += 1
            
            # Update total bonus paid
            current_total = self.safe_decimal(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
            package.total_bonus_paid = current_total + daily_bonus
            
            # Check if package completed
            if package.total_bonus_paid >= package.max_bonus_amount:
                package.status = 'completed'
                logger.info(f"Package {package.id} completed - max payout reached")
            
            package.updated_at = self.current_time
            
        except Exception as e:
            raise BonusValidationError(f"Failed to update package: {e}")
    
    def create_bonus_transaction(self, user_id: int, wallet_id: int, 
                               amount: Decimal, package_id: int) -> str:
        """Create audit trail for bonus payment"""
        try:
            # Create bonus record
            bonus = Bonus(
                user_id=user_id,
                package_id=package_id,
                type="daily",
                amount=amount,
                status="paid",
                paid_at=self.current_time,
                created_at=self.current_time
            )
            db.session.add(bonus)
            
            # Create transaction
            transaction_ref = f"BONUS-{uuid.uuid4().hex[:12].upper()}"
            transaction = Transaction(
                wallet_id=wallet_id,
                package_id=package_id,
                type="bonus_credit",
                amount=amount,
                status="completed",
                reference=transaction_ref,
                description=f"Daily bonus for package {package_id}",
                created_at=self.current_time
            )
            db.session.add(transaction)
            
            return transaction_ref
            
        except Exception as e:
            raise BonusSecurityError(f"Failed to create bonus records: {e}")
    
    def get_user_wallet(self, user_id: int) -> Wallet:
        """Get or create user wallet with validation"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(
                user_id=user_id,
                balance=Decimal("0.00"),
                created_at=self.current_time
            )
            db.session.add(wallet)
            db.session.flush()
        
        # Validate wallet
        # if wallet.is_locked:
        #     raise BonusSecurityError("Wallet is locked")
        
        return wallet
    
    def process_single_package(self, package: Package, wallet: Wallet) -> Dict:
        """Process bonus for a single package with full validation"""
        package_result = {
            "package_id": package.id,
            "package_name": package.package,
            "success": False,
            "bonus_amount": 0.0,
            "error": None,
            "transaction_ref": None
        }
        
        try:
            # Comprehensive validation chain
            self.validate_package_status(package)
            self.validate_bonus_timing(package)
            daily_bonus, max_payout, remaining_limit = self.validate_bonus_limits(package)
            
            # All validations passed - process bonus
            old_balance = self.safe_decimal(wallet.balance, "wallet_balance")
            wallet.balance = old_balance + daily_bonus
            wallet.updated_at = self.current_time
            
            # Update package
            self.update_package_after_bonus(package, daily_bonus)
            
            # Create audit trail
            transaction_ref = self.create_bonus_transaction(
                package.user_id, wallet.id, daily_bonus, package.id
            )
            
            package_result.update({
                "success": True,
                "bonus_amount": float(daily_bonus),
                "transaction_ref": transaction_ref,
                "old_balance": float(old_balance),
                "new_balance": float(wallet.balance),
                "remaining_limit": float(remaining_limit - daily_bonus)
            })
            
            self.processed_count += 1
            logger.info(f"Bonus paid for package {package.id}: ${daily_bonus}")
            
        except (BonusValidationError, BonusSecurityError) as e:
            package_result["error"] = str(e)
            logger.warning(f"Bonus skipped for package {package.id}: {e}")
        except Exception as e:
            package_result["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error processing package {package.id}: {e}")
        
        return package_result
    
    def process_user_bonus(self, user_id: int) -> Dict:
        """Main method to process daily bonus for a user"""
        response = {
            "success": False,
            "user_id": user_id,
            "total_bonus": 0.0,
            "wallet_balance": 0.0,
            "packages_processed": 0,
            "packages_successful": 0,
            "packages_failed": 0,
            "processed_packages": [],
            "timestamp": self.current_time.isoformat(),
            "error": None
        }
        
        db_session = db.session
        
        try:
            # Begin transaction
           #db_session.begin()
            
            # Validate user
            user = User.query.get(user_id)
            self.validate_user(user)
            
            # Get wallet
            wallet = self.get_user_wallet(user_id)
            initial_balance = self.safe_decimal(wallet.balance, "wallet_balance")
            
            # Get eligible packages
            packages = Package.query.filter_by(
                user_id=user_id, 
                status='active'
            ).all()
            
            if not packages:
                response.update({
                    "success": True,
                    "wallet_balance": float(initial_balance),
                    "message": "No active packages found"
                })
                return response
            
            total_bonus = Decimal("0.00")
            processed_packages = []
            
            # Process each package
            for package in packages:
                result = self.process_single_package(package, wallet)
                processed_packages.append(result)
                
                if result["success"]:
                    total_bonus += self.safe_decimal(result["bonus_amount"], "bonus_amount")
            
            # Commit only if we have successful processing
            if total_bonus > Decimal("0"):
                db_session.commit()
                logger.info(f"Daily bonus completed for user {user_id}: ${total_bonus}")
            else:
                db_session.rollback()
            
            # Prepare response
            successful_packages = [p for p in processed_packages if p["success"]]
            failed_packages = [p for p in processed_packages if not p["success"]]
            
            response.update({
                "success": True,
                "total_bonus": float(total_bonus),
                "wallet_balance": float(wallet.balance),
                "packages_processed": len(processed_packages),
                "packages_successful": len(successful_packages),
                "packages_failed": len(failed_packages),
                "processed_packages": processed_packages
            })
            
        except (BonusSecurityError, BonusValidationError) as e:
            db_session.rollback()
            response["error"] = str(e)
            logger.error(f"Bonus processing failed for user {user_id}: {e}")
            
        except SQLAlchemyError as e:
            db_session.rollback()
            response["error"] = f"Database error: {str(e)}"
            logger.error(f"Database error processing bonus for user {user_id}: {e}")
            
        except Exception as e:
            db_session.rollback()
            response["error"] = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error processing bonus for user {user_id}: {e}", exc_info=True)
        
        return response