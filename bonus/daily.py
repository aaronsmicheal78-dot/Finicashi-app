
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, List, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
import uuid
import logging
from flask import session
from extensions import db
from models import User, Wallet, Package, Bonus, Transaction, Notification

logger = logging.getLogger(__name__)

class BonusSecurityError(Exception):
    """Security-related bonus errors"""
    pass

class BonusValidationError(Exception):
    """Bonus validation errors"""
    pass

TEST_MODE = True

class DailyBonusProcessor:
    """Secure daily bonus processor with comprehensive validation"""
    
    DAILY_RATE = Decimal("0.05")  # 5%
    MAX_PAYOUT_RATE = Decimal("0.75")  # 75%
    BONUS_COOLDOWN_HOURS = 24
    
    def __init__(self, user_id):
        self.user_id = user_id
    
    @staticmethod
    def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is UTC timezone-aware"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def make_naive_if_needed(dt: Optional[datetime]) -> Optional[datetime]:
        """Convert to naive datetime for database storage if needed"""
        if dt is None:
            return None
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    
    def run(self):
        """Entry point for external callers"""
        self.current_time = datetime.now(timezone.utc)
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
        
        # Ensure activated_at is timezone-aware for comparison
        activated_at_utc = self.ensure_utc(package.activated_at)
        
        # Check expiration
        if package.expires_at:
            expires_at_utc = self.ensure_utc(package.expires_at)
            if self.current_time > expires_at_utc:
                package.status = 'expired'
                db.session.add(package)
                raise BonusValidationError("Package has expired")
        
        return True
    
    def validate_bonus_timing(self, package: Package) -> bool:
        """Validate bonus timing and cooldown"""
        # Ensure current time is UTC
        current_utc = self.current_time
        
        # Ensure activated_at is timezone-aware
        activated_at_utc = self.ensure_utc(package.activated_at)
        
        # First bonus check
        if not package.last_bonus_date:
            # Allow first bonus 24 hours after activation
            first_bonus_time = activated_at_utc + timedelta(hours=24)
            
            if current_utc < first_bonus_time:
                time_remaining = first_bonus_time - current_utc
                hours_remaining = time_remaining.total_seconds() / 3600
                raise BonusValidationError(f"First bonus not yet available. {hours_remaining:.1f} hours remaining")
            return True
        
        # Ensure last_bonus_date is timezone-aware
        last_bonus_utc = self.ensure_utc(package.last_bonus_date)
        
        # Subsequent bonuses - check cooldown
        if package.next_bonus_date:
            next_bonus_utc = self.ensure_utc(package.next_bonus_date)
            if current_utc < next_bonus_utc:
                time_remaining = next_bonus_utc - current_utc
                hours_remaining = time_remaining.total_seconds() / 3600
                raise BonusValidationError(f"Bonus cooldown active. {hours_remaining:.1f} hours remaining")
        
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
            # Convert current_time to naive for database if needed
            # (Assuming your database stores naive datetimes)
            naive_current = self.make_naive_if_needed(self.current_time)
            
            # Calculate next bonus time
            next_bonus_aware = self.current_time + timedelta(hours=self.BONUS_COOLDOWN_HOURS)
            naive_next = self.make_naive_if_needed(next_bonus_aware)
            
            # Update bonus tracking
            package.last_bonus_date = naive_current
            package.next_bonus_date = naive_next
            package.bonus_count += 1
            package.total_days_paid += 1
            
            # Update total bonus paid
            current_total = self.safe_decimal(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
            package.total_bonus_paid = current_total + daily_bonus
            
            # Check if package completed
            if package.total_bonus_paid >= package.max_bonus_amount:
                package.status = 'completed'
                logger.info(f"Package {package.id} completed - max payout reached")
            
            package.updated_at = naive_current
            
        except Exception as e:
            raise BonusValidationError(f"Failed to update package: {e}")
    
    def create_bonus_transaction(self, user_id: int, wallet_id: int, 
                               amount: Decimal, package_id: int) -> str:
        """Create audit trail for bonus payment"""
        try:
            # Convert current_time to naive for database
            naive_current = self.make_naive_if_needed(self.current_time)
            
            # Create bonus record
            bonus = Bonus(
                user_id=user_id,
                
                package_id=package_id,
                type="daily",
                amount=amount,
                status="paid",
                paid_at=naive_current,
                created_at=naive_current
            )
            db.session.add(bonus)
            
            # Create transaction
            transaction_ref = f"BONUS-{uuid.uuid4().hex[:12].upper()}"
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet_id,
                type="bonus_credit",
                amount=amount,
                status="completed",
                reference=transaction_ref,
                created_at=naive_current
            )
            db.session.add(transaction)
            
            return transaction_ref
            
        except Exception as e:
            raise BonusSecurityError(f"Failed to create bonus records: {e}")
    def get_pending_packages_with_time(self, packages: List[Package]) -> List[Tuple[Package, float]]:
        """Get packages with pending bonuses and their remaining hours"""
        pending_packages = []
        current_utc = self.current_time
        
        for package in packages:
            try:
                # Skip if package can't receive bonus
                if package.status != 'active' or package.is_bonus_locked:
                    continue
                
                # Check if max payout reached
                package_amount = self.safe_decimal(package.package_amount, "package_amount")
                max_payout = (package_amount * self.MAX_PAYOUT_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
                current_paid = self.safe_decimal(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
                
                if current_paid >= max_payout:
                    continue  # Package completed, no bonus available
                
                # Calculate time until next bonus
                if not package.last_bonus_date:
                    # First bonus - 24 hours after activation
                    activated_at_utc = self.ensure_utc(package.activated_at)
                    first_bonus_time = activated_at_utc + timedelta(hours=24)
                    if current_utc < first_bonus_time:
                        hours_left = (first_bonus_time - current_utc).total_seconds() / 3600
                        pending_packages.append((package, hours_left))
                else:
                    # Subsequent bonuses - check next_bonus_date
                    if package.next_bonus_date:
                        next_bonus_utc = self.ensure_utc(package.next_bonus_date)
                        if current_utc < next_bonus_utc:
                            hours_left = (next_bonus_utc - current_utc).total_seconds() / 3600
                            pending_packages.append((package, hours_left))
            except Exception as e:
                logger.warning(f"Error checking pending status for package {package.id}: {e}")
                continue    
        return pending_packages
    
    def create_pending_bonus_notifications(self, user_id: int, packages_with_remaining_time: List[Tuple[Package, float]]) -> None:
        """Create notifications for pending bonuses with time remaining"""
        try:
            from models import Notification  # Import here to avoid circular imports
            
            naive_current = self.make_naive_if_needed(self.current_time)
            
            if not packages_with_remaining_time:
                return
            
            # Sort by closest to ready
            packages_with_remaining_time.sort(key=lambda x: x[1])
            
            # Create detailed notification
            if len(packages_with_remaining_time) == 1:
                package, hours_left = packages_with_remaining_time[0]
                message = f"⏰ Bonus pending for {package.package}. {hours_left:.1f} hours remaining until next bonus is available."
            else:
                # Multiple packages - show closest one
                closest_package, closest_hours = packages_with_remaining_time[0]
                total_pending = len(packages_with_remaining_time)
                message = f"⏰ {total_pending} package(s) have pending bonuses. Next bonus for {closest_package.package} available in {closest_hours:.1f} hours."
            
            # Check if similar notification already exists in last 6 hours (to avoid spam)
            six_hours_ago = self.make_naive_if_needed(self.current_time - timedelta(hours=6))
            existing = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.notification_type == 'bonus_pending',
                Notification.created_at >= six_hours_ago
            ).first()
            
            if existing:
                return  # Skip to avoid spam
            
            notification = Notification(
                user_id=user_id,
                message=message,
                notification_type='bonus_pending',
                is_read=False,
                created_at=naive_current
            )
            db.session.add(notification)
            db.session.commit()
            logger.info(f"Pending bonus notification created for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to create pending bonus notification for user {user_id}: {e}")
    def get_user_wallet(self, user_id: int) -> Wallet:
        """Get or create user wallet with validation"""
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            # Convert current_time to naive for database
            naive_current = self.make_naive_if_needed(self.current_time)
            
            wallet = Wallet(
                user_id=user_id,
                balance=Decimal("0.00"),
                created_at=naive_current
            )
            db.session.add(wallet)
            db.session.flush()
        
        return wallet
    
    def process_single_package(self, package: Package, wallet: Wallet) -> Dict:
        """Process bonus for a single package with full validation"""
        package_result = {
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
            wallet.updated_at = self.make_naive_if_needed(self.current_time)
            
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
            logger.info(f"Bonus paid for package {package.id}: {daily_bonus}")
            
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
            # Validate user
            user = User.query.get(user_id)
            self.validate_user(user)
            
            # Get wallet
            wallet = self.get_user_wallet(user_id)
            initial_balance = self.safe_decimal(wallet.balance, "wallet_balance")
            
            # Get eligible packages with row locking
            packages = (
                Package.query
                .filter_by(user_id=user_id, status='active')
                .with_for_update()
                .all()
            )
            
            if not packages:
                response.update({
                    "success": True,
                    "wallet_balance": float(initial_balance),
                    "message": "No active packages found"
                })
                return response  # ✅ Added return
            
            # Process pending notifications (only once)
            try:
                pending_packages = self.get_pending_packages_with_time(packages)
                if pending_packages:
                    self.create_pending_bonus_notifications(user_id, pending_packages)
            except Exception as e:
                logger.warning(f"Failed to process pending notifications: {e}")
            
            total_bonus = Decimal("0.00")
            processed_packages = []
            
            # Process each package
            for package in packages:
                result = self.process_single_package(package, wallet)
                processed_packages.append(result)
                
                if result["success"]:
                    total_bonus += self.safe_decimal(result["bonus_amount"], "bonus_amount")
            
            # ✅ Define successful_packages BEFORE using it
            successful_packages = [p for p in processed_packages if p["success"]]
            failed_packages = [p for p in processed_packages if not p["success"]]
            
            # Commit only if we have successful processing
            if successful_packages:
                try:
                    if total_bonus > 0:
                        notification = Notification(
                            user_id=user_id,
                            message=f"🎉 You've earned ${float(total_bonus):.2f} in daily bonuses from {len(successful_packages)} active package(s)!",
                            notification_type='bonus',
                            is_read=False,
                            created_at=self.make_naive_if_needed(self.current_time)
                        )
                        db.session.add(notification)
                except Exception as e:
                    logger.warning(f"Failed to prepare notification: {e}")
                
                db_session.commit()
            else:
                db_session.rollback()
            
            # Prepare response
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
    # def process_user_bonus(self, user_id: int) -> Dict:
    #     """Main method to process daily bonus for a user"""
    #     response = {
    #         "success": False,
    #         "user_id": user_id,
    #         "total_bonus": 0.0,
    #         "wallet_balance": 0.0,
    #         "packages_processed": 0,
    #         "packages_successful": 0,
    #         "packages_failed": 0,
    #         "processed_packages": [],
    #         "timestamp": self.current_time.isoformat(),
    #         "error": None
    #     }
        
    #     db_session = db.session
        
    #     try:
    #         # Validate user
    #         user = User.query.get(user_id)
    #         self.validate_user(user)
            
    #         # Get wallet
    #         wallet = self.get_user_wallet(user_id)
    #         initial_balance = self.safe_decimal(wallet.balance, "wallet_balance")
            
    #         # Get eligible packages with row locking
    #         packages = (
    #             Package.query
    #             .filter_by(user_id=user_id, status='active')
    #             .with_for_update()
    #             .all()
    #         )
            
    #         if not packages:
    #             response.update({
    #                 "success": True,
    #                 "wallet_balance": float(initial_balance),
    #                 "message": "No active packages found"
    #             })
        
    #         try:
    #             pending_packages = self.get_pending_packages_with_time(packages)
    #             if pending_packages:
    #                 self.create_pending_bonus_notifications(user_id, pending_packages)
    #         except Exception as e:
    #             logger.warning(f"Failed to process pending notifications: {e}")
        
    #         if pending_packages:
    #             self.create_pending_bonus_notifications(user_id, pending_packages)
                
    #         total_bonus = Decimal("0.00")
    #         processed_packages = []
            
    #         # Process each package
    #         for package in packages:
    #             result = self.process_single_package(package, wallet)
    #             processed_packages.append(result)
                
    #             if result["success"]:
    #                 total_bonus += self.safe_decimal(result["bonus_amount"], "bonus_amount")
            
    #         # Commit only if we have successful processing
    #         if any(p["success"] for p in processed_packages):
                
    #             try:
    #                 if total_bonus > 0:
    #                     notification = Notification(
    #                         user_id=user_id,
    #                         message=f"🎉 You've earned ${float(total_bonus):.2f} in daily bonuses from {len(successful_packages)} active package(s)!",
    #                         notification_type='bonus',
    #                         is_read=False,
    #                         created_at=self.make_naive_if_needed(self.current_time)
    #                     )
    #                     db.session.add(notification)
    #             except Exception as e:
    #                 logger.warning(f"Failed to prepare notification: {e}")
    #             db_session.commit()
    #         else:
    #             db_session.rollback()
            
    #         # Prepare response
    #         successful_packages = [p for p in processed_packages if p["success"]]
    #         failed_packages = [p for p in processed_packages if not p["success"]]
            
    #         response.update({
    #             "success": True,
    #             "total_bonus": float(total_bonus),
    #             "wallet_balance": float(wallet.balance),
    #             "packages_processed": len(processed_packages),
    #             "packages_successful": len(successful_packages),
    #             "packages_failed": len(failed_packages),
    #             "processed_packages": processed_packages
    #         })
            
    #     except (BonusSecurityError, BonusValidationError) as e:
    #         db_session.rollback()
    #         response["error"] = str(e)
    #         logger.error(f"Bonus processing failed for user {user_id}: {e}")
            
    #     except SQLAlchemyError as e:
    #         db_session.rollback()
    #         response["error"] = f"Database error: {str(e)}"
    #         logger.error(f"Database error processing bonus for user {user_id}: {e}")
            
    #     except Exception as e:
    #         db_session.rollback()
    #         response["error"] = f"Unexpected error: {str(e)}"
    #         logger.error(f"Unexpected error processing bonus for user {user_id}: {e}", exc_info=True)
        
    #     return response 
   
def create_bonus_notification(self, user_id: int, total_bonus: Decimal, successful_count: int) -> None:
    """Create notification for bonus earnings"""
    try:
        naive_current = self.make_naive_if_needed(self.current_time)
        
        if successful_count > 0:
            message = f"🎉 You've earned ${float(total_bonus):.2f} in daily bonuses from {successful_count} active package(s)!"
        else:
            message = "📋 No bonuses were processed today. Check your active packages for bonus eligibility."
        
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type='bonus',
            is_read=False,
            created_at=naive_current
        )
        db.session.add(notification)
        db.session.commit()  # Commit notification separately or within main transaction
    except Exception as e:
        logger.warning(f"Failed to create notification for user {user_id}: {e}")

def create_pending_bonus_notifications(self, user_id: int, packages_with_remaining_time: List[Tuple[Package, float]]) -> None:
    """Create notifications for pending bonuses with time remaining"""
    try:
        naive_current = self.make_naive_if_needed(self.current_time)
        
        if not packages_with_remaining_time:
            return
        
        # Sort by closest to ready
        packages_with_remaining_time.sort(key=lambda x: x[1])
        
        # Create detailed notification
        if len(packages_with_remaining_time) == 1:
            package, hours_left = packages_with_remaining_time[0]
            message = f"⏰ Bonus pending for {package.package}. {hours_left:.1f} hours remaining until next bonus is available."
        else:
            # Multiple packages - show closest one
            closest_package, closest_hours = packages_with_remaining_time[0]
            total_pending = len(packages_with_remaining_time)
            message = f"⏰ {total_pending} package(s) have pending bonuses. Next bonus for {closest_package.package} available in {closest_hours:.1f} hours."
        
        # Check if similar notification already exists in last 6 hours (to avoid spam)
        six_hours_ago = self.make_naive_if_needed(self.current_time - timedelta(hours=6))
        existing = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.notification_type == 'bonus_pending',
            Notification.created_at >= six_hours_ago
        ).first()
        
        if existing:
            return  # Skip to avoid spam
        
        notification = Notification(
            user_id=user_id,
            message=message,
            notification_type='bonus_pending',
            is_read=False,
            created_at=naive_current
        )
        db.session.add(notification)
        db.session.commit()
        logger.info(f"Pending bonus notification created for user {user_id}")
        
    except Exception as e:
        logger.warning(f"Failed to create pending bonus notification for user {user_id}: {e}")

def get_pending_packages_with_time(self, packages: List[Package]) -> List[Tuple[Package, float]]:
    """Get packages with pending bonuses and their remaining hours"""
    pending_packages = []
    current_utc = self.current_time
    
    for package in packages:
        try:
            # Skip if package can't receive bonus
            if package.status != 'active' or package.is_bonus_locked:
                continue
            
            # Check if max payout reached
            package_amount = self.safe_decimal(package.package_amount, "package_amount")
            max_payout = (package_amount * self.MAX_PAYOUT_RATE).quantize(Decimal("0.01"), ROUND_HALF_UP)
            current_paid = self.safe_decimal(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
            
            if current_paid >= max_payout:
                continue  # Package completed, no bonus available
            
            # Calculate time until next bonus
            if not package.last_bonus_date:
                # First bonus - 24 hours after activation
                activated_at_utc = self.ensure_utc(package.activated_at)
                first_bonus_time = activated_at_utc + timedelta(hours=24)
                if current_utc < first_bonus_time:
                    hours_left = (first_bonus_time - current_utc).total_seconds() / 3600
                    pending_packages.append((package, hours_left))
            else:
                # Subsequent bonuses - check next_bonus_date
                if package.next_bonus_date:
                    next_bonus_utc = self.ensure_utc(package.next_bonus_date)
                    if current_utc < next_bonus_utc:
                        hours_left = (next_bonus_utc - current_utc).total_seconds() / 3600
                        pending_packages.append((package, hours_left))
        except Exception as e:
            logger.warning(f"Error checking pending status for package {package.id}: {e}")
            continue
    
    return pending_packages