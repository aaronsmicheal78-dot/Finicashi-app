# bonus/bonus_calculation.py
from decimal import Decimal
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timezone
from flask import current_app
from sqlalchemy import text
import hashlib
import json

from models import Payment, User, ReferralBonus
from bonus.config import BonusConfigHelper

class BonusCalculationHelper:
    """
    Secure bonus calculation helper - now supports up to level 20
    """
    
    @staticmethod
    def calculate_all_bonuses_secure(payment: Payment) -> Tuple[bool, List[Dict], str, Dict[str, Any]]:
        """
        Calculate bonuses for all levels up to 20 with comprehensive security
        """
        try:
            print(f"🔍 DEBUG - Payment details:")
            print(f"  ID: {payment.id}")
            print(f"  Amount: {payment.amount}")
            print(f"  User ID: {payment.user_id}")
            current_app.logger.info(f"Starting secure bonus calculation for payment {payment.id}")
            
            # Security audit info
            audit_info = {
                'calculation_start': datetime.now(timezone.utc),
                'payment_amount': float(payment.amount),
                'payment_user_id': payment.user_id,
                'levels_processed': 0,
                'total_bonus_calculated': Decimal('0'),
                'security_checks': []
            }
            
            bonuses = []
            total_bonus_amount = Decimal('0')
            
            # Get the user who made the payment
            paying_user = User.query.get(payment.user_id)
            if not paying_user:
                return False, [], "Paying user not found", audit_info
            
            # DEBUG: Log the referral chain
            current_app.logger.info(f"🔍 Payment user ID: {paying_user.id}, referred_by: {paying_user.referred_by}")
            
            # Calculate bonuses for each level (1 to 20)
            for level in range(1, BonusConfigHelper.MAX_LEVEL + 1):
                level_bonuses = BonusCalculationHelper._calculate_bonuses_for_level(
                    paying_user, payment, level, audit_info
                )
                bonuses.extend(level_bonuses)
                
                # Sum bonuses for this level
                for bonus in level_bonuses:
                    total_bonus_amount += Decimal(str(bonus.get('amount', 0)))
            
            audit_info['calculation_end'] = datetime.now(timezone.utc)
            audit_info['levels_processed'] = len(set(bonus.get('level', 0) for bonus in bonuses))
            audit_info['total_bonus_calculated'] = float(total_bonus_amount)
            audit_info['bonuses_count'] = len(bonuses)
            
            current_app.logger.info(
                f"Bonus calculation completed: {len(bonuses)} bonuses across "
                f"{audit_info['levels_processed']} levels, total: {total_bonus_amount}"
            )
            
            return True, bonuses, f"Calculated {len(bonuses)} bonuses", audit_info
            
        except Exception as e:
            current_app.logger.error(f"Bonus calculation error: {str(e)}")
            audit_info['error'] = str(e)
            audit_info['calculation_end'] = datetime.now(timezone.utc)
            return False, [], f"Calculation failed: {str(e)}", audit_info
        
    @staticmethod
    def _calculate_bonuses_for_level(user: User, payment: Payment, level: int, audit_info: Dict) -> List[Dict]:
        """
        Calculate bonuses for a specific level safely.
        """
        bonuses = []

        try:
            # Get all users at this referral level
            users_at_level = BonusCalculationHelper._get_users_at_referral_level(user, level)
            current_app.logger.info(f"🔍 Level {level}: Found {len(users_at_level)} users")

            for target_user in users_at_level:
                try:
                    bonus_data = BonusCalculationHelper._calculate_single_bonus(
                        target_user, payment, level, user.id
                    )
                    if bonus_data:
                        # Ensure 'amount' key exists for logging
                        bonus_amount = bonus_data.get('amount') or bonus_data.get('bonus_amount')
                        bonuses.append(bonus_data)
                        current_app.logger.info(
                            f"💰 Level {level} bonus: User {target_user.id} - {bonus_amount:.2f} UGX"
                        )
                    else:
                        current_app.logger.info(f"User {target_user.id} did not receive a bonus")
                except Exception as inner_e:
                    current_app.logger.error(
                        f"Error calculating single bonus for User {target_user.id}: {inner_e}"
                    )
                    audit_info['security_checks'].append(
                        f'level_{level}_user_{target_user.id}_error:{inner_e}'
                    )

            audit_info['security_checks'].append(f'level_{level}_processed:{len(users_at_level)}_users')

        except Exception as e:
            current_app.logger.error(f"Error calculating bonuses for level {level}: {str(e)}")
            audit_info['security_checks'].append(f'level_{level}_error:{str(e)}')

        return bonuses

    
    # @staticmethod
    # def _calculate_bonuses_for_level(user: User, payment: Payment, level: int, audit_info: Dict) -> List[Dict]:
    #     """
    #     Calculate bonuses for a specific level
    #     """
    #     bonuses = []
        
    #     try:
    #         # Get all users at this referral level
    #         users_at_level = BonusCalculationHelper._get_users_at_referral_level(user, level)
            
    #         current_app.logger.info(f"🔍 Level {level}: Found {len(users_at_level)} users")
            
    #         for target_user in users_at_level:
    #             bonus_data = BonusCalculationHelper._calculate_single_bonus(
    #                 target_user, payment, level, user.id
    #             )
    #             if bonus_data:
    #                 bonuses.append(bonus_data)
    #                 current_app.logger.info(f"💰 Level {level} bonus: User {target_user.id} - {bonus_data['amount']} UGX")
            
    #         audit_info['security_checks'].append(f'level_{level}_processed:{len(users_at_level)}_users')
            
    #     except Exception as e:
    #         current_app.logger.error(f"Error calculating bonuses for level {level}: {str(e)}")
    #         audit_info['security_checks'].append(f'level_{level}_error:{str(e)}')
        
    #     return bonuses
    # In your bonus_calculation.py, update the _get_users_at_referral_level method:

    
    @staticmethod
    def _get_users_at_referral_level(start_user: User, target_level: int) -> List[User]:
        """
        FIXED VERSION: Correctly traverse up the referral chain
        """
        try:
            if target_level == 1:
                # Direct referrer
                if start_user.referred_by:
                    referrer = User.query.get(start_user.referred_by)
                    current_app.logger.info(f"🔍 Level 1: User {start_user.id} -> Referrer {referrer.id if referrer else 'None'}")
                    return [referrer] if referrer else []
                return []
            
            # For levels 2+, start from the direct referrer and traverse up
            current_user_id = start_user.referred_by
            if not current_user_id:
                return []
            
            # Traverse up the chain (target_level - 1) more times from the direct referrer
            for step in range(1, target_level):  # We already have level 1, so start from step 1
                current_user = User.query.get(current_user_id)
                if not current_user or not current_user.referred_by:
                    return []  # Chain ended
                
                current_user_id = current_user.referred_by  # Move up the chain
                current_app.logger.info(f"🔍 Level {target_level}, Step {step}: User {current_user.id} -> Referrer {current_user_id}")
            
            # Get the final user at the target level
            final_user = User.query.get(current_user_id)
            return [final_user] if final_user else []
            
        except Exception as e:
            current_app.logger.error(f"Error getting users at level {target_level}: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_single_bonus(target_user: User, payment: Payment, level: int, original_payer_id: int) -> Optional[Dict]:
        """
        Calculate a single bonus for a target user with validation-ready fields.
        """
        try:
            # Validate target user exists and is eligible
            if not target_user or not target_user.id:
                return None
                
            if not getattr(target_user, 'referral_bonus_eligible', True):
                current_app.logger.info(f"User {target_user.id} not eligible for bonuses")
                return None

            # Get bonus percentage for this level
            bonus_percentage = BonusConfigHelper.get_bonus_percentage(level)

            # Calculate bonus amount
            payment_amount = Decimal(str(payment.amount))
            bonus_amount = payment_amount * bonus_percentage

            # Skip if bonus is too small (less than 1 UGX)
            if bonus_amount < Decimal('1'):
                current_app.logger.info(f"Bonus too small: {bonus_amount} for level {level}")
                return None

            # Ensure bonus amount is reasonable
            if bonus_amount > payment_amount:
                current_app.logger.warning(
                    f"Bonus amount {bonus_amount} exceeds payment amount {payment_amount}"
                )
                return None

            # Get referrer ID
            referrer_id = getattr(target_user, 'referred_by', None)

            # Build bonus data dict aligned with validation and DB model
            bonus_data = {
                'user_id': target_user.id,                    # FK → recipient
                'ancestor_id': target_user.id,               # For network / validation
                'referrer_id': referrer_id,                 # FK → referrer
                'referred_id': original_payer_id,           # FK → original payer
                'payment_id': payment.id,                    # FK → payment
               'purchase_id': (payment.id),
                'level': level,                              # 1-20
                'bonus_amount': float(bonus_amount),        # Validation expects this key
                'amount': float(bonus_amount),              # For logging / legacy code
                'bonus_percentage': float(bonus_percentage),
                'qualifying_amount': float(payment_amount),
                'calculated_on': datetime.now(timezone.utc).isoformat(),
            }

            current_app.logger.info(
                f"💰 Calculated bonus: Level {level}, User {target_user.id}, Amount: {bonus_amount:.2f} UGX"
            )

            return bonus_data

        except Exception as e:
            current_app.logger.error(
                f"Error calculating single bonus for user "
                f"{target_user.id if target_user else 'unknown'}: {str(e)}"
            )
            return None

        
    # @staticmethod
    # def _calculate_single_bonus(target_user: User, payment: Payment, level: int, original_payer_id: int) -> Optional[Dict]:
    #     """
    #     Calculate a single bonus for a target user with validation
    #     """
    #     try:
    #         # Validate target user exists and is eligible
    #         if not target_user or not target_user.id:
    #             return None
                
    #         if not getattr(target_user, 'referral_bonus_eligible', True):
    #             current_app.logger.info(f"User {target_user.id} not eligible for bonuses")
    #             return None

    #         # Get bonus percentage for this level
    #         bonus_percentage = BonusConfigHelper.get_bonus_percentage(level)

    #         # Calculate bonus amount
    #         payment_amount = Decimal(str(payment.amount))
    #         bonus_amount = payment_amount * bonus_percentage

    #         # Skip if bonus is too small (less than 1 UGX)
    #         if bonus_amount < Decimal('1'):
    #             current_app.logger.info(f"Bonus too small: {bonus_amount} for level {level}")
    #             return None

    #         # Ensure bonus amount is reasonable
    #         if bonus_amount > payment_amount:
    #             current_app.logger.warning(
    #                 f"Bonus amount {bonus_amount} exceeds payment amount {payment_amount}"
    #             )
    #             return None

    #         # Get referrer ID
    #         referrer_id = getattr(target_user, 'referred_by', None)

    #         # Create bonus record in format used by other parts of system
    #         bonus_data = {
    #             'user_id': target_user.id,
    #             'referrer_id': referrer_id,
    #             'referred_id': original_payer_id,
    #             'payment_id': payment.id,
    #             'level': level,
    #             'amount': float(bonus_amount),              # <-- REQUIRED
    #             'bonus_percentage': float(bonus_percentage),
    #             'qualifying_amount': float(payment_amount),
    #             'calculated_at': datetime.now(timezone.utc).isoformat(),
    #         }

    #         current_app.logger.info(
    #             f"💰 Calculated bonus: Level {level}, User {target_user.id}, Amount: {bonus_amount:.2f} UGX"
    #         )

    #         return bonus_data

    #     except Exception as e:
    #         current_app.logger.error(
    #             f"Error calculating single bonus for user "
    #             f"{target_user.id if target_user else 'unknown'}: {str(e)}"
    #         )
    #         return None

    # @staticmethod
    # def _calculate_single_bonus(target_user: User, payment: Payment, level: int, original_payer_id: int) -> Optional[Dict]:
    #     """
    #     Calculate a single bonus for a target user with validation
    #     """
    #     try:
    #         # Validate target user exists and is eligible
    #         if not target_user or not target_user.id:
    #             return None
                
    #         if not getattr(target_user, 'referral_bonus_eligible', True):
    #             current_app.logger.info(f"User {target_user.id} not eligible for bonuses")
    #             return None

    #         # Get bonus percentage for this level
    #         bonus_percentage = BonusConfigHelper.get_bonus_percentage(level)
            
    #         # Calculate bonus amount
    #         payment_amount = Decimal(str(payment.amount))
    #         bonus_amount = payment_amount * bonus_percentage
            
    #         # Skip if bonus is too small (less than 1 UGX)
    #         if bonus_amount < Decimal('1'):
    #             current_app.logger.info(f"Bonus too small: {bonus_amount} for level {level}")
    #             return None
            
    #         # Ensure bonus amount is reasonable
    #         if bonus_amount > payment_amount:
    #             current_app.logger.warning(f"Bonus amount {bonus_amount} exceeds payment amount {payment_amount}")
    #             return None
            
    #         # Get referrer ID
    #         referrer_id = getattr(target_user, 'referred_by', None)
            
    #         # Create bonus record with validated data
    #         bonus_data = {
    #                                        # ✅ Matches validation
    #                     'ancestor_id': target_user.id,                # ✅ CHANGED from 'user_id'
    #                     'level': level,                               # ✅ Matches validation  
    #                     'bonus_amount': float(bonus_amount), 
    #                     'payment.id': payment.id    
    #                           }     # ✅ CHANGED from 'amount'   
    #                  #   'user_id': target_user.id,  # Must be integer
    #                    # 'referrer_id': referrer_id,  # Can be None
    #                    # 'referred_id': original_payer_id,  # Must be integer
    #                  #   'amount': float(bonus_amount),  # Convert to float for JSON serialization
    #                  #   'level': level,  # Must be integer 1-20
    #                  #   'bonus_percentage': float(bonus_percentage),
    #                   #  'qualifying_amount': float(payment_amount),
    #                      # Must be integer
    #                  #   'calculated_at': datetime.now(timezone.utc).isoformat(),
    #                 #    'security_hash': BonusCalculationHelper._calculate_bonus_hash(
    #                # target_user.id, payment.id, bonus_amount, level
    #            # )
           
            
    #         current_app.logger.info(f"💰 Calculated bonus: Level {level}, User {target_user.id}, Amount: {bonus_amount:.2f} UGX")
            
    #         return bonus_data
            
    #     except Exception as e:
    #         current_app.logger.error(f"Error calculating single bonus for user {target_user.id if target_user else 'unknown'}: {str(e)}")
    #         return None
   
    @staticmethod
    def _calculate_bonus_hash(user_id: int, payment_id: int, amount: Decimal, level: int) -> str:
        """Calculate security hash for bonus integrity"""
        data_str = f"{user_id}_{payment_id}_{amount}_{level}"
        secret = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        return hashlib.sha256(f"{data_str}{secret}".encode()).hexdigest()
    
    @staticmethod
    def calculate_referral_bonuses_with_practical_validation(payment_id: int) -> bool:
        """
        Calculate bonuses using practical validation
        """
        try:
            from bonus.bonus_payment import BonusPaymentProcessor
            from extensions import db
            payment = Payment.query.get(payment_id)
            if not payment:
                return False
            
            start_user = User.query.get(payment.user_id)
            total_bonuses = 0
            
            for level in range(1, 21):  # 20 levels
                users = BonusCalculationHelper._get_users_at_referral_level(start_user, level)
                
                for user in users:
                    # Use practical validation
                    is_eligible, message = BonusCalculationHelper.validate_user_eligibility(
                        user.id, level, payment.user_id
                    )
                    
                    if is_eligible:
                        bonus_amount = BonusCalculationHelper.calculate_bonus_amount(level, payment.amount)
                        
                        # Create bonus
                        bonus = ReferralBonus(
                            user_id=user.id,
                            payment_id=payment_id,
                            amount=bonus_amount,
                            level=level,
                            status='pending',
                         
    #                  

                        )
                        db.session.add(bonus)
                        total_bonuses += bonus_amount
                        
                        current_app.logger.info(f"💰 Level {level}: User {user.id} - UGX {bonus_amount}")
                    else:
                        current_app.logger.info(f"⏭️ Level {level}: User {user.id} - {message}")
            
            db.session.commit()
            
            # Use the new BonusPaymentProcessor instead of BonusPaymentHelper
            payment_success, payment_message, stats = BonusPaymentProcessor.process_payment_bonuses(payment_id)
            
            current_app.logger.info(f"🎊 Bonus calculation complete: {total_bonuses} calculated, payment: {payment_success}")
            return payment_success
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Bonus calculation error: {str(e)}")
            return False

