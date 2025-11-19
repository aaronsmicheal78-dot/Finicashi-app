# # Debug: Check the actual referral network structure
# # bonus_orchestrator.py
# from decimal import Decimal
# from typing import Dict, Any, Tuple, List, Optional
# from datetime import datetime, timedelta, timezone
# from flask import current_app
# from sqlalchemy import text, and_
# from concurrent.futures import ThreadPoolExecutor, as_completed
# import threading
# import uuid
# import hashlib
# import json

# # Import your models - adjust these imports based on your actual structure
# from models import Payment, ReferralBonus, User, AuditLog
# from bonus.validation import BonusValidationHelper
# from bonus.audit_fraud import AuditFraudHelper
# from bonus.bonus_payment import BonusPaymentHelper
# from bonus.bonus_calculation import BonusCalculationHelper
# from bonus.security_config import BonusSecurityConfig


# class ProductionBonusOrchestrator:
#     """
#     Production-grade bonus orchestrator with comprehensive security,
#     monitoring, and fault tolerance
#     """
    
#     def __init__(self):
#         self.max_workers = 5
#         self.processing_lock = threading.Lock()
#         self.active_processes = {}
        
#         # Security monitoring
#         self.suspicious_activities = []
#         self.performance_metrics = {
#             'total_processed': 0,
#             'successful_calculations': 0,
#             'failed_calculations': 0,
#             'average_processing_time': 0,
#             'last_processed': None
#         }
        
#         # Initialize Redis if available, otherwise use in-memory lock
#         self._init_redis()
    
#     def _init_redis(self):
#         """Initialize Redis connection if available"""
#         try:
#             from redis import Redis
#             self.redis = Redis(
#                 host=current_app.config.get('REDIS_HOST', 'localhost'),
#                 port=current_app.config.get('REDIS_PORT', 6379),
#                 db=current_app.config.get('REDIS_DB', 0),
#                 decode_responses=True
#             )
#             # Test connection
#             self.redis.ping()
#             current_app.logger.info("✅ Redis connected for bonus processing locks")
#         except Exception as e:
#             current_app.logger.warning(f"Redis not available, using in-memory locks: {e}")
#             self.redis = None
#             self._memory_locks = {}
    
#     def process_payment_bonuses_secure(self, payment_id: int) -> Tuple[bool, str, Dict[str, Any]]:
#         """
#         SECURE ENTRY POINT: Process bonuses for a payment with comprehensive security
#         """
#         security_context = {
#             'payment_id': payment_id,
#             'start_time': datetime.now(timezone.utc),
#             'security_checks_passed': [],
#             'security_checks_failed': [],
#             'threat_level': 'low',
#             'processing_id': self._generate_processing_id()
#         }
        
#         try:
#             # 1. PRE-PROCESSING SECURITY CHECKS
#             current_app.logger.info(f"Starting secure bonus processing for payment {payment_id}")
            
#             # Check if already processing (prevent duplicates)
#             if not self._acquire_processing_lock(payment_id, security_context['processing_id']):
#                 return False, "Payment already being processed", security_context
            
#             # Validate payment exists and is accessible
#             payment = self._secure_payment_lookup(payment_id, security_context)
#             if not payment:
#                 return False, "Payment security validation failed", security_context
            
#             # 2. FRAUD DETECTION & RISK ASSESSMENT
#             risk_assessment = self._perform_risk_assessment(payment, security_context)
#             if risk_assessment['threat_level'] == 'high':
#                 self._handle_high_risk_payment(payment, risk_assessment, security_context)
#                 return False, "Payment flagged as high risk", security_context
            
#             # 3. BONUS CALCULATION WITH SECURITY CONTEXT
#             calculation_result = self._secure_bonus_calculation(payment, security_context)
#             if not calculation_result['success']:
#                 return False, calculation_result['message'], security_context
            
#             # 4. BONUS VALIDATION & INTEGRITY CHECKING
#             validation_result = self._secure_bonus_validation(
#                 calculation_result['bonuses'], 
#                 payment, 
#                 security_context
#             )
#             if not validation_result['success']:
#                 return False, validation_result['message'], security_context
            
#             # 5. SECURE BONUS STORAGE
#             storage_result = self._secure_bonus_storage(
#                 validation_result['valid_bonuses'], 
#                 payment, 
#                 security_context
#             )
#             if not storage_result['success']:
#                 return False, storage_result['message'], security_context
            
#             # 6. QUEUE FOR PAYOUT WITH MONITORING
#             queue_result = self._secure_bonus_queuing(
#                 storage_result['stored_bonuses'], 
#                 security_context
#             )
            
#             # 7. COMPREHENSIVE AUDITING
#             self._log_successful_processing(payment, security_context, calculation_result)
            
#             security_context['end_time'] = datetime.now(timezone.utc)
#             security_context['processing_duration'] = (
#                 security_context['end_time'] - security_context['start_time']
#             ).total_seconds()
            
#             current_app.logger.info(
#                 f"SECURE_PROCESSING_COMPLETE: Payment {payment_id}, "
#                 f"Bonuses: {len(validation_result['valid_bonuses'])}, "
#                 f"Threat Level: {security_context['threat_level']}, "
#                 f"Duration: {security_context['processing_duration']:.2f}s"
#             )
            
#             return True, f"Successfully processed {len(validation_result['valid_bonuses'])} bonuses", security_context
            
#         except Exception as e:
#             self._handle_processing_error(payment_id, e, security_context)
#             return False, f"Processing error: {str(e)}", security_context
        
#         finally:
#             self._release_processing_lock(payment_id, security_context['processing_id'])
    
#     def _secure_payment_lookup(self, payment_id: int, security_context: Dict) -> Optional[Payment]:
#         """Secure payment lookup with validation"""
#         try:
#             # Use row-level locking to prevent race conditions
#             # Note: Adjust based on your database support
#             payment = Payment.query.filter_by(id=payment_id).first()
            
#             if not payment:
#                 security_context['security_checks_failed'].append('payment_not_found')
#                 return None
            
#             # Validate payment state
#             if payment.status != 'completed':
#                 security_context['security_checks_failed'].append(f'invalid_status: {payment.status}')
#                 return None
            
#             # Check if bonuses already processed
#             existing_bonuses = ReferralBonus.query.filter_by(payment_id=payment_id).count()
#             if existing_bonuses > 0:
#                 security_context['security_checks_failed'].append('bonuses_already_calculated')
#                 return None
            
#             # Check payment age (prevent processing old payments)
#             payment_age = datetime.now(timezone.utc) - payment.created_at
#             if payment_age > timedelta(days=30):
#                 security_context['security_checks_failed'].append('payment_too_old')
#                 return None
            
#             security_context['security_checks_passed'].append('payment_validation')
#             return payment
            
#         except Exception as e:
#             current_app.logger.error(f"Secure payment lookup failed: {str(e)}")
#             security_context['security_checks_failed'].append(f'lookup_error: {str(e)}')
#             return None
    
#     def _perform_risk_assessment(self, payment: Payment, security_context: Dict) -> Dict[str, Any]:
#         """Comprehensive risk assessment for payment"""
#         risk_factors = []
#         threat_level = 'low'
        
#         try:
#             # 1. Amount-based risk
#             amount = Decimal(str(payment.amount))
#             if amount > Decimal('5000000'):  # 5M UGX
#                 risk_factors.append('high_amount')
#                 threat_level = 'medium'
            
#             if amount > Decimal('10000000'):  # 10M UGX
#                 risk_factors.append('very_high_amount')
#                 threat_level = 'high'
            
#             # 2. User behavior risk
#             user_recent_payments = Payment.query.filter(
#                 Payment.user_id == payment.user_id,
#                 Payment.created_at > datetime.now(timezone.utc) - timedelta(hours=1)
#             ).count()
            
#             if user_recent_payments > 3:
#                 risk_factors.append('rapid_payments')
#                 threat_level = 'medium'
            
#             # 3. Network analysis (if available)
#             try:
#                 network_risk = AuditFraudHelper.analyze_network_risk(payment.user_id)
#                 if network_risk.get('risk_score', 0) > 70:
#                     risk_factors.append('network_risk')
#                     threat_level = 'high'
#             except Exception as e:
#                 current_app.logger.warning(f"Network risk analysis failed: {e}")
            
#             # 4. Geographic risk (if location data available)
#             if hasattr(payment, 'ip_address') and payment.ip_address:
#                 geo_risk = self._assess_geographic_risk(payment.ip_address)
#                 if geo_risk == 'high':
#                     risk_factors.append('geographic_risk')
#                     threat_level = 'high'
            
#             security_context['threat_level'] = threat_level
#             security_context['risk_factors'] = risk_factors
            
#             return {
#                 'threat_level': threat_level,
#                 'risk_factors': risk_factors,
#                 'risk_score': len(risk_factors) * 25  # Simple scoring
#             }
            
#         except Exception as e:
#             current_app.logger.error(f"Risk assessment failed: {str(e)}")
#             return {'threat_level': 'medium', 'risk_factors': ['assessment_failed'], 'risk_score': 50}
    
#     def _secure_bonus_calculation(self, payment: Payment, security_context: Dict) -> Dict[str, Any]:
#         """Secure bonus calculation with monitoring"""
#         try:
#             # Use the secure calculation method
#             success, bonuses, message, audit_info = BonusCalculationHelper.calculate_all_bonuses_secure(payment)
            
#             if not success:
#                 security_context['security_checks_failed'].append(f'calculation_failed: {message}')
#                 return {'success': False, 'message': message}
            
#             # Additional security checks on calculated bonuses
#             suspicious_bonuses = []
#             for bonus in bonuses:
#                 # Check for suspicious bonus amounts
#                 bonus_amount = Decimal(str(bonus.get('amount', 0)))
#                 if bonus_amount > Decimal('1000000'):  # 1M UGX
#                     security_context['threat_level'] = max(security_context['threat_level'], 'medium')
#                     suspicious_bonuses.append(bonus)
            
#             if suspicious_bonuses:
#                 security_context['suspicious_bonuses'] = suspicious_bonuses
            
#             security_context['security_checks_passed'].append('bonus_calculation')
            
#             return {
#                 'success': True,
#                 'bonuses': bonuses,
#                 'message': message,
#                 'audit_info': audit_info
#             }
            
#         except Exception as e:
#             current_app.logger.error(f"Secure bonus calculation failed: {str(e)}")
#             security_context['security_checks_failed'].append(f'calculation_error: {str(e)}')
#             return {'success': False, 'message': f"Calculation error: {str(e)}"}
    
#     def _secure_bonus_validation(self, bonuses: List[Dict], payment: Payment, security_context: Dict) -> Dict[str, Any]:
#         """Secure bonus validation with integrity checks"""
#         try:
#             # Use the production validation helper
#             # Note: Adjust based on your actual BonusValidationHelper implementation
#             valid_bonuses = []
#             invalid_bonuses = []
#             batch_validation = {}
            
#             # Basic validation if BonusValidationHelper is not available
#             try:
#                 valid_bonuses, invalid_bonuses, batch_validation = BonusValidationHelper.validate_bonus_batch(bonuses)
#             except Exception as e:
#                 current_app.logger.warning(f"BonusValidationHelper not available, using basic validation: {e}")
#                 # Fallback basic validation
#                 for bonus in bonuses:
#                     if self._basic_bonus_validation(bonus):
#                         valid_bonuses.append(bonus)
#                     else:
#                         invalid_bonuses.append({
#                             **bonus,
#                             'validation_error': 'Basic validation failed'
#                         })
            
#             # Additional security validation
#             final_valid_bonuses = []
#             for bonus in valid_bonuses:
#                 # Check bonus amount limits
#                 bonus_amount = Decimal(str(bonus.get('amount', 0)))
#                 max_bonus = getattr(BonusSecurityConfig, 'MAX_BONUS_AMOUNT', Decimal('1000000'))
#                 if bonus_amount > max_bonus:
#                     invalid_bonuses.append({
#                         **bonus,
#                         'validation_error': f'Bonus amount exceeds maximum limit: {max_bonus}'
#                     })
#                     continue
                
#                 # Check user bonus limits
#                 user_daily_bonus = self._get_user_daily_bonus(bonus['user_id'])
#                 daily_limit = getattr(BonusSecurityConfig, 'DAILY_BONUS_LIMIT_PER_USER', Decimal('5000000'))
#                 if user_daily_bonus + bonus_amount > daily_limit:
#                     invalid_bonuses.append({
#                         **bonus,
#                         'validation_error': f'User daily bonus limit exceeded: {daily_limit}'
#                     })
#                     continue
                
#                 final_valid_bonuses.append(bonus)
            
#             security_context['valid_bonuses_count'] = len(final_valid_bonuses)
#             security_context['invalid_bonuses_count'] = len(invalid_bonuses)
#             security_context['security_checks_passed'].append('bonus_validation')
            
#             if invalid_bonuses:
#                 current_app.logger.warning(
#                     f"Found {len(invalid_bonuses)} invalid bonuses for payment {payment.id}"
#                 )
            
#             return {
#                 'success': True,
#                 'valid_bonuses': final_valid_bonuses,
#                 'invalid_bonuses': invalid_bonuses,
#                 'validation_details': batch_validation
#             }
            
#         except Exception as e:
#             current_app.logger.error(f"Bonus validation failed: {str(e)}")
#             security_context['security_checks_failed'].append(f'validation_error: {str(e)}')
#             return {'success': False, 'message': f"Validation error: {str(e)}"}
    
#     def _basic_bonus_validation(self, bonus: Dict) -> bool:
#         """Basic bonus validation fallback"""
#         try:
#             required_fields = ['user_id', 'amount', 'level']
#             for field in required_fields:
#                 if field not in bonus:
#                     return False
            
#             amount = Decimal(str(bonus['amount']))
#             if amount <= Decimal('0'):
#                 return False
            
#             level = bonus['level']
#             if not isinstance(level, int) or level < 1 or level > 20:
#                 return False
            
#             return True
#         except Exception:
#             return False
    
#     def _secure_bonus_storage(self, bonuses: List[Dict], payment: Payment, security_context: Dict) -> Dict[str, Any]:
#         """Secure bonus storage with transaction safety"""
#         try:
#             stored_bonuses = []
            
#             # Use database transaction
#             for bonus_data in bonuses:
#                 # Create bonus record with additional security fields
#                 bonus = ReferralBonus(
#                     user_id=bonus_data['user_id'],
#                     payment_id=payment.id,
#                     amount=bonus_data['amount'],
#                     level=bonus_data['level'],
#                     status='pending',
#                     security_hash=self._calculate_bonus_security_hash(bonus_data),
#                     processing_id=security_context['processing_id'],
#                     threat_level=security_context['threat_level'],
#                     created_at=datetime.now(timezone.utc)
#                 )
                
#                 # Add optional fields if they exist
#                 optional_fields = ['referrer_id', 'referred_id', 'bonus_percentage', 'qualifying_amount']
#                 for field in optional_fields:
#                     if field in bonus_data:
#                         setattr(bonus, field, bonus_data[field])
                
#                 current_app.db.session.add(bonus)
#                 stored_bonuses.append(bonus)
            
#             # Mark payment as processed
#             payment.bonuses_calculated = True
#             payment.bonuses_calculated_at = datetime.now(timezone.utc)
#             payment.bonus_processing_id = security_context['processing_id']
            
#             # Commit the transaction
#             current_app.db.session.commit()
            
#             security_context['security_checks_passed'].append('bonus_storage')
            
#             return {
#                 'success': True,
#                 'stored_bonuses': stored_bonuses,
#                 'message': f"Stored {len(stored_bonuses)} bonuses"
#             }
            
#         except Exception as e:
#             current_app.db.session.rollback()
#             current_app.logger.error(f"Bonus storage failed: {str(e)}")
#             security_context['security_checks_failed'].append(f'storage_error: {str(e)}')
#             return {'success': False, 'message': f"Storage error: {str(e)}"}
    
#     def _secure_bonus_queuing(self, bonuses: List[ReferralBonus], security_context: Dict) -> Dict[str, Any]:
#         """Secure bonus queuing for payout"""
#         try:
#             queued_count = 0
            
#             for bonus in bonuses:
#                 try:
#                     success = BonusPaymentHelper.queue_bonus_payout(bonus.id)
#                     if success:
#                         queued_count += 1
#                     else:
#                         current_app.logger.warning(f"Failed to queue bonus {bonus.id} for payout")
#                 except Exception as e:
#                     current_app.logger.error(f"Error queuing bonus {bonus.id}: {e}")
            
#             security_context['queued_bonuses_count'] = queued_count
#             security_context['security_checks_passed'].append('bonus_queuing')
            
#             return {
#                 'success': True,
#                 'queued_count': queued_count,
#                 'message': f"Queued {queued_count} bonuses for payout"
#             }
            
#         except Exception as e:
#             current_app.logger.error(f"Bonus queuing failed: {str(e)}")
#             security_context['security_checks_failed'].append(f'queuing_error: {str(e)}')
#             return {'success': False, 'message': f"Queuing error: {str(e)}"}
    
#     # Security utility methods
#     def _acquire_processing_lock(self, payment_id: int, processing_id: str) -> bool:
#         """Acquire processing lock to prevent duplicates"""
#         if self.redis:
#             key = f"processing_lock:payment:{payment_id}"
#             return self.redis.set(key, processing_id, nx=True, ex=300)  # 5-minute lock
#         else:
#             # In-memory fallback
#             with self.processing_lock:
#                 if payment_id in self._memory_locks:
#                     return False
#                 self._memory_locks[payment_id] = processing_id
#                 return True
    
#     def _release_processing_lock(self, payment_id: int, processing_id: str):
#         """Release processing lock"""
#         if self.redis:
#             key = f"processing_lock:payment:{payment_id}"
#             current_processing_id = self.redis.get(key)
#             if current_processing_id == processing_id:
#                 self.redis.delete(key)
#         else:
#             # In-memory fallback
#             with self.processing_lock:
#                 if self._memory_locks.get(payment_id) == processing_id:
#                     del self._memory_locks[payment_id]
    
#     def _generate_processing_id(self) -> str:
#         """Generate unique processing ID"""
#         return f"proc_{uuid.uuid4().hex[:16]}_{int(datetime.now(timezone.utc).timestamp())}"
    
#     def _calculate_bonus_security_hash(self, bonus_data: Dict) -> str:
#         """Calculate security hash for bonus integrity"""
#         # Create a stable representation of the data
#         stable_data = {
#             'user_id': bonus_data.get('user_id'),
#             'amount': str(bonus_data.get('amount')),
#             'level': bonus_data.get('level'),
#             'payment_id': bonus_data.get('purchase_id')
#         }
#         data_str = json.dumps(stable_data, sort_keys=True)
#         secret = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
#         return hashlib.sha256(f"{data_str}{secret}".encode()).hexdigest()
    
#     def _get_user_daily_bonus(self, user_id: int) -> Decimal:
#         """Get user's total bonuses for today"""
#         try:
#             today = datetime.now(timezone.utc).date()
#             result = current_app.db.session.execute(
#                 text("""
#                     SELECT COALESCE(SUM(amount), 0) 
#                     FROM referral_bonus 
#                     WHERE user_id = :user_id 
#                     AND DATE(created_at) = :today 
#                     AND status = 'paid'
#                 """),
#                 {'user_id': user_id, 'today': today}
#             ).scalar()
            
#             return Decimal(str(result or 0))
#         except Exception as e:
#             current_app.logger.error(f"Error getting user daily bonus: {e}")
#             return Decimal('0')
    
#     def _assess_geographic_risk(self, ip_address: str) -> str:
#         """Assess geographic risk based on IP address"""
#         # Simplified implementation - in production, use a geoIP service
#         try:
#             # Example: High risk countries (customize based on your needs)
#             high_risk_countries = []  # Add country codes as needed
            
#             # This would typically call a geoIP service
#             # For now, return low risk
#             return 'low'
#         except Exception as e:
#             current_app.logger.warning(f"Geographic risk assessment failed: {e}")
#             return 'medium'  # Default to medium on error
    
#     def _send_security_alert(self, payment: Payment, risk_assessment: Dict):
#         """Send security alert (stub implementation)"""
#         try:
#             current_app.logger.warning(
#                 f"SECURITY_ALERT: High risk payment {payment.id} "
#                 f"for user {payment.user_id}. Risk factors: {risk_assessment['risk_factors']}"
#             )
#             # In production, integrate with your alerting system (email, Slack, etc.)
#         except Exception as e:
#             current_app.logger.error(f"Failed to send security alert: {e}")
    
#     def _handle_high_risk_payment(self, payment: Payment, risk_assessment: Dict, security_context: Dict):
#         """Handle high-risk payments with enhanced security"""
#         security_context['threat_level'] = 'high'
        
#         # Log for manual review
#         audit_log = AuditLog(
#             actor_id=payment.user_id,
#             action='high_risk_payment_detected',
#             ip_address=getattr(payment, 'ip_address', 'system'),
#             details={
#                 'payment_id': payment.id,
#                 'risk_factors': risk_assessment['risk_factors'],
#                 'risk_score': risk_assessment['risk_score'],
#                 'amount': float(payment.amount),
#                 'processing_id': security_context['processing_id']
#             },
#             created_at=datetime.now(timezone.utc)
#         )
#         current_app.db.session.add(audit_log)
#         current_app.db.session.commit()
        
#         # Notify security team
#         self._send_security_alert(payment, risk_assessment)
        
#         current_app.logger.warning(
#             f"HIGH_RISK_PAYMENT: Payment {payment.id} flagged for manual review. "
#             f"Risk factors: {risk_assessment['risk_factors']}"
#         )
    
#     def _handle_processing_error(self, payment_id: int, error: Exception, security_context: Dict):
#         """Handle processing errors with security context"""
#         security_context['error'] = str(error)
#         security_context['end_time'] = datetime.now(timezone.utc)
        
#         # Log error with security context
#         current_app.logger.error(
#             f"BONUS_PROCESSING_ERROR: Payment {payment_id}, "
#             f"Processing ID: {security_context['processing_id']}, "
#             f"Threat Level: {security_context['threat_level']}, "
#             f"Error: {str(error)}"
#         )
        
#         # Create error audit log
#         audit_log = AuditLog(
#             actor_id=None,  # System error
#             action='bonus_processing_error',
#             ip_address='system',
#             details=security_context,
#             created_at=datetime.now(timezone.utc)
#         )
#         current_app.db.session.add(audit_log)
#         current_app.db.session.commit()
    
#     def _log_successful_processing(self, payment: Payment, security_context: Dict, calculation_result: Dict):
#         """Log successful processing with security context"""
#         audit_log = AuditLog(
#             actor_id=payment.user_id,
#             action='bonus_processing_complete',
#             ip_address='system',
#             details={
#                 'payment_id': payment.id,
#                 'processing_id': security_context['processing_id'],
#                 'threat_level': security_context['threat_level'],
#                 'bonuses_calculated': calculation_result.get('audit_info', {}).get('bonuses_calculated', 0),
#                 'total_bonus_amount': float(calculation_result.get('audit_info', {}).get('total_bonus_amount', 0)),
#                 'security_checks_passed': security_context['security_checks_passed'],
#                 'processing_duration': security_context.get('processing_duration', 0)
#             },
#             created_at=datetime.u()
#         )
#         current_app.db.session.add(audit_log)
#         current_app.db.session.commit()


# # Create a singleton instance for use throughout the application
# bonus_orchestrator = ProductionBonusOrchestrator()


























































































































# from models import User
# from extensions import db
# def debug_referral_network():
#     """See the actual relationships in your database"""
#     from sqlalchemy import text
    
#     print("🔍 REFERRAL NETWORK STRUCTURE:")
    
#     # Check all relationships for user 19
#     user_19_relationships = db.session.execute(
#         text("""
#             SELECT * FROM referral_network 
#             WHERE ancestor_id = 19 OR descendant_id = 19
#             ORDER BY depth
#         """)
#     ).fetchall()
    
#     print(f"User 19 relationships:")
#     for rel in user_19_relationships:
#         print(f"  Ancestor: {rel.ancestor_id} -> Descendant: {rel.descendant_id}, Depth: {rel.depth}")
    
#     # Check the entire network structure
#     all_relationships = db.session.execute(
#         text("""
#             SELECT ancestor_id, descendant_id, depth 
#             FROM referral_network 
#             WHERE depth > 0
#             ORDER BY descendant_id, depth
#             LIMIT 20
#         """)
#     ).fetchall()
    
#     print("Sample of all relationships (depth > 0):")
#     for rel in all_relationships:
#         ancestor = User.query.get(rel.ancestor_id)
#         descendant = User.query.get(rel.descendant_id)
#         ancestor_name = ancestor.username if ancestor else 'Unknown'
#         descendant_name = descendant.username if descendant else 'Unknown'
#         print(f"  {ancestor_name} ({rel.ancestor_id}) -> {descendant_name} ({rel.descendant_id}) [Level {rel.depth}]")

# # Call this in your bonus processing temporarily
# debug_referral_network()