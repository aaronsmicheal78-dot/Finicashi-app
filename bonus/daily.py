# bonus/daily_bonus_processor.py
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.exc import SQLAlchemyError
import uuid
import logging

from extensions import db
from models import User, Wallet, Package, Bonus, Transaction

logger = logging.getLogger(__name__)

class BonusProcessingError(Exception):
    """Custom exception for bonus processing errors"""
    pass

class DecimalConversionError(BonusProcessingError):
    """Raised when decimal conversion fails"""
    pass

class PackageValidationError(BonusProcessingError):
    """Raised when package validation fails"""
    pass

def safe_decimal_convert(value, field_name: str = "value") -> Decimal:
    """
    Safely convert a value to Decimal with proper error handling
    
    Args:
        value: Value to convert to Decimal
        field_name: Name of the field for error reporting
    
    Returns:
        Decimal value
    
    Raises:
        DecimalConversionError: If conversion fails
    """
    if value is None:
        raise DecimalConversionError(f"{field_name} cannot be None")
    
    try:
        if isinstance(value, (int, float, str)):
            return Decimal(str(value)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        elif isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"), ROUND_HALF_UP)
        else:
            raise DecimalConversionError(f"Unsupported type for {field_name}: {type(value)}")
    except (InvalidOperation, ValueError, TypeError) as e:
        raise DecimalConversionError(f"Failed to convert {field_name} '{value}' to Decimal: {e}")

def validate_package_for_bonus(package: Package, current_time: datetime) -> Tuple[bool, Optional[str]]:
    """
    Validate if a package is eligible for bonus calculation
    
    Returns:
        Tuple of (is_valid, reason_if_invalid)
    """
    try:
        # Check package amount
        if not package.package_amount:
            return False, "Package amount is missing"
        
        package_amount = safe_decimal_convert(package.package_amount, "package_amount")
        if package_amount <= Decimal("0"):
            return False, "Package amount must be positive"
        
        # Check activation date
        activation_date = package.activated_at or package.created_at
        if not activation_date:
            return False, "Missing activation date"
        
        # Check expiry
        expiry_date = activation_date + timedelta(days=60)
        if current_time > expiry_date:
            return False, "Package expired"
        
        # Check status
        if package.status != 'active':
            return False, f"Package status is '{package.status}', not 'active'"
        
        return True, None
        
    except (DecimalConversionError, Exception) as e:
        return False, f"Package validation error: {e}"

def calculate_daily_bonus(package: Package) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculate daily bonus for a package
    
    Returns:
        Tuple of (daily_bonus, max_payout, remaining_limit)
    """
    try:
        package_amount = safe_decimal_convert(package.package_amount, "package_amount")
        current_total_paid = safe_decimal_convert(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
        
        # Daily bonus rate: 2.5%
        daily_bonus_rate = Decimal("0.05")
        daily_bonus = (package_amount * daily_bonus_rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        # Maximum payout: 75% of package amount
        max_payout = (package_amount * Decimal("0.75")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        remaining_limit = max_payout - current_total_paid
        
        return daily_bonus, max_payout, remaining_limit
        
    except DecimalConversionError as e:
        logger.error(f"Decimal conversion error for package {package.id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calculating bonus for package {package.id}: {e}")
        raise BonusProcessingError(f"Bonus calculation failed: {e}")

def update_package_status(package: Package, daily_bonus: Decimal, remaining_limit: Decimal) -> str:
    """
    Update package status based on bonus payout
    
    Returns:
        New package status
    """
    try:
        if remaining_limit <= Decimal("0"):
            package.status = "completed"
            return "completed"
        
        # Update total bonus paid
        current_total_paid = safe_decimal_convert(package.total_bonus_paid or Decimal("0"), "total_bonus_paid")
        package.total_bonus_paid = current_total_paid + daily_bonus
        
        # Check if package reached max payout after this bonus
        package_amount = safe_decimal_convert(package.package_amount, "package_amount")
        max_payout = (package_amount * Decimal("0.75")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        
        if package.total_bonus_paid >= max_payout:
            package.status = "completed"
            return "completed"
        
        return "active"
        
    except DecimalConversionError as e:
        logger.error(f"Decimal error updating package {package.id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error updating package status {package.id}: {e}")
        raise BonusProcessingError(f"Package status update failed: {e}")

def create_bonus_records(user_id: int, total_bonus: Decimal, wallet_id: int, 
                        now: datetime, db_session) -> str:
    """
    Create bonus and transaction records
    
    Returns:
        Transaction reference
    """
    try:
        # Create bonus record
        bonus_record = Bonus(
            user_id=user_id,
            type="daily",
            amount=total_bonus,
            status="active",
            created_at=now
        )
        db_session.add(bonus_record)
        
        # Create transaction
        transaction_ref = f"BONUS-{uuid.uuid4().hex[:10].upper()}"
        transaction = Transaction(
            wallet_id=wallet_id,
            type="bonus",
            amount=total_bonus,
            status="successful",
            reference=transaction_ref,
            created_at=now
        )
        db_session.add(transaction)
        
        return transaction_ref
        
    except Exception as e:
        logger.error(f"Error creating bonus records for user {user_id}: {e}")
        raise BonusProcessingError(f"Failed to create bonus records: {e}")

def get_or_create_wallet(user_id: int, db_session) -> Wallet:
    """Get existing wallet or create a new one"""
    try:
        wallet = Wallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = Wallet(
                user_id=user_id, 
                balance=Decimal("0.00"),
                created_at=datetime.utcnow()
            )
            db_session.add(wallet)
            # Flush to get wallet ID but don't commit yet
            db_session.flush()
        return wallet
    except SQLAlchemyError as e:
        logger.error(f"Database error getting/creating wallet for user {user_id}: {e}")
        raise BonusProcessingError(f"Wallet operation failed: {e}")

def process_user_daily_bonus(user_id: int) -> dict:
    """
    Calculate and credit daily bonuses for a user with enhanced error handling.
    
    Returns:
        dict: Processing summary with total_bonus_today and updated wallet balance
    """
    db_session = db.session
    now = datetime.utcnow()
    
    response_data = {
        "success": False,
        "total_bonus_today": 0.0,
        "wallet_balance": 0.0,
        "packages_processed": 0,
        "packages_expired": 0,
        "packages_completed": 0,
        "packages_skipped": 0,
        "processed_packages": [],
        "error": None
    }

    try:
        # Validate user
        user = User.query.get(user_id)
        if not user:
            response_data["error"] = f"User {user_id} not found"
            return response_data
            
        if not user.is_active:
            response_data["error"] = f"User {user_id} is not active"
            return response_data

        # Get or create wallet
        wallet = get_or_create_wallet(user_id, db_session)
        original_balance = safe_decimal_convert(wallet.balance, "wallet_balance")

        # Fetch active packages
        packages = Package.query.filter_by(user_id=user_id, status='active').all()
        if not packages:
            response_data.update({
                "success": True,
                "wallet_balance": float(original_balance)
            })
            return response_data

        total_bonus_today = Decimal("0.00")
        packages_updated = []
        expired_packages = []
        completed_packages = []
        skipped_packages = []

        for package in packages:
            try:
                # Validate package
                is_valid, reason = validate_package_for_bonus(package, now)
                if not is_valid:
                    if "expired" in reason.lower():
                        package.status = "expired"
                        expired_packages.append(package.id)
                    else:
                        skipped_packages.append({
                            "package_id": package.id,
                            "reason": reason
                        })
                    db_session.add(package)
                    continue

                # Calculate bonus
                daily_bonus, max_payout, remaining_limit = calculate_daily_bonus(package)
                
                # Apply remaining limit constraint
                if remaining_limit <= Decimal("0"):
                    package.status = "completed"
                    completed_packages.append(package.id)
                    db_session.add(package)
                    continue
                    
                if daily_bonus > remaining_limit:
                    daily_bonus = remaining_limit

                if daily_bonus <= Decimal("0"):
                    skipped_packages.append({
                        "package_id": package.id,
                        "reason": "Daily bonus is zero or negative"
                    })
                    continue

                # Update package
                old_status = package.status
                new_status = update_package_status(package, daily_bonus, remaining_limit - daily_bonus)
                
                if new_status == "completed":
                    completed_packages.append(package.id)
                
                packages_updated.append({
                    "package_id": package.id,
                    "package_name": package.package,
                    "bonus_today": float(daily_bonus),
                    "total_paid": float(package.total_bonus_paid),
                    "remaining_limit": float(remaining_limit - daily_bonus),
                    "previous_status": old_status,
                    "new_status": new_status
                })
                
                db_session.add(package)
                total_bonus_today += daily_bonus

            except (DecimalConversionError, PackageValidationError, BonusProcessingError) as e:
                logger.warning(f"Skipping package {package.id} due to error: {e}")
                skipped_packages.append({
                    "package_id": package.id,
                    "reason": f"Processing error: {str(e)}"
                })
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing package {package.id}: {e}")
                skipped_packages.append({
                    "package_id": package.id,
                    "reason": f"Unexpected error: {str(e)}"
                })
                continue

        # Commit if there's any bonus to award
        if total_bonus_today > Decimal("0"):
            try:
                # Update wallet
                wallet.balance = original_balance + total_bonus_today
                wallet.updated_at = now
                db_session.add(wallet)
                
                # Create bonus and transaction records
                transaction_ref = create_bonus_records(user_id, total_bonus_today, wallet.id, now, db_session)
                
                # Commit all changes
                db_session.commit()
                
                logger.info(f"Successfully processed daily bonus for user {user_id}: "
                           f"${total_bonus_today} credited, transaction: {transaction_ref}")
                           
            except Exception as e:
                db_session.rollback()
                logger.error(f"Failed to commit bonus transaction for user {user_id}: {e}")
                raise BonusProcessingError(f"Transaction commit failed: {e}")
        else:
            # Commit package status changes even if no bonus awarded
            if expired_packages or completed_packages or skipped_packages:
                try:
                    db_session.commit()
                    logger.info(f"Updated package statuses for user {user_id}: "
                               f"{len(expired_packages)} expired, {len(completed_packages)} completed")
                except Exception as e:
                    db_session.rollback()
                    logger.error(f"Failed to commit package status changes for user {user_id}: {e}")

        response_data.update({
            "success": True,
            "total_bonus_today": float(total_bonus_today),
            "wallet_balance": float(wallet.balance),
            "packages_processed": len(packages_updated),
            "packages_expired": len(expired_packages),
            "packages_completed": len(completed_packages),
            "packages_skipped": len(skipped_packages),
            "processed_packages": packages_updated,
            "skipped_packages": skipped_packages
        })

        return response_data

    except BonusProcessingError as e:
        db_session.rollback()
        logger.error(f"Bonus processing error for user {user_id}: {e}")
        response_data["error"] = str(e)
        return response_data
        
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.error(f"Database error during bonus processing for user {user_id}: {e}")
        response_data["error"] = f"Database error: {str(e)}"
        return response_data
        
    except Exception as e:
        db_session.rollback()
        logger.error(f"Unexpected error processing daily bonus for user {user_id}: {e}", exc_info=True)
        response_data["error"] = f"Unexpected error: {str(e)}"
        return response_data