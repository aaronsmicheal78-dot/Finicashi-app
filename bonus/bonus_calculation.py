from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text, and_
from models import User, Payment, PackageCatalog, ReferralBonus, ReferralNetwork
from bonus.refferral_tree import ReferralTreeHelper
from bonus.validation import BonusValidationHelper

class BonusCalculationHelper:
    """Production-grade secure bonus calculation with comprehensive validation"""
    
    # Security constants
    MAX_BONUS_AMOUNT = Decimal('10000000')  # 10M UGX maximum
    MIN_BONUS_AMOUNT = Decimal('1')         # 1 UGX minimum
    MAX_LEVEL = 20
    
    @staticmethod
    def calculate_level_bonus(amount: Decimal, level: int, package_id: int = None) -> Tuple[bool, Decimal, str]:
        """
        SECURE VERSION: Calculate bonus with comprehensive validation
        Returns: (success, bonus_amount, error_message)
        """
        try:
            # 1. Input validation
            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return False, Decimal('0'), "Invalid amount format"
            
            if amount <= Decimal('0'):
                return False, Decimal('0'), "Amount must be positive"
            
            if not isinstance(level, int) or not 1 <= level <= BonusCalculationHelper.MAX_LEVEL:
                return False, Decimal('0'), f"Level must be between 1 and {BonusCalculationHelper.MAX_LEVEL}"
            
            # 2. Get bonus percentage with validation
            bonus_percentage = BonusConfigHelper.get_bonus_percentage(level, package_id)
            if not isinstance(bonus_percentage, Decimal):
                try:
                    bonus_percentage = Decimal(str(bonus_percentage))
                except (InvalidOperation, ValueError):
                    return False, Decimal('0'), "Invalid bonus percentage"
            
            if bonus_percentage < Decimal('0') or bonus_percentage > Decimal('1'):
                return False, Decimal('0'), "Bonus percentage out of valid range (0-1)"
            
            # 3. Calculate raw bonus with overflow protection
            try:
                raw_bonus = amount * bonus_percentage
                
                # Check for unreasonable bonus amounts
                if raw_bonus > amount * Decimal('0.5'):  # Bonus > 50% of amount
                    current_app.logger.warning(
                        f"Suspicious bonus calculation: amount={amount}, "
                        f"level={level}, bonus={raw_bonus}, percentage={bonus_percentage}"
                    )
                
            except (OverflowError, InvalidOperation) as e:
                return False, Decimal('0'), f"Bonus calculation overflow: {str(e)}"
            
            # 4. Apply rounding with bounds checking
            try:
                bonus_amount = raw_bonus.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                
                # Enforce minimum and maximum limits
                if bonus_amount < BonusCalculationHelper.MIN_BONUS_AMOUNT:
                    return False, Decimal('0'), "Bonus amount below minimum"
                
                if bonus_amount > BonusCalculationHelper.MAX_BONUS_AMOUNT:
                    bonus_amount = BonusCalculationHelper.MAX_BONUS_AMOUNT
                    current_app.logger.warning(
                        f"Bonus capped at maximum: {bonus_amount} for level {level}"
                    )
                
            except (OverflowError, InvalidOperation) as e:
                return False, Decimal('0'), f"Bonus rounding error: {str(e)}"
            
            # 5. Final sanity check
            if bonus_amount <= Decimal('0'):
                return False, Decimal('0'), "Invalid bonus amount after calculation"
            
            current_app.logger.info(
                f"Bonus calculation: level={level}, amount={amount}, "
                f"percentage={bonus_percentage}, bonus={bonus_amount}"
            )
            
            return True, bonus_amount, "Success"
            
        except Exception as e:
            current_app.logger.error(f"Critical error in bonus calculation: {str(e)}")
            return False, Decimal('0'), f"Calculation error: {str(e)}"
    
    @staticmethod
    def batch_check_user_eligibility(user_ids: List[int]) -> Dict[int, Tuple[bool, str]]:
        """
        OPTIMIZED: Batch check user eligibility to avoid N+1 queries
        """
        try:
            if not user_ids:
                return {}
            
            # Single query to get all users with necessary fields
            users = User.query.filter(User.id.in_(user_ids)).all()
            
            eligibility_map = {}
            for user in users:
                is_eligible, reason = BonusCalculationHelper._check_single_user_eligibility(user)
                eligibility_map[user.id] = (is_eligible, reason)
            
            # Handle missing users
            for user_id in user_ids:
                if user_id not in eligibility_map:
                    eligibility_map[user_id] = (False, "User not found")
            
            return eligibility_map
            
        except Exception as e:
            current_app.logger.error(f"Batch eligibility check error: {str(e)}")
            return {user_id: (False, f"System error: {str(e)}") for user_id in user_ids}
    
    @staticmethod
    def _check_single_user_eligibility(user: User) -> Tuple[bool, str]:
        """
        COMPREHENSIVE: Individual user eligibility with security checks
        """
        try:
            # 1. Basic account status
            if not user.is_active:
                return False, "User account is inactive"
            
            if not user.is_verified:
                return False, "User is not verified"
            
            # 2. Bonus eligibility flag
            if not getattr(user, 'bonus_eligible', True):
                return False, "User not eligible for bonuses"
            
            # 3. KYC status (if profile exists)
            if hasattr(user, 'profile') and user.profile:
                if getattr(user.profile, 'kyc_status', 'pending') != 'approved':
                    return False, "KYC not approved"
            
            # 4. Fraud detection
            if getattr(user, 'flagged', False):
                return False, "User account is flagged for review"
            
            # 5. Account age requirement
            account_age = datetime.utcnow() - user.created_at
            if account_age < timedelta(hours=24):  # 24-hour minimum
                return False, "Account too new for bonuses"
            
            # 6. Geographic restrictions (if applicable)
            if hasattr(user, 'profile') and user.profile:
                country = getattr(user.profile, 'country', None)
                if country and country not in ['UG', 'KE', 'TZ']:  # Example restriction
                    return False, "User location not eligible for bonuses"
            
            # 7. Activity requirements
            if getattr(user, 'total_network_size', 0) == 0 and getattr(user, 'direct_referrals_count', 0) == 0:
                # New users without any network activity
                pass  # Could add specific rules here
            
            return True, "Eligible"
            
        except Exception as e:
            current_app.logger.error(f"User eligibility error for {user.id}: {str(e)}")
            return False, f"Eligibility check error: {str(e)}"
    
    @staticmethod
    def calculate_all_bonuses_secure(purchase: Payment) -> Tuple[bool, List[Dict[str, Any]], str, Dict[str, Any]]:
        """
        SECURE VERSION: Comprehensive bonus calculation with audit trail
        Returns: (success, bonuses, message, audit_info)
        """
        audit_info = {
            'purchase_id': purchase.id if purchase else None,
            'user_id': purchase.user_id if purchase else None,
            'start_time': datetime.utcnow().isoformat(),
            'total_ancestors': 0,
            'eligible_ancestors': 0,
            'bonuses_calculated': 0,
            'total_bonus_amount': Decimal('0'),
            'validation_errors': [],
            'calculation_errors': []
        }
        
        try:
            # 1. Pre-validation with comprehensive checks
            if not purchase:
                audit_info['validation_errors'].append('purchase_not_found')
                return False, [], "Purchase not found", audit_info
            
            # Validate purchase ownership and integrity
            is_purchase_valid, purchase_error, validation_details = BonusValidationHelper.validate_purchase_for_bonus(purchase.id)
            if not is_purchase_valid:
                audit_info['validation_errors'].append(purchase_error)
                return False, [], f"Purchase validation failed: {purchase_error}", audit_info
            
            # 2. Check if bonuses already calculated (idempotency)
            existing_bonuses = ReferralBonus.query.filter_by(payment_id=purchase.id).count()
            if existing_bonuses > 0:
                audit_info['validation_errors'].append(f'bonuses_already_exist: {existing_bonuses}')
                return False, [], f"Bonuses already calculated for this purchase", audit_info
            
            # 3. Get purchase details with validation
            user_id = purchase.user_id
            try:
                amount = Decimal(str(purchase.amount))
                if amount <= Decimal('0'):
                    audit_info['validation_errors'].append('invalid_purchase_amount')
                    return False, [], "Invalid purchase amount", audit_info
            except (InvalidOperation, ValueError) as e:
                audit_info['validation_errors'].append(f'amount_conversion_error: {str(e)}')
                return False, [], "Invalid purchase amount format", audit_info
            
            package_id = purchase.package_catalog_id
            
            # 4. Get ancestors with network validation
            ancestors = ReferralTreeHelper.get_ancestors(user_id, BonusCalculationHelper.MAX_LEVEL)
            audit_info['total_ancestors'] = len(ancestors)
            
            if not ancestors:
                audit_info['validation_errors'].append('no_ancestors_found')
                return True, [], "No eligible ancestors found", audit_info  # Not an error
            
            # 5. Batch eligibility check for performance
            ancestor_ids = [ancestor['user_id'] for ancestor in ancestors]
            eligibility_map = BonusCalculationHelper.batch_check_user_eligibility(ancestor_ids)
            
            bonuses = []
            
            # 6. Calculate bonuses for eligible ancestors
            for ancestor in ancestors:
                level = ancestor['level']
                ancestor_id = ancestor['user_id']
                
                # Check eligibility from batch results
                is_eligible, eligibility_reason = eligibility_map.get(ancestor_id, (False, "User not found in batch"))
                
                if not is_eligible:
                    audit_info['validation_errors'].append(f'user_{ancestor_id}_ineligible: {eligibility_reason}')
                    current_app.logger.debug(
                        f"Ancestor {ancestor_id} level {level} ineligible: {eligibility_reason}"
                    )
                    continue
                
                audit_info['eligible_ancestors'] += 1
                
                # Calculate bonus amount with security
                success, bonus_amount, calc_error = BonusCalculationHelper.calculate_level_bonus(
                    amount, level, package_id
                )
                
                if not success:
                    audit_info['calculation_errors'].append({
                        'ancestor_id': ancestor_id,
                        'level': level,
                        'error': calc_error
                    })
                    current_app.logger.warning(
                        f"Bonus calculation failed for ancestor {ancestor_id} level {level}: {calc_error}"
                    )
                    continue
                
                # Skip zero bonuses
                if bonus_amount <= Decimal('0'):
                    continue
                
                # 7. Create bonus data with comprehensive information
                bonus_data = {
                    'purchase_id': purchase.id,
                    'user_id': ancestor_id,
                    'referrer_id': ancestor_id,  # The recipient of the bonus
                    'referred_id': user_id,      # The user who made the purchase
                    'level': level,
                    'amount': bonus_amount,
                    'bonus_percentage': float(BonusConfigHelper.get_bonus_percentage(level, package_id)),
                    'qualifying_amount': float(amount),
                    'status': 'pending',
                    'calculated_at': datetime.utcnow(),
                    'network_depth': level,
                    'bonus_type': 'referral_level',
                    'currency': getattr(purchase, 'currency', 'UGX'),
                    'metadata': {
                        'purchase_user_id': user_id,
                        'purchase_amount': float(amount),
                        'package_id': package_id,
                        'calculation_timestamp': datetime.utcnow().isoformat(),
                        'ancestor_username': ancestor.get('username', 'Unknown')
                    }
                }
                
                bonuses.append(bonus_data)
                audit_info['bonuses_calculated'] += 1
                audit_info['total_bonus_amount'] += bonus_amount
                
                current_app.logger.info(
                    f"Calculated bonus: Level {level}, User {ancestor_id}, Amount {bonus_amount}"
                )
            
            # 8. Final validation and summary
            audit_info['end_time'] = datetime.utcnow().isoformat()
            calculation_time = datetime.fromisoformat(audit_info['end_time']) - datetime.fromisoformat(audit_info['start_time'])
            audit_info['calculation_duration_seconds'] = calculation_time.total_seconds()
            
            success = len(bonuses) > 0 or audit_info['total_ancestors'] == 0
            message = f"Calculated {len(bonuses)} bonuses from {audit_info['eligible_ancestors']} eligible ancestors"
            
            current_app.logger.info(
                f"Bonus calculation complete for purchase {purchase.id}: {message}. "
                f"Total amount: {audit_info['total_bonus_amount']}, "
                f"Duration: {audit_info['calculation_duration_seconds']:.2f}s"
            )
            
            return success, bonuses, message, audit_info
            
        except Exception as e:
            current_app.logger.error(f"Critical error in bonus calculation: {str(e)}")
            audit_info['end_time'] = datetime.utcnow().isoformat()
            audit_info['critical_error'] = str(e)
            return False, [], f"Calculation failed: {str(e)}", audit_info
    
    @staticmethod
    def normalize_bonus_amount(amount: Decimal) -> Tuple[bool, Decimal, str]:
        """
        SECURE VERSION: Normalize bonus amount with validation
        """
        try:
            if not isinstance(amount, Decimal):
                try:
                    amount = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return False, Decimal('0'), "Invalid amount format"
            
            if amount < Decimal('0'):
                return False, Decimal('0'), "Amount cannot be negative"
            
            # Round to 2 decimal places
            normalized = amount.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            
            # Remove trailing zeros but ensure it's still a monetary value
            normalized = normalized.normalize()
            
            # Ensure we still have 2 decimal places for monetary values
            if normalized.as_tuple().exponent < -2:
                normalized = normalized.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            
            return True, normalized, "Success"
            
        except (InvalidOperation, OverflowError) as e:
            return False, Decimal('0'), f"Normalization error: {str(e)}"
        except Exception as e:
            return False, Decimal('0'), f"Unexpected normalization error: {str(e)}"
    
    @staticmethod
    def get_purchase_bonus_summary_secure(purchase_id: int) -> Tuple[bool, Dict[str, Any], str]:
        """
        SECURE VERSION: Get bonus summary with validation
        """
        try:
            # Validate purchase exists
            purchase = Payment.query.get(purchase_id)
            if not purchase:
                return False, {}, "Purchase not found"
            
            # Get bonuses with proper error handling
            bonuses = ReferralBonus.query.filter_by(payment_id=purchase_id).all()
            
            total_bonus = Decimal('0')
            bonus_breakdown = {}
            
            for bonus in bonuses:
                try:
                    bonus_amount = Decimal(str(bonus.amount))
                    total_bonus += bonus_amount
                    
                    # Track by level
                    level = bonus.level
                    if level not in bonus_breakdown:
                        bonus_breakdown[level] = {
                            'count': 0,
                            'total_amount': Decimal('0'),
                            'users': []
                        }
                    
                    bonus_breakdown[level]['count'] += 1
                    bonus_breakdown[level]['total_amount'] += bonus_amount
                    bonus_breakdown[level]['users'].append({
                        'user_id': bonus.user_id,
                        'amount': float(bonus_amount),
                        'status': bonus.status
                    })
                    
                except (InvalidOperation, ValueError) as e:
                    current_app.logger.error(f"Invalid bonus amount for bonus {bonus.id}: {str(e)}")
                    continue
            
            # Convert breakdown to float for JSON serialization
            for level in bonus_breakdown:
                bonus_breakdown[level]['total_amount'] = float(bonus_breakdown[level]['total_amount'])
            
            status_counts = {
                'pending': sum(1 for b in bonuses if b.status == 'pending'),
                'paid': sum(1 for b in bonuses if b.status == 'paid'),
                'failed': sum(1 for b in bonuses if b.status == 'failed'),
                'cancelled': sum(1 for b in bonuses if b.status == 'cancelled')
            }
            
            summary = {
                'purchase_id': purchase_id,
                'total_bonuses': len(bonuses),
                'total_amount': float(total_bonus),
                'status_breakdown': status_counts,
                'level_breakdown': bonus_breakdown,
                'currency': getattr(purchase, 'currency', 'UGX'),
                'calculated_at': getattr(purchase, 'bonuses_calculated_at', None),
                'bonuses': [
                    {
                        'id': b.id,
                        'user_id': b.user_id,
                        'level': b.level,
                        'amount': float(Decimal(str(b.amount))),
                        'status': b.status,
                        'paid_at': b.paid_at.isoformat() if b.paid_at else None,
                        'created_at': b.created_at.isoformat() if b.created_at else None
                    }
                    for b in bonuses
                ]
            }
            
            return True, summary, "Success"
            
        except Exception as e:
            current_app.logger.error(f"Error getting bonus summary for purchase {purchase_id}: {str(e)}")
            return False, {}, f"Summary retrieval error: {str(e)}"
    
    @staticmethod
    def validate_bonus_calculation_integrity(purchase_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        SECURE VERSION: Validate that bonus calculations are mathematically correct
        """
        try:
            purchase = Payment.query.get(purchase_id)
            if not purchase:
                return False, "Purchase not found", {}
            
            bonuses = ReferralBonus.query.filter_by(payment_id=purchase_id).all()
            validation_result = {
                'purchase_amount': float(purchase.amount),
                'total_calculated_bonus': 0.0,
                'expected_total_bonus': 0.0,
                'level_verification': {},
                'discrepancies': []
            }
            
            # Recalculate expected bonuses for verification
            for bonus in bonuses:
                level = bonus.level
                package_id = purchase.package_catalog_id
                
                # Recalculate bonus for this level
                success, expected_amount, error = BonusCalculationHelper.calculate_level_bonus(
                    Decimal(str(purchase.amount)), level, package_id
                )
                
                if not success:
                    validation_result['discrepancies'].append({
                        'bonus_id': bonus.id,
                        'level': level,
                        'error': f"Recalculation failed: {error}"
                    })
                    continue
                
                actual_amount = Decimal(str(bonus.amount))
                validation_result['total_calculated_bonus'] += float(actual_amount)
                validation_result['expected_total_bonus'] += float(expected_amount)
                
                # Check for discrepancies
                if abs(actual_amount - expected_amount) > Decimal('0.01'):  # Allow 0.01 tolerance
                    validation_result['discrepancies'].append({
                        'bonus_id': bonus.id,
                        'level': level,
                        'expected': float(expected_amount),
                        'actual': float(actual_amount),
                        'difference': float(abs(actual_amount - expected_amount))
                    })
                
                # Track level verification
                if level not in validation_result['level_verification']:
                    validation_result['level_verification'][level] = {
                        'count': 0,
                        'total_actual': Decimal('0'),
                        'total_expected': Decimal('0')
                    }
                
                validation_result['level_verification'][level]['count'] += 1
                validation_result['level_verification'][level]['total_actual'] += actual_amount
                validation_result['level_verification'][level]['total_expected'] += expected_amount
            
            # Convert level verification to float
            for level in validation_result['level_verification']:
                validation_result['level_verification'][level]['total_actual'] = float(
                    validation_result['level_verification'][level]['total_actual']
                )
                validation_result['level_verification'][level]['total_expected'] = float(
                    validation_result['level_verification'][level]['total_expected']
                )
            
            is_valid = len(validation_result['discrepancies']) == 0
            message = "Validation passed" if is_valid else f"Found {len(validation_result['discrepancies'])} discrepancies"
            
            return is_valid, message, validation_result
            
        except Exception as e:
            current_app.logger.error(f"Bonus validation error for purchase {purchase_id}: {str(e)}")
            return False, f"Validation error: {str(e)}", {}