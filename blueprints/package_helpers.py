# package_helpers.py
from models import db, User, Package, PackageCatalog, Payment, PaymentStatus
from datetime import datetime, timedelta, timezone
import json


class PackagePurchaseValidator:
    @staticmethod
    def validate_package_purchase(user_id, package_id):
        """
        Validate if user can purchase package with actual balance
        """
        user = User.query.get(user_id)
        package = PackageCatalog.query.get(package_id)
        
        if not user:
            return False, "User not found"
        
        if not package:
            return False, "Package not found"
        
        # Check if user has sufficient actual balance
        if user.actual_balance < package.amount:
            return False, f"Insufficient actual balance. Required: {package.amount}, Available: {user.actual_balance}"
        
        return True, "Validation passed"
    
    @staticmethod
    def process_package_purchase(user_id, package_id, phone=None):
        """
        Process package purchase using only actual balance
        """
        try:
            user = User.query.get(user_id)
            package = PackageCatalog.query.get(package_id)
            
            # Validate purchase
            is_valid, message = PackagePurchaseValidator.validate_package_purchase(user_id, package_id)
            if not is_valid:
                return False, message
            
            # Deduct from actual balance
            user.actual_balance -= package.amount
            
            # Create payment record
            payment = Payment(
                user_id=user.id,
                amount=package.amount,
                phone=phone,
                payment_type="package",
                status=PaymentStatus.COMPLETED.value,
                reference=f"PKG_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{user.id}",
                raw_response=json.dumps({
                    "method": "internal_balance",
                    "balance_type": "actual_balance",
                    "package_id": package_id,
                    "package_name": package.name
                }),
                balance_type_used="actual_balance"
            )
            
            db.session.add(payment)
            
            # Create user package
            new_package = Package(
                user_id=user.id,
                catalog_id=package.id,
                package=package.name,
                type="purchased",
                status='active',
                activated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=package.duration_days)
            )
            
            db.session.add(new_package)
            db.session.commit()
            
            return True, {
                "payment_reference": payment.reference,
                "package_activated": package.name,
                "new_actual_balance": user.actual_balance,
                "available_balance": user.available_balance,
                "expires_at": new_package.expires_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            return False, f"Package purchase failed: {str(e)}"