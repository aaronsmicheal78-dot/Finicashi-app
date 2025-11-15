# bonus_orchestrator.py
from decimal import Decimal
from typing import Dict, Any, Tuple, List
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import text, and_
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from models import Payment, ReferralBonus
from bonus.validation import BonusValidationHelper
from bonus.audit_fraud import AuditLog
from bonus.bonus_payment import BonusPaymentHelper
from bonus.audit_fraud import AuditFraudHelper
from bonus.bonus_calculation import BonusCalculationHelper
from bonus.security_config import BonusSecurityConfig


class ProductionBonusOrchestrator:
    """
    Production-grade bonus orchestrator with comprehensive security,
    monitoring, and fault tolerance
    """
    
    def __init__(self):
        self.max_workers = 5
        self.processing_lock = threading.Lock()
        self.active_processes = {}
        
        # Security monitoring
        self.suspicious_activities = []
        self.performance_metrics = {
            'total_processed': 0,
            'successful_calculations': 0,
            'failed_calculations': 0,
            'average_processing_time': 0,
            'last_processed': None
        }
    
    def process_payment_bonuses_secure(self, payment_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        SECURE ENTRY POINT: Process bonuses for a payment with comprehensive security
        """
        security_context = {
            'payment_id': payment_id,
            'start_time': datetime.utcnow(),
            'security_checks_passed': [],
            'security_checks_failed': [],
            'threat_level': 'low',
            'processing_id': self._generate_processing_id()
        }
        
        try:
            # 1. PRE-PROCESSING SECURITY CHECKS
            current_app.logger.info(f"Starting secure bonus processing for payment {payment_id}")
            
            # Check if already processing (prevent duplicates)
            if not self._acquire_processing_lock(payment_id, security_context['processing_id']):
                return False, "Payment already being processed", security_context
            
            # Validate payment exists and is accessible
            payment = self._secure_payment_lookup(payment_id, security_context)
            if not payment:
                return False, "Payment security validation failed", security_context
            
            # 2. FRAUD DETECTION & RISK ASSESSMENT
            risk_assessment = self._perform_risk_assessment(payment, security_context)
            if risk_assessment['threat_level'] == 'high':
                self._handle_high_risk_payment(payment, risk_assessment, security_context)
                return False, "Payment flagged as high risk", security_context
            
            # 3. BONUS CALCULATION WITH SECURITY CONTEXT
            calculation_result = self._secure_bonus_calculation(payment, security_context)
            if not calculation_result['success']:
                return False, calculation_result['message'], security_context
            
            # 4. BONUS VALIDATION & INTEGRITY CHECKING
            validation_result = self._secure_bonus_validation(
                calculation_result['bonuses'], 
                payment, 
                security_context
            )
            if not validation_result['success']:
                return False, validation_result['message'], security_context
            
            # 5. SECURE BONUS STORAGE
            storage_result = self._secure_bonus_storage(
                validation_result['valid_bonuses'], 
                payment, 
                security_context
            )
            if not storage_result['success']:
                return False, storage_result['message'], security_context
            
            # 6. QUEUE FOR PAYOUT WITH MONITORING
            queue_result = self._secure_bonus_queuing(
                storage_result['stored_bonuses'], 
                security_context
            )
            
            # 7. COMPREHENSIVE AUDITING
            self._log_successful_processing(payment, security_context, calculation_result)
            
            security_context['end_time'] = datetime.utcnow()
            security_context['processing_duration'] = (
                security_context['end_time'] - security_context['start_time']
            ).total_seconds()
            
            current_app.logger.info(
                f"SECURE_PROCESSING_COMPLETE: Payment {payment_id}, "
                f"Bonuses: {len(validation_result['valid_bonuses'])}, "
                f"Threat Level: {security_context['threat_level']}, "
                f"Duration: {security_context['processing_duration']:.2f}s"
            )
            
            return True, f"Successfully processed {len(validation_result['valid_bonuses'])} bonuses", security_context
            
        except Exception as e:
            self._handle_processing_error(payment_id, e, security_context)
            return False, f"Processing error: {str(e)}", security_context
        
        finally:
            self._release_processing_lock(payment_id, security_context['processing_id'])
    
    def _secure_payment_lookup(self, payment_id: int, security_context: Dict) -> Payment:
        """Secure payment lookup with validation"""
        try:
            # Use row-level locking to prevent race conditions
            payment = Payment.query.with_for_update(
                skip_locked=True, nowait=True
            ).filter_by(id=payment_id).first()
            
            if not payment:
                security_context['security_checks_failed'].append('payment_not_found')
                return None
            
            # Validate payment state
            if payment.status != 'completed':
                security_context['security_checks_failed'].append(f'invalid_status: {payment.status}')
                return None
            
            # Check if bonuses already processed
            if getattr(payment, 'bonuses_calculated', False):
                security_context['security_checks_failed'].append('bonuses_already_calculated')
                return None
            
            # Check payment age (prevent processing old payments)
            payment_age = datetime.utcnow() - payment.created_at
            if payment_age > timedelta(days=30):
                security_context['security_checks_failed'].append('payment_too_old')
                return None
            
            security_context['security_checks_passed'].append('payment_validation')
            return payment
            
        except Exception as e:
            current_app.logger.error(f"Secure payment lookup failed: {str(e)}")
            security_context['security_checks_failed'].append(f'lookup_error: {str(e)}')
            return None
    
    def _perform_risk_assessment(self, payment: Payment, security_context: Dict) -> Dict[str, Any]:
        """Comprehensive risk assessment for payment"""
        risk_factors = []
        threat_level = 'low'
        
        try:
            # 1. Amount-based risk
            amount = Decimal(str(payment.amount))
            if amount > Decimal('5000000'):  # 5M UGX
                risk_factors.append('high_amount')
                threat_level = 'medium'
            
            if amount > Decimal('10000000'):  # 10M UGX
                risk_factors.append('very_high_amount')
                threat_level = 'high'
            
            # 2. User behavior risk
            user_recent_payments = Payment.query.filter(
                Payment.user_id == payment.user_id,
                Payment.created_at > datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if user_recent_payments > 3:
                risk_factors.append('rapid_payments')
                threat_level = 'medium'
            
            # 3. Network analysis
            network_risk = AuditFraudHelper.analyze_network_risk(payment.user_id)
            if network_risk.get('risk_score', 0) > 70:
                risk_factors.append('network_risk')
                threat_level = 'high'
            
            # 4. Geographic risk (if location data available)
            if hasattr(payment, 'ip_address'):
                geo_risk = self._assess_geographic_risk(payment.ip_address)
                if geo_risk == 'high':
                    risk_factors.append('geographic_risk')
                    threat_level = 'high'
            
            security_context['threat_level'] = threat_level
            security_context['risk_factors'] = risk_factors
            
            return {
                'threat_level': threat_level,
                'risk_factors': risk_factors,
                'risk_score': len(risk_factors) * 25  # Simple scoring
            }
            
        except Exception as e:
            current_app.logger.error(f"Risk assessment failed: {str(e)}")
            return {'threat_level': 'medium', 'risk_factors': ['assessment_failed'], 'risk_score': 50}
    
    def _secure_bonus_calculation(self, payment: Payment, security_context: Dict) -> Dict[str, Any]:
        """Secure bonus calculation with monitoring"""
        try:
            # Use the secure calculation method
            success, bonuses, message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            
            if not success:
                security_context['security_checks_failed'].append(f'calculation_failed: {message}')
                return {'success': False, 'message': message}
            
            # Additional security checks on calculated bonuses
            for bonus in bonuses:
                # Check for suspicious bonus amounts
                if Decimal(str(bonus['bonus_amount'])) > Decimal('1000000'):  # 1M UGX
                    security_context['threat_level'] = max(security_context['threat_level'], 'medium')
                    security_context['suspicious_bonuses'] = security_context.get('suspicious_bonuses', []) + [bonus]
            
            security_context['security_checks_passed'].append('bonus_calculation')
            
            return {
                'success': True,
                'bonuses': bonuses,
                'message': message,
                'audit_info': audit_info
            }
            
        except Exception as e:
            current_app.logger.error(f"Secure bonus calculation failed: {str(e)}")
            security_context['security_checks_failed'].append(f'calculation_error: {str(e)}')
            return {'success': False, 'message': f"Calculation error: {str(e)}"}
    
    def _secure_bonus_validation(self, bonuses: List[Dict], payment: Payment, security_context: Dict) -> Dict[str, Any]:
        """Secure bonus validation with integrity checks"""
        try:
            # Use the production validation helper
            valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonuses)
            
            # Additional security validation
            for bonus in valid_bonuses:
                # Check bonus amount limits
                bonus_amount = Decimal(str(bonus['bonus_amount']))
                if bonus_amount > BonusSecurityConfig.MAX_BONUS_AMOUNT:
                    invalid_bonuses.append({
                        **bonus,
                        'validation_error': 'Bonus amount exceeds maximum limit'
                    })
                    valid_bonuses.remove(bonus)
                    continue
                
                # Check user bonus limits
                user_daily_bonus = self._get_user_daily_bonus(bonus['user_id'])
                if user_daily_bonus + bonus_amount > BonusSecurityConfig.DAILY_BONUS_LIMIT_PER_USER:
                    invalid_bonuses.append({
                        **bonus,
                        'validation_error': 'User daily bonus limit exceeded'
                    })
                    valid_bonuses.remove(bonus)
            
            security_context['valid_bonuses_count'] = len(valid_bonuses)
            security_context['invalid_bonuses_count'] = len(invalid_bonuses)
            security_context['security_checks_passed'].append('bonus_validation')
            
            if invalid_bonuses:
                current_app.logger.warning(
                    f"Found {len(invalid_bonuses)} invalid bonuses for payment {payment.id}"
                )
            
            return {
                'success': True,
                'valid_bonuses': valid_bonuses,
                'invalid_bonuses': invalid_bonuses,
                'validation_details': batch_validation
            }
            
        except Exception as e:
            current_app.logger.error(f"Bonus validation failed: {str(e)}")
            security_context['security_checks_failed'].append(f'validation_error: {str(e)}')
            return {'success': False, 'message': f"Validation error: {str(e)}"}
    
    def _secure_bonus_storage(self, bonuses: List[Dict], payment: Payment, security_context: Dict) -> Dict[str, Any]:
        """Secure bonus storage with transaction safety"""
        try:
            stored_bonuses = []
            
            # Use database transaction for atomic operations
            with current_app.db.session.begin_nested():
                for bonus_data in bonuses:
                    # Create bonus record with additional security fields
                    bonus = ReferralBonus(**bonus_data)
                    bonus.security_hash = self._calculate_bonus_security_hash(bonus_data)
                    bonus.processing_id = security_context['processing_id']
                    bonus.threat_level = security_context['threat_level']
                    
                    current_app.db.session.add(bonus)
                    stored_bonuses.append(bonus)
                
                # Mark payment as processed
                payment.bonuses_calculated = True
                payment.bonuses_calculated_at = datetime.utcnow()
                payment.bonus_processing_id = security_context['processing_id']
            
            security_context['security_checks_passed'].append('bonus_storage')
            
            return {
                'success': True,
                'stored_bonuses': stored_bonuses,
                'message': f"Stored {len(stored_bonuses)} bonuses"
            }
            
        except Exception as e:
            current_app.db.session.rollback()
            current_app.logger.error(f"Bonus storage failed: {str(e)}")
            security_context['security_checks_failed'].append(f'storage_error: {str(e)}')
            return {'success': False, 'message': f"Storage error: {str(e)}"}
    
    def _secure_bonus_queuing(self, bonuses: List[ReferralBonus], security_context: Dict) -> Dict[str, Any]:
        """Secure bonus queuing for payout"""
        try:
            queued_count = 0
            
            for bonus in bonuses:
                success = BonusPaymentHelper.queue_bonus_payout(bonus.id)
                if success:
                    queued_count += 1
                else:
                    current_app.logger.warning(f"Failed to queue bonus {bonus.id} for payout")
            
            security_context['queued_bonuses_count'] = queued_count
            security_context['security_checks_passed'].append('bonus_queuing')
            
            return {
                'success': True,
                'queued_count': queued_count,
                'message': f"Queued {queued_count} bonuses for payout"
            }
            
        except Exception as e:
            current_app.logger.error(f"Bonus queuing failed: {str(e)}")
            security_context['security_checks_failed'].append(f'queuing_error: {str(e)}')
            return {'success': False, 'message': f"Queuing error: {str(e)}"}
    
    # Security utility methods
    def _acquire_processing_lock(self, payment_id: int, processing_id: str) -> bool:
        """Acquire processing lock to prevent duplicates"""
        key = f"processing_lock:payment:{payment_id}"
        return self.redis.set(key, processing_id, nx=True, ex=300)  # 5-minute lock
    
    def _release_processing_lock(self, payment_id: int, processing_id: str):
        """Release processing lock"""
        key = f"processing_lock:payment:{payment_id}"
        current_processing_id = self.redis.get(key)
        if current_processing_id == processing_id:
            self.redis.delete(key)
    
    def _generate_processing_id(self) -> str:
        """Generate unique processing ID"""
        import uuid
        return f"proc_{uuid.uuid4().hex[:16]}_{int(datetime.utcnow().timestamp())}"
    
    def _calculate_bonus_security_hash(self, bonus_data: Dict) -> str:
        """Calculate security hash for bonus integrity"""
        import hashlib
        import json
        
        data_str = json.dumps(bonus_data, sort_keys=True)
        return hashlib.sha256(
            f"{data_str}{current_app.config['SECRET_KEY']}".encode()
        ).hexdigest()
    
    def _get_user_daily_bonus(self, user_id: int) -> Decimal:
        """Get user's total bonuses for today"""
        today = datetime.utcnow().date()
        daily_bonus = ReferralBonus.query.filter(
            ReferralBonus.user_id == user_id,
            ReferralBonus.created_at >= today,
            ReferralBonus.status == 'paid'
        ).with_entities(
            text('COALESCE(SUM(amount), 0)')
        ).scalar()
        
        return Decimal(str(daily_bonus or 0))
    
    def _handle_high_risk_payment(self, payment: Payment, risk_assessment: Dict, security_context: Dict):
        """Handle high-risk payments with enhanced security"""
        security_context['threat_level'] = 'high'
        
        # Log for manual review
        audit_log = AuditLog(
            actor_id=payment.user_id,
            action='high_risk_payment_detected',
            ip_address='system',
            details={
                'payment_id': payment.id,
                'risk_factors': risk_assessment['risk_factors'],
                'risk_score': risk_assessment['risk_score'],
                'amount': float(payment.amount),
                'processing_id': security_context['processing_id']
            }
        )
        current_app.db.session.add(audit_log)
        
        # Notify security team
        self._send_security_alert(payment, risk_assessment)
        
        current_app.logger.warning(
            f"HIGH_RISK_PAYMENT: Payment {payment.id} flagged for manual review. "
            f"Risk factors: {risk_assessment['risk_factors']}"
        )
    
    def _handle_processing_error(self, payment_id: int, error: Exception, security_context: Dict):
        """Handle processing errors with security context"""
        security_context['error'] = str(error)
        security_context['end_time'] = datetime.utcnow()
        
        # Log error with security context
        current_app.logger.error(
            f"BONUS_PROCESSING_ERROR: Payment {payment_id}, "
            f"Processing ID: {security_context['processing_id']}, "
            f"Threat Level: {security_context['threat_level']}, "
            f"Error: {str(error)}"
        )
        
        # Create error audit log
        audit_log = AuditLog(
            actor_id=None,  # System error
            action='bonus_processing_error',
            ip_address='system',
            details=security_context
        )
        current_app.db.session.add(audit_log)
        current_app.db.session.commit()
    
    def _log_successful_processing(self, payment: Payment, security_context: Dict, calculation_result: Dict):
        """Log successful processing with security context"""
        audit_log = AuditLog(
            actor_id=payment.user_id,
            action='bonus_processing_complete',
            ip_address='system',
            details={
                'payment_id': payment.id,
                'processing_id': security_context['processing_id'],
                'threat_level': security_context['threat_level'],
                'bonuses_calculated': calculation_result.get('audit_info', {}).get('bonuses_calculated', 0),
                'total_bonus_amount': float(calculation_result.get('audit_info', {}).get('total_bonus_amount', 0)),
                'security_checks_passed': security_context['security_checks_passed'],
                'processing_duration': security_context.get('processing_duration', 0)
            }
        )
        current_app.db.session.add(audit_log)
        current_app.db.session.commit()