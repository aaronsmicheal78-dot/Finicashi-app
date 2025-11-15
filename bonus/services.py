from app import db
from models import Payment, Bonus, BonusStatus
from bonus.bonus_calculation import calculate_all_bonuses
from bonus.validation import validate_bonus_entry
from bonus.bonus_payment import process_pending_bonuses
import logging

logger = logging.getLogger(__name__)

class BonusService:
    """
    Main service for handling bonus operations
    Simple interface for application logic
    """
    
    @staticmethod
    def process_purchase_bonuses(purchase_id: int) -> Dict:
        """
        Main method to process bonuses for a completed purchase
        Call this from your payment webhook or purchase completion logic
        """
        try:
            purchase = Payment.query.get(purchase_id)
            if not purchase:
                return {'success': False, 'error': 'Purchase not found'}
            
            if purchase.status != 'completed':
                return {'success': False, 'error': 'Purchase not completed'}
            
            # Step 1: Calculate all bonuses
            bonuses_data = calculate_all_bonuses(purchase)
            created_bonuses = []
            
            # Step 2: Create bonus records
            for bonus_data in bonuses_data:
                try:
                    if validate_bonus_entry(bonus_data):
                        bonus = Bonus(**bonus_data)
                        db.session.add(bonus)
                        created_bonuses.append(bonus_data)
                except Exception as e:
                    logger.warning(f"Failed to create bonus: {bonus_data}, error: {e}")
                    continue
            
            db.session.commit()
            
            # Step 3: Process pending bonuses (optional - could be separate job)
            payment_results = process_pending_bonuses(purchase_id)
            
            return {
                'success': True,
                'purchase_id': purchase_id,
                'bonuses_created': len(created_bonuses),
                'bonuses_paid': payment_results['approved'],
                'details': created_bonuses
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing purchase bonuses {purchase_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_user_bonus_summary(user_id: int) -> Dict:
        """
        Get comprehensive bonus summary for a user
        """
        from bonus.bonus_state import (
            get_user_bonus_history, 
            get_pending_bonuses, 
            get_total_paid_bonuses
        )
        
        try:
            return {
                'pending_bonuses': get_pending_bonuses(user_id),
                'bonus_history': get_user_bonus_history(user_id, limit=10),
                'total_earnings': get_total_paid_bonuses(user_id)
            }
        except Exception as e:
            logger.error(f"Error getting bonus summary for user {user_id}: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def run_fraud_checks() -> Dict:
        """
        Run comprehensive fraud detection
        """
        from bonus.audit_fraud import (
            detect_cycle_in_referrals,
            detect_self_referrals,
            detect_rapid_multi_account_creation,
            detect_same_phone_misuse
        )
        
        try:
            return {
                'referral_cycles': detect_cycle_in_referrals(),
                'self_referrals': detect_self_referrals(),
                'rapid_creation': detect_rapid_multi_account_creation(),
                'phone_misuse': detect_same_phone_misuse()
            }
        except Exception as e:
            logger.error(f"Error running fraud checks: {e}")
            return {'error': str(e)}