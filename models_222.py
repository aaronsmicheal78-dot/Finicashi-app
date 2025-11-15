# class User(db.Model, BaseMixin):
#     """Production-grade User model for PostgreSQL with closure table support"""
#     __tablename__ = 'users'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False, index=True)
#     email = db.Column(db.String(120), unique=True, nullable=True, index=True)
#     phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # AUTHENTICATION & SECURITY
#     # ===========================================================
#     password_hash = db.Column(db.String(255), nullable=False)
#     role = db.Column(db.String(20), nullable=False, default="user", index=True)
#     is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
#     is_verified = db.Column(db.Boolean, nullable=False, default=False, index=True)
#     member_since = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    
#     # ===========================================================
#     # FINANCIAL FIELDS (ALL Numeric for precision)
#     # ===========================================================
#     actual_balance = db.Column(db.Numeric(18, 2), nullable=False, default=0.00, server_default=text("0.00"))
#     available_balance = db.Column(db.Numeric(18, 2), nullable=False, default=0.00, server_default=text("0.00"))
    
#     # ===========================================================
#     # REFERRAL SYSTEM FIELDS
#     # ===========================================================
#     referred_by = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='SET NULL'), 
#         nullable=True, 
#         index=True
#     )
#     referral_code_used = db.Column(db.String(20), nullable=True, index=True)
#     referral_code = db.Column(db.String(20), unique=True, nullable=True, index=True)
#     referral_bonus_eligible = db.Column(db.Boolean, nullable=False, default=True)
    
#     # ===========================================================
#     # NETWORK HIERARCHY FIELDS (Closure Table Optimized)
#     # ===========================================================
#     network_depth = db.Column(db.SmallInteger, nullable=False, default=0, index=True)  # SmallInteger for 0-20 range
#     direct_referrals_count = db.Column(db.Integer, nullable=False, default=0, index=True)
#     total_network_size = db.Column(db.Integer, nullable=False, default=0, index=True)
    
#     # Network performance metrics
#     network_total_investment = db.Column(db.Numeric(18, 2), nullable=False, default=0)
#     network_active_members = db.Column(db.Integer, nullable=False, default=0, index=True)
#     last_network_calculation = db.Column(db.DateTime(timezone=True), nullable=True)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     # Self-referral relationship
#     referrer = db.relationship(
#         'User', 
#         remote_side=[id],
#         backref=db.backref('direct_referrals', lazy='dynamic'),
#         foreign_keys=[referred_by]
#     )
    
#     # Core relationships
#     profile = db.relationship(
#         'UserProfile', 
#         uselist=False, 
#         back_populates='user', 
#         cascade="all,delete-orphan",
#         lazy='joined'  # Eager load for frequent access
#     )
    
#     wallet = db.relationship(
#         'Wallet', 
#         uselist=False, 
#         back_populates='user', 
#         cascade="all,delete-orphan",
#         lazy='joined'  # Eager load for frequent access
#     )
    
#     # Referral relationships
#     referrals_made = db.relationship(
#         'Referral',
#         foreign_keys='Referral.referrer_id',
#         back_populates='referrer',
#         lazy='dynamic'
#     )
    
#     bonuses = db.relationship('Bonus', back_populates='user', lazy='dynamic')
#     packages = db.relationship('Package', back_populates='user', lazy='dynamic')
    
#     # Closure table relationships
#     network_ancestors = db.relationship(
#         'ReferralNetwork',
#         foreign_keys='ReferralNetwork.descendant_id',
#         backref='descendant_user',
#         lazy='dynamic',
#         viewonly=True  # Read-only for closure table
#     )
    
#     network_descendants = db.relationship(
#         'ReferralNetwork', 
#         foreign_keys='ReferralNetwork.ancestor_id',
#         backref='ancestor_user', 
#         lazy='dynamic',
#         viewonly=True  # Read-only for closure table
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS FOR PERFORMANCE
#     # ===========================================================
#     __table_args__ = (
#         # Index for common query patterns
#         Index('idx_user_network_stats', 'network_depth', 'direct_referrals_count', 'total_network_size'),
#         Index('idx_user_financial', 'actual_balance', 'available_balance'),
#         Index('idx_user_activity', 'is_active', 'is_verified', 'member_since'),
#         Index('idx_user_referral_lookup', 'referred_by', 'referral_code'),
        
#         # Partial indexes for better performance
#         Index('idx_active_users', 'is_active', postgresql_where=text('is_active = true')),
#         Index('idx_verified_users', 'is_verified', postgresql_where=text('is_verified = true')),
        
#         # Constraint to ensure network depth doesn't exceed 20
#         db.CheckConstraint('network_depth >= 0 AND network_depth <= 20', name='chk_network_depth_range'),
#         db.CheckConstraint('direct_referrals_count >= 0', name='chk_direct_referrals_positive'),
#         db.CheckConstraint('total_network_size >= 0', name='chk_network_size_positive'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def set_password(self, password: str):
#         """Hash and set password"""
#         if len(password) < 6:
#             raise ValueError("Password must be at least 6 characters")
#         self.password_hash = generate_password_hash(password)
    
#     def check_password(self, password: str) -> bool:
#         """Verify password against hash"""
#         return check_password_hash(self.password_hash, password)
    
#     def update_network_stats(self):
#         """Update network statistics (call periodically)"""
#         from sqlalchemy import func
#         from models import ReferralNetwork
        
#         # Update total network size
#         total_descendants = db.session.query(
#             func.count(ReferralNetwork.descendant_id.distinct())
#         ).filter(
#             ReferralNetwork.ancestor_id == self.id,
#             ReferralNetwork.depth > 0
#         ).scalar()
        
#         self.total_network_size = total_descendants or 0
#         self.last_network_calculation = db.func.now()
    
#     def to_dict(self, include_sensitive=False):
#         """Serialize user with security considerations"""
#         base_data = {
#             "id": self.id,
#             "username": self.username,
#             "email": self.email,
#             "phone": self.phone,
#             "role": self.role,
#             "is_active": self.is_active,
#             "is_verified": self.is_verified,
#             "member_since": self.member_since.isoformat() if self.member_since else None,
#             "network_depth": self.network_depth,
#             "direct_referrals_count": self.direct_referrals_count,
#             "total_network_size": self.total_network_size,
#         }
        
#         if include_sensitive:
#             base_data.update({
#                 "actual_balance": float(self.actual_balance),
#                 "available_balance": float(self.available_balance),
#                 "referral_code": self.referral_code,
#                 "referred_by": self.referred_by,
#             })
        
#         return base_data
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(User, 'before_insert')
#     def generate_referral_code(mapper, connection, target):
#         """Generate unique referral code before insert"""
#         if not target.referral_code:
#             import secrets
#             import string
            
#             def generate_code(length=8):
#                 chars = string.ascii_uppercase + string.digits
#                 return ''.join(secrets.choice(chars) for _ in range(length))
            
#             # Ensure uniqueness
#             for _ in range(10):  # Try 10 times
#                 code = generate_code()
#                 exists = db.session.query(
#                     User.query.filter_by(referral_code=code).exists()
#                 ).scalar()
#                 if not exists:
#                     target.referral_code = code
#                     break
#             else:
#                 raise ValueError("Could not generate unique referral code")
    
#     def __repr__(self):
#         return f"<User(id={self.id}, username='{self.username}', phone='{self.phone}')>"



#PAYMENTS TABLE
# class Payment(db.Model, BaseMixin):
#     """
#     Production-grade Payment model with bonus system integration
#     and comprehensive audit tracking
#     """
#     __tablename__ = 'payments'

#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.Integer, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)  # External reference
#     reference = db.Column(db.String(128), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # USER & PRODUCT RELATIONSHIPS
#     # ===========================================================
#     user_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='RESTRICT'), 
#         nullable=False,  # Payments must have a user
#         index=True
#     )
#     package_catalog_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('packagecatalog.id', ondelete='RESTRICT'), 
#         nullable=True,  # Allow non-package payments
#         index=True
#     )
    
#     # ===========================================================
#     # TRANSACTION LINKING
#     # ===========================================================
#     transaction_id = db.Column(
#         db.Integer,
#         db.ForeignKey('transactions.id', ondelete='SET NULL'),
#         nullable=True,
#         index=True
#     )
    
#     # ===========================================================
#     # PAYMENT CORE DATA
#     # ===========================================================
#     amount = db.Column(db.Numeric(12, 2), nullable=False)  # Increased precision
#     currency = db.Column(db.String(3), nullable=False, default='UGX')  # ISO 4217
#     exchange_rate = db.Column(db.Numeric(8, 4), default=1.0)  # For multi-currency
    
#     # ===========================================================
#     # PAYMENT METHOD & PROVIDER DETAILS
#     # ===========================================================
#     provider = db.Column(db.String(50), nullable=False)  # mtn, airtel, bank, etc.
#     provider_channel = db.Column(db.String(50))  # momo, card, bank_transfer
#     method = db.Column(db.String(50), nullable=False)  # mobile_money, card, bank
    
#     # Provider references
#     external_ref = db.Column(db.String(128), index=True)  # Provider transaction ID
#     provider_fee = db.Column(db.Numeric(10, 2), default=0)  # Fees charged by provider
    
#     # ===========================================================
#     # PAYMENT STATUS & LIFECYCLE
#     # ===========================================================
#     status = db.Column(
#         db.Enum(PaymentStatus),  # Use the shared Enum
#         nullable=False, 
#         default=PaymentStatus.PENDING,
#         index=True
#     )
    
#     # Status timestamps for audit
#     initiated_at = db.Column(db.DateTime(timezone=True))
#     processed_at = db.Column(db.DateTime(timezone=True))
#     completed_at = db.Column(db.DateTime(timezone=True))
#     failed_at = db.Column(db.DateTime(timezone=True))
#     cancelled_at = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # SECURITY & IDEMPOTENCY
#     # ===========================================================
#     idempotency_key = db.Column(db.String(128), unique=True, nullable=False, index=True)
#     idempotency_expires = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # BONUS SYSTEM INTEGRATION
#     # ===========================================================
#     bonus_eligible = db.Column(db.Boolean, nullable=False, default=True, index=True)
#     bonuses_calculated = db.Column(db.Boolean, nullable=False, default=False, index=True)
#     bonuses_calculated_at = db.Column(db.DateTime(timezone=True))
#     bonus_calculation_attempts = db.Column(db.SmallInteger, default=0)
    
#     # Track which levels received bonuses (bitmask or JSON)
#     bonus_levels_paid = db.Column(db.JSON)  # {1: true, 2: true, 3: false}
#     total_bonus_paid = db.Column(db.Numeric(12, 2), default=0)
    
#     # ===========================================================
#     # FRAUD DETECTION & AUDIT
#     # ===========================================================
#     verified = db.Column(db.Boolean, nullable=False, default=False, index=True)
#     verification_method = db.Column(db.String(50))  # webhook, manual, api
#     verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who verified
#     verified_at = db.Column(db.DateTime(timezone=True))
    
#     # Client information
#     ip_address = db.Column(db.String(45))  # IPv6 compatible
#     user_agent = db.Column(db.Text)
#     device_id = db.Column(db.String(255))  # For mobile app tracking
    
#     # Risk scoring
#     risk_score = db.Column(db.SmallInteger, default=0)  # 0-100
#     risk_reasons = db.Column(db.JSON)  # ['new_device', 'high_amount']
#     flagged = db.Column(db.Boolean, default=False, index=True)
    
#     # ===========================================================
#     # PAYMENT SPECIFIC DATA
#     # ===========================================================
#     phone_number = db.Column(db.String(20))  # For mobile money
#     account_number = db.Column(db.String(50))  # For bank transfers
    
#     # Payment type classification
#     payment_type = db.Column(db.String(50), nullable=False, default='package')  # package, deposit, withdrawal
#     transaction_type = db.Column(db.String(50))  # More granular: package_purchase, wallet_topup
    
#     # Balance usage (if applicable)
#     balance_type_used = db.Column(db.String(20))  # main_balance, bonus_balance
#     balance_amount_used = db.Column(db.Numeric(12, 2), default=0)
    
#     # ===========================================================
#     # PROVIDER RESPONSE & WEBHOOK DATA
#     # ===========================================================
#     raw_request = db.Column(db.Text)  # What we sent to provider
#     raw_response = db.Column(db.Text)  # Raw response from provider
#     parsed_response = db.Column(db.JSON)  # Structured response data
    
#     webhook_received = db.Column(db.Boolean, default=False)
#     webhook_processed = db.Column(db.Boolean, default=False)
#     webhook_attempts = db.Column(db.SmallInteger, default=0)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     user = db.relationship(
#         'User', 
#         backref=db.backref('payments', lazy='dynamic', order_by='Payment.created_at.desc()')
#     )
    
#     package_catalog = db.relationship('PackageCatalog', backref='payments')
#     transaction = db.relationship('Transaction', backref='payment')
#     verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_payments')
    
#     # Bonus relationships
#     referral_bonuses = db.relationship(
#         'ReferralBonus', 
#         backref='payment',
#         lazy='dynamic',
#         cascade='all, delete-orphan'
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('reference', name='uq_payments_reference'),
#         UniqueConstraint('uuid', name='uq_payments_uuid'),
#         UniqueConstraint('idempotency_key', name='uq_payments_idempotency'),
        
#         # Composite indexes for common queries
#         Index('idx_payments_user_status', 'user_id', 'status'),
#         Index('idx_payments_bonus_eligible', 'bonus_eligible', 'bonuses_calculated'),
#         Index('idx_payments_created_status', 'created_at', 'status'),
#         Index('idx_payments_provider_ref', 'provider', 'external_ref'),
#         Index('idx_payments_amount_currency', 'amount', 'currency'),
        
#         # Partial indexes for better performance
#         Index('idx_payments_pending', 'status', postgresql_where=text("status = 'pending'")),
#         Index('idx_payments_completed', 'status', 'completed_at', postgresql_where=text("status = 'completed'")),
#         Index('idx_payments_recent', 'created_at', postgresql_where=text("created_at > NOW() - INTERVAL '30 days'")),
        
#         # Check constraints
#         db.CheckConstraint('amount > 0', name='chk_payment_amount_positive'),
#         db.CheckConstraint('bonus_calculation_attempts >= 0', name='chk_bonus_attempts_positive'),
#         db.CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='chk_risk_score_range'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def mark_completed(self, external_ref: str = None):
#         """Mark payment as completed with timestamp"""
#         self.status = PaymentStatus.COMPLETED
#         self.completed_at = db.func.now()
#         if external_ref:
#             self.external_ref = external_ref
#         self.verified = True
    
#     def mark_failed(self, reason: str = None):
#         """Mark payment as failed with timestamp"""
#         self.status = PaymentStatus.FAILED
#         self.failed_at = db.func.now()
#         if reason and hasattr(self, 'parsed_response'):
#             current_response = self.parsed_response or {}
#             current_response['failure_reason'] = reason
#             self.parsed_response = current_response
    
#     def is_bonus_eligible(self) -> bool:
#         """Check if payment is eligible for bonus calculation"""
#         return (
#             self.status == PaymentStatus.COMPLETED 
#             and self.bonus_eligible 
#             and not self.bonuses_calculated
#             and self.verified
#         )
    
#     def mark_bonuses_calculated(self, levels_paid: dict = None, total_bonus: Decimal = None):
#         """Mark that bonuses have been calculated for this payment"""
#         self.bonuses_calculated = True
#         self.bonuses_calculated_at = db.func.now()
        
#         if levels_paid:
#             self.bonus_levels_paid = levels_paid
#         if total_bonus:
#             self.total_bonus_paid = total_bonus
    
#     def calculate_risk_score(self) -> int:
#         """Calculate risk score based on payment characteristics"""
#         risk_score = 0
        
#         # High amount risk
#         if self.amount > Decimal('1000000'):  # 1M UGX
#             risk_score += 30
#         elif self.amount > Decimal('500000'):  # 500K UGX
#             risk_score += 15
        
#         # New device risk (pseudo-code - implement based on your device tracking)
#         if self._is_new_device():
#             risk_score += 20
        
#         # Unverified user risk
#         if not self.user.is_verified:
#             risk_score += 25
        
#         # Multiple recent payments risk
#         recent_payments = Payment.query.filter(
#             Payment.user_id == self.user_id,
#             Payment.created_at > db.func.now() - timedelta(hours=1)
#         ).count()
        
#         if recent_payments > 3:
#             risk_score += 20
        
#         self.risk_score = min(risk_score, 100)
#         return self.risk_score
    
#     def to_dict(self, include_sensitive: bool = False) -> dict:
#         """Serialize payment data"""
#         base_data = {
#             "id": self.id,
#             "uuid": self.uuid,
#             "reference": self.reference,
#             "user_id": self.user_id,
#             "amount": float(self.amount),
#             "currency": self.currency,
#             "status": self.status.value,
#             "provider": self.provider,
#             "method": self.method,
#             "payment_type": self.payment_type,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "completed_at": self.completed_at.isoformat() if self.completed_at else None,
#         }
        
#         if include_sensitive:
#             base_data.update({
#                 "external_ref": self.external_ref,
#                 "phone_number": self.phone_number,
#                 "bonus_eligible": self.bonus_eligible,
#                 "bonuses_calculated": self.bonuses_calculated,
#                 "risk_score": self.risk_score,
#                 "ip_address": self.ip_address,
#             })
        
#         return base_data
    
#     def __repr__(self):
#         return f"<Payment(id={self.id}, ref={self.reference}, amount={self.amount}, status={self.status})>"

#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(Payment, 'before_insert')
#     def generate_uuid_and_timestamps(mapper, connection, target):
#         """Generate UUID and set initial timestamps"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())
#         if not target.initiated_at:
#             target.initiated_at = db.func.now()

#     @staticmethod
#     @event.listens_for(Payment, 'before_update')
#     def update_status_timestamps(mapper, connection, target):
#         """Update status-specific timestamps"""
#         # Check if status changed
#         history = db.inspect(target)
#         if history.attrs.status.history.has_changes():
#             if target.status == PaymentStatus.COMPLETED and not target.completed_at:
#                 target.completed_at = db.func.now()
#             elif target.status == PaymentStatus.FAILED and not target.failed_at:
#                 target.failed_at = db.func.now()
#             elif target.status == PaymentStatus.CANCELLED and not target.cancelled_at:
#                 target.cancelled_at = db.func.now()

#REFFERALBONUS TABLE
# class ReferralBonus(db.Model, BaseMixin):
#     """
#     Production-grade Referral Bonus model with closure table integration
#     and comprehensive audit tracking
#     """
#     __tablename__ = 'referral_bonuses'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.Integer, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # BONUS RECIPIENT & SOURCE
#     # ===========================================================
#     user_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     referrer_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     referred_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=True,  # Can be null for indirect bonuses
#         index=True
#     )
#     payment_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('payments.id', ondelete='CASCADE'), 
#         nullable=False,  # Bonus must come from a payment
#         index=True
#     )
    
#     # ===========================================================
#     # BONUS CALCULATION DATA
#     # ===========================================================
#     level = db.Column(db.SmallInteger, nullable=False, index=True)  # 1-20
#     amount = db.Column(db.Numeric(12, 2), nullable=False)  # Actual bonus amount
#     qualifying_amount = db.Column(db.Numeric(12, 2), nullable=False)  # Purchase amount that triggered bonus
#     bonus_percentage = db.Column(db.Numeric(5, 4), nullable=False)  # 0.1000 for 10%
    
#     # Bonus type classification
#     bonus_type = db.Column(
#         db.Enum('direct', 'indirect', 'level', 'signup', name='bonustype'),
#         nullable=False,
#         default='level',
#         index=True
#     )
    
#     # ===========================================================
#     # BONUS STATUS & LIFECYCLE
#     # ===========================================================
#     status = db.Column(
#         db.Enum('pending', 'approved', 'paid', 'cancelled', 'rejected', name='bonusstatus'),
#         nullable=False,
#         default='pending',
#         index=True
#     )
    
#     # Status timestamps
#     calculated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
#     approved_at = db.Column(db.DateTime(timezone=True))
#     paid_at = db.Column(db.DateTime(timezone=True))
#     cancelled_at = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # PAYOUT TRACKING
#     # ===========================================================
#     payout_transaction_id = db.Column(
#         db.Integer,
#         db.ForeignKey('transactions.id', ondelete='SET NULL'),
#         nullable=True,
#         index=True
#     )
#     payout_reference = db.Column(db.String(128), unique=True, index=True)
#     payout_method = db.Column(db.String(50))  # wallet_credit, bank_transfer, etc.
    
#     # Retry and failure tracking
#     payout_attempts = db.Column(db.SmallInteger, default=0)
#     last_payout_attempt = db.Column(db.DateTime(timezone=True))
#     payout_failure_reason = db.Column(db.Text)
    
#     # ===========================================================
#     # NETWORK HIERARCHY TRACKING (Closure Table Integration)
#     # ===========================================================
#     network_path = db.Column(db.String(500))  # Human-readable: "1→5→12→15"
#     network_depth = db.Column(db.SmallInteger, nullable=False)  # Redundant but useful for queries
#     closure_path_hash = db.Column(db.String(64), index=True)  # Hash of network path for quick lookups
    
#     # Ancestry chain (for audit and reporting)
#     ancestry_chain = db.Column(db.JSON)  # [{"user_id": 1, "level": 3}, {"user_id": 5, "level": 2}]
    
#     # ===========================================================
#     # FRAUD DETECTION & COMPLIANCE
#     # ===========================================================
#     risk_score = db.Column(db.SmallInteger, default=0)  # 0-100
#     flagged = db.Column(db.Boolean, default=False, index=True)
#     audit_notes = db.Column(db.Text)
    
#     # Manual override fields
#     manually_approved = db.Column(db.Boolean, default=False)
#     approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin user ID
#     approval_notes = db.Column(db.Text)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     user = db.relationship(
#         'User', 
#         foreign_keys=[user_id],
#         backref=db.backref('referral_bonuses', lazy='dynamic', cascade='all, delete-orphan')
#     )
    
#     referrer = db.relationship(
#         'User', 
#         foreign_keys=[referrer_id],
#         backref=db.backref('bonuses_given', lazy='dynamic')
#     )
    
#     referred_user = db.relationship(
#         'User', 
#         foreign_keys=[referred_id],
#         backref=db.backref('bonuses_triggered', lazy='dynamic')
#     )
    
#     payment = db.relationship(
#         'Payment', 
#         backref=db.backref('referral_bonuses', lazy='dynamic', cascade='all, delete-orphan')
#     )
    
#     payout_transaction = db.relationship(
#         'Transaction', 
#         backref='referral_bonus_payout'
#     )
    
#     approver = db.relationship(
#         'User', 
#         foreign_keys=[approved_by],
#         backref='approved_bonuses'
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('uuid', name='uq_referral_bonus_uuid'),
#         UniqueConstraint('payout_reference', name='uq_bonus_payout_reference'),
        
#         # Prevent duplicate bonus calculations for same payment+user+level
#         UniqueConstraint('payment_id', 'user_id', 'level', name='uq_bonus_payment_user_level'),
        
#         # Composite indexes for common queries
#         Index('idx_bonus_user_status', 'user_id', 'status'),
#         Index('idx_bonus_level_status', 'level', 'status'),
#         Index('idx_bonus_payment_level', 'payment_id', 'level'),
#         Index('idx_bonus_calculated_status', 'calculated_at', 'status'),
#         Index('idx_bonus_payout_pending', 'status', 'payout_attempts', postgresql_where=text("status = 'approved'")),
#         Index('idx_bonus_network_depth', 'network_depth', 'status'),
        
#         # Partial indexes for performance
#         Index('idx_bonus_pending', 'status', postgresql_where=text("status = 'pending'")),
#         Index('idx_bonus_approved', 'status', postgresql_where=text("status = 'approved'")),
#         Index('idx_bonus_paid', 'status', 'paid_at', postgresql_where=text("status = 'paid'")),
        
#         # Check constraints
#         db.CheckConstraint('level >= 1 AND level <= 20', name='chk_bonus_level_range'),
#         db.CheckConstraint('amount >= 0', name='chk_bonus_amount_positive'),
#         db.CheckConstraint('qualifying_amount > 0', name='chk_qualifying_amount_positive'),
#         db.CheckConstraint('bonus_percentage >= 0 AND bonus_percentage <= 1', name='chk_bonus_percentage_range'),
#         db.CheckConstraint('payout_attempts >= 0', name='chk_payout_attempts_positive'),
#         db.CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='chk_risk_score_range'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def mark_approved(self, approved_by_user_id: int = None, notes: str = None):
#         """Mark bonus as approved"""
#         self.status = 'approved'
#         self.approved_at = db.func.now()
#         if approved_by_user_id:
#             self.manually_approved = True
#             self.approved_by = approved_by_user_id
#         if notes:
#             self.approval_notes = notes
    
#     def mark_paid(self, transaction_id: int, payout_reference: str):
#         """Mark bonus as paid with transaction reference"""
#         self.status = 'paid'
#         self.paid_at = db.func.now()
#         self.payout_transaction_id = transaction_id
#         self.payout_reference = payout_reference
    
#     def mark_failed(self, reason: str):
#         """Mark payout attempt as failed"""
#         self.payout_attempts += 1
#         self.last_payout_attempt = db.func.now()
#         self.payout_failure_reason = reason
    
#     def calculate_network_path_hash(self):
#         """Calculate hash for network path for quick lookups"""
#         import hashlib
#         if self.network_path:
#             self.closure_path_hash = hashlib.sha256(self.network_path.encode()).hexdigest()
    
#     def is_eligible_for_payout(self) -> bool:
#         """Check if bonus is eligible for payout"""
#         return (
#             self.status == 'approved'
#             and self.amount > 0
#             and self.payout_attempts < 5  # Max retry attempts
#             and not self.flagged
#             and self.risk_score < 80  # Medium risk threshold
#         )
    
#     def to_dict(self, include_sensitive: bool = False) -> dict:
#         """Serialize bonus data"""
#         base_data = {
#             "id": self.id,
#             "uuid": self.uuid,
#             "user_id": self.user_id,
#             "referrer_id": self.referrer_id,
#             "referred_id": self.referred_id,
#             "level": self.level,
#             "amount": float(self.amount),
#             "bonus_type": self.bonus_type,
#             "status": self.status,
#             "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
#             "network_depth": self.network_depth,
#         }
        
#         if include_sensitive:
#             base_data.update({
#                 "qualifying_amount": float(self.qualifying_amount),
#                 "bonus_percentage": float(self.bonus_percentage),
#                 "payment_id": self.payment_id,
#                 "risk_score": self.risk_score,
#                 "network_path": self.network_path,
#                 "payout_attempts": self.payout_attempts,
#             })
        
#         return base_data
    
#     def __repr__(self):
#         return f"<ReferralBonus(id={self.id}, user={self.user_id}, level={self.level}, amount={self.amount}, status={self.status})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(ReferralBonus, 'before_insert')
#     def generate_uuid_and_hash(mapper, connection, target):
#         """Generate UUID and network path hash before insert"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())
#         target.calculate_network_path_hash()

# #REFFERAL TABLE
# class Referral(db.Model, BaseMixin):
#     """
#     Production-grade Referral model for tracking direct referral relationships
#     with bonus system integration
#     """
#     __tablename__ = 'referrals'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.Integer, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # REFERRAL RELATIONSHIPS
#     # ===========================================================
#     referrer_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     referred_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,  # Must have a referred user
#         index=True
#     )
#     referred_email = db.Column(db.String(120), nullable=False)  # Email at time of referral
    
#     # ===========================================================
#     # REFERRAL STATUS & LIFECYCLE
#     # ===========================================================
#     status = db.Column(
#         db.Enum('pending', 'completed', 'cancelled', 'expired', name='referralstatus'),
#         nullable=False,
#         default='pending',
#         index=True
#     )
    
#     # Status timestamps
#     completed_at = db.Column(db.DateTime(timezone=True))
#     expired_at = db.Column(db.DateTime(timezone=True))
#     cancelled_at = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # BONUS TRACKING
#     # ===========================================================
#     signup_bonus_awarded = db.Column(db.Boolean, default=False, index=True)
#     signup_bonus_amount = db.Column(db.Numeric(10, 2), default=0)
#     signup_bonus_paid_at = db.Column(db.DateTime(timezone=True))
    
#     # First purchase bonus tracking
#     first_purchase_bonus_eligible = db.Column(db.Boolean, default=True, index=True)
#     first_purchase_bonus_awarded = db.Column(db.Boolean, default=False, index=True)
#     first_purchase_bonus_amount = db.Column(db.Numeric(10, 2), default=0)
#     first_purchase_bonus_paid_at = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # REFERRAL CONTEXT & METADATA
#     # ===========================================================
#     referral_code_used = db.Column(db.String(20), nullable=False, index=True)
#     referral_channel = db.Column(db.String(50))  # web, mobile, social_media, etc.
#     campaign_source = db.Column(db.String(100))  # UTM source tracking
#     ip_address = db.Column(db.String(45))  # IPv6 compatible
#     user_agent = db.Column(db.Text)
    
#     # ===========================================================
#     # COMPLETION CRITERIA
#     # ===========================================================
#     completion_requirement = db.Column(
#         db.Enum('signup', 'first_purchase', 'kyc_verified', name='completionrequirement'),
#         nullable=False,
#         default='first_purchase'
#     )
#     completion_notes = db.Column(db.Text)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     referrer = db.relationship(
#         'User', 
#         foreign_keys=[referrer_id],
#         backref=db.backref('referrals_made', lazy='dynamic', cascade='all, delete-orphan')
#     )
    
#     referred = db.relationship(
#         'User', 
#         foreign_keys=[referred_id],
#         backref=db.backref('referrals_received', lazy='dynamic')
#     )
    
#     # Link to bonus payments
#     signup_bonus_payment = db.relationship(
#         'ReferralBonus',
#         foreign_keys='ReferralBonus.referred_id',
#         primaryjoin=f"and_(Referral.referred_id == ReferralBonus.referred_id, "
#                    f"ReferralBonus.bonus_type == 'signup')",
#         uselist=False,
#         viewonly=True
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('uuid', name='uq_referral_uuid'),
#         UniqueConstraint('referrer_id', 'referred_id', name='uq_referral_relationship'),  # One referral per pair
#         UniqueConstraint('referred_email', name='uq_referral_email'),  # One referral per email
        
#         # Composite indexes
#         Index('idx_referral_status_completion', 'status', 'completed_at'),
#         Index('idx_referral_bonus_tracking', 'signup_bonus_awarded', 'first_purchase_bonus_eligible'),
#         Index('idx_referral_channel', 'referral_channel', 'created_at'),
        
#         # Partial indexes
#         Index('idx_referral_pending', 'status', postgresql_where=text("status = 'pending'")),
#         Index('idx_referral_completed', 'status', 'completed_at', postgresql_where=text("status = 'completed'")),
#         Index('idx_referral_active', 'status', postgresql_where=text("status IN ('pending', 'completed')")),
        
#         # Check constraints
#         db.CheckConstraint('referrer_id != referred_id', name='chk_no_self_referral'),
#         db.CheckConstraint('signup_bonus_amount >= 0', name='chk_signup_bonus_positive'),
#         db.CheckConstraint('first_purchase_bonus_amount >= 0', name='chk_purchase_bonus_positive'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def mark_completed(self, completion_type: str = None):
#         """Mark referral as completed"""
#         self.status = 'completed'
#         self.completed_at = db.func.now()
#         if completion_type:
#             self.completion_requirement = completion_type
    
#     def award_signup_bonus(self, amount: Decimal):
#         """Award signup bonus to referrer"""
#         self.signup_bonus_awarded = True
#         self.signup_bonus_amount = amount
#         self.signup_bonus_paid_at = db.func.now()
    
#     def award_first_purchase_bonus(self, amount: Decimal):
#         """Award first purchase bonus to referrer"""
#         self.first_purchase_bonus_awarded = True
#         self.first_purchase_bonus_amount = amount
#         self.first_purchase_bonus_paid_at = db.func.now()
#         self.first_purchase_bonus_eligible = False
    
#     def is_completable(self, user_action: str) -> bool:
#         """Check if referral can be completed based on user action"""
#         if self.status != 'pending':
#             return False
        
#         completion_map = {
#             'signup': self.completion_requirement == 'signup',
#             'first_purchase': self.completion_requirement == 'first_purchase',
#             'kyc_verified': self.completion_requirement == 'kyc_verified',
#         }
        
#         return completion_map.get(user_action, False)
    
#     def get_total_bonus_awarded(self) -> Decimal:
#         """Get total bonus awarded for this referral"""
#         total = Decimal('0')
#         if self.signup_bonus_awarded:
#             total += self.signup_bonus_amount
#         if self.first_purchase_bonus_awarded:
#             total += self.first_purchase_bonus_amount
#         return total
    
#     def to_dict(self, include_sensitive: bool = False) -> dict:
#         """Serialize referral data"""
#         base_data = {
#             "id": self.id,
#             "referrer_id": self.referrer_id,
#             "referred_id": self.referred_id,
#             "status": self.status,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#             "completed_at": self.completed_at.isoformat() if self.completed_at else None,
#             "completion_requirement": self.completion_requirement,
#         }
        
#         if include_sensitive:
#             base_data.update({
#                 "referred_email": self.referred_email,
#                 "referral_code_used": self.referral_code_used,
#                 "signup_bonus_awarded": self.signup_bonus_awarded,
#                 "signup_bonus_amount": float(self.signup_bonus_amount),
#                 "first_purchase_bonus_eligible": self.first_purchase_bonus_eligible,
#                 "first_purchase_bonus_awarded": self.first_purchase_bonus_awarded,
#                 "referral_channel": self.referral_channel,
#             })
        
#         return base_data
    
#     def __repr__(self):
#         return f"<Referral(id={self.id}, referrer={self.referrer_id}, referred={self.referred_id}, status={self.status})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(Referral, 'before_insert')
#     def generate_uuid_and_validate(mapper, connection, target):
#         """Generate UUID and validate referral before insert"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())
        
#         # Ensure referrer and referred are different
#         if target.referrer_id == target.referred_id:
#             raise ValueError("User cannot refer themselves")


#---------------------------------------
# REFFERRAL NETWORK TABLE

# class ReferralNetwork(db.Model, BaseMixin):
#     """
#     Production-optimized Closure Table for referral hierarchy
#     Supports efficient 20-level bonus calculations and network traversal
#     """
#     __tablename__ = 'referral_network'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.BigInteger, primary_key=True)  # BigInt for potential high volume
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # HIERARCHY RELATIONSHIPS
#     # ===========================================================
#     ancestor_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     descendant_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
    
#     # ===========================================================
#     # HIERARCHY METADATA
#     # ===========================================================
#     depth = db.Column(db.SmallInteger, nullable=False, index=True)  # 0-20, SmallInt for storage
#     path_length = db.Column(db.SmallInteger, nullable=False)  # Direct path length
#     is_direct = db.Column(db.Boolean, nullable=False, default=False, index=True)  # Direct referral
    
#     # Path tracking for audit and debugging
#     path_hash = db.Column(db.String(64), index=True)  # Hash of ancestor-descendant path
    
#     # ===========================================================
#     # PERFORMANCE & MAINTENANCE FIELDS
#     # ===========================================================
#     is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
#     last_verified = db.Column(db.DateTime(timezone=True))
#     verification_count = db.Column(db.SmallInteger, default=0)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     ancestor_user = db.relationship(
#         'User', 
#         foreign_keys=[ancestor_id],
#         backref=db.backref('network_descendants', lazy='dynamic')
#     )
    
#     descendant_user = db.relationship(
#         'User', 
#         foreign_keys=[descendant_id],
#         backref=db.backref('network_ancestors', lazy='dynamic')
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('ancestor_id', 'descendant_id', name='uq_network_relationship'),
#         UniqueConstraint('uuid', name='uq_network_uuid'),
        
#         # Critical composite indexes for closure table operations
#         Index('idx_network_ancestor_depth', 'ancestor_id', 'depth', 'descendant_id'),
#         Index('idx_network_descendant_ancestor', 'descendant_id', 'ancestor_id', 'depth'),
#         Index('idx_network_depth_ancestor', 'depth', 'ancestor_id'),
#         Index('idx_network_depth_descendant', 'depth', 'descendant_id'),
#         Index('idx_network_direct_relationships', 'ancestor_id', 'descendant_id', 'is_direct'),
#         Index('idx_network_path_hash', 'path_hash'),
        
#         # Partial indexes for common query patterns
#         Index('idx_network_active', 'is_active', postgresql_where=text("is_active = true")),
#         Index('idx_network_direct', 'is_direct', postgresql_where=text("is_direct = true")),
#         Index('idx_network_indirect', 'is_direct', postgresql_where=text("is_direct = false")),
#         Index('idx_network_depth_range', 'depth', postgresql_where=text("depth BETWEEN 1 AND 20")),
        
#         # Check constraints
#         db.CheckConstraint('depth >= 0 AND depth <= 20', name='chk_network_depth_range'),
#         db.CheckConstraint('path_length >= 0 AND path_length <= 20', name='chk_path_length_range'),
#         db.CheckConstraint('ancestor_id != descendant_id OR depth = 0', name='chk_no_self_loop'),
#         db.CheckConstraint('verification_count >= 0', name='chk_verification_count_positive'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def calculate_path_hash(self):
#         """Calculate hash for the relationship path"""
#         import hashlib
#         path_str = f"{self.ancestor_id}->{self.descendant_id}->{self.depth}"
#         self.path_hash = hashlib.sha256(path_str.encode()).hexdigest()
    
#     def mark_verified(self):
#         """Mark relationship as verified"""
#         self.last_verified = db.func.now()
#         self.verification_count += 1
    
#     def is_within_bonus_range(self) -> bool:
#         """Check if this relationship is within bonus calculation range (1-20)"""
#         return 1 <= self.depth <= 20
    
#     @classmethod
#     def get_ancestors_for_bonus(cls, descendant_id: int) -> List['ReferralNetwork']:
#         """Get ancestors eligible for bonus calculations (levels 1-20)"""
#         return cls.query.filter(
#             cls.descendant_id == descendant_id,
#             cls.depth.between(1, 20),
#             cls.is_active == True
#         ).order_by(cls.depth.asc()).all()
    
#     @classmethod
#     def get_descendants_at_level(cls, ancestor_id: int, level: int) -> List['ReferralNetwork']:
#         """Get all descendants at specific level"""
#         return cls.query.filter(
#             cls.ancestor_id == ancestor_id,
#             cls.depth == level,
#             cls.is_active == True
#         ).all()
    
#     def to_dict(self) -> dict:
#         """Serialize network relationship"""
#         return {
#             "id": self.id,
#             "ancestor_id": self.ancestor_id,
#             "descendant_id": self.descendant_id,
#             "depth": self.depth,
#             "path_length": self.path_length,
#             "is_direct": self.is_direct,
#             "is_active": self.is_active,
#             "created_at": self.created_at.isoformat() if self.created_at else None,
#         }
    
#     def __repr__(self):
#         return f"<ReferralNetwork(ancestor={self.ancestor_id}, descendant={self.descendant_id}, depth={self.depth})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(ReferralNetwork, 'before_insert')
#     def generate_uuid_and_hash(mapper, connection, target):
#         """Generate UUID and path hash before insert"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())
#         target.calculate_path_hash()
        
#         # Set is_direct based on depth
#         if target.depth == 1:
#             target.is_direct = True

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#REFFERAL BONUS PLAN TABLE
# class ReferralBonusPlan(db.Model, BaseMixin):
#     """
#     Production-grade bonus configuration with versioning and audit trail
#     Supports dynamic bonus percentage management for 20-level system
#     """
#     __tablename__ = 'referral_bonus_plan'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.Integer, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # BONUS CONFIGURATION
#     # ===========================================================
#     level = db.Column(db.SmallInteger, nullable=False, index=True)  # 1 to 20
#     bonus_percentage = db.Column(db.Numeric(5, 4), nullable=False)  # 0.1000 for 10%
#     minimum_qualifying_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
#     maximum_bonus_amount = db.Column(db.Numeric(12, 2), nullable=True)  # Cap per bonus
    
#     # ===========================================================
#     # PLAN METADATA & VERSIONING
#     # ===========================================================
#     plan_name = db.Column(db.String(100), nullable=False, default='Standard')
#     plan_version = db.Column(db.SmallInteger, nullable=False, default=1)
#     is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
#     is_default = db.Column(db.Boolean, nullable=False, default=False, index=True)
    
#     # Activation timeframe
#     effective_from = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
#     effective_until = db.Column(db.DateTime(timezone=True), nullable=True)
    
#     # ===========================================================
#     # PACKAGE-SPECIFIC BONUSES
#     # ===========================================================
#     package_catalog_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('packagecatalog.id', ondelete='CASCADE'), 
#         nullable=True,  # Null means applies to all packages
#         index=True
#     )
    
#     # ===========================================================
#     # AUDIT & COMPLIANCE
#     # ===========================================================
#     created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who created
#     approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who approved
#     approval_notes = db.Column(db.Text)
    
#     # Change tracking
#     last_modified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
#     modification_reason = db.Column(db.Text)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     package_catalog = db.relationship('PackageCatalog', backref='bonus_plans')
#     creator = db.relationship('User', foreign_keys=[created_by], backref='created_bonus_plans')
#     approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_bonus_plans')
#     modifier = db.relationship('User', foreign_keys=[last_modified_by], backref='modified_bonus_plans')
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('uuid', name='uq_bonus_plan_uuid'),
#         UniqueConstraint('level', 'package_catalog_id', 'plan_version', name='uq_plan_level_package_version'),
        
#         # Composite indexes
#         Index('idx_bonus_plan_active', 'is_active', 'effective_from', 'effective_until'),
#         Index('idx_bonus_plan_level_active', 'level', 'is_active'),
#         Index('idx_bonus_plan_package_level', 'package_catalog_id', 'level', 'is_active'),
#         Index('idx_bonus_plan_effective', 'effective_from', 'effective_until'),
#         Index('idx_bonus_plan_default', 'is_default', 'is_active'),
        
#         # Partial indexes
#         Index('idx_active_plans', 'is_active', postgresql_where=text("is_active = true")),
#         Index('idx_default_plans', 'is_default', postgresql_where=text("is_default = true")),
#         Index('idx_current_plans', 'is_active', 'effective_from', 'effective_until', 
#               postgresql_where=text("is_active = true AND effective_from <= NOW() AND (effective_until IS NULL OR effective_until > NOW())")),
        
#         # Check constraints
#         db.CheckConstraint('level >= 1 AND level <= 20', name='chk_level_range'),
#         db.CheckConstraint('bonus_percentage >= 0 AND bonus_percentage <= 1', name='chk_bonus_range'),
#         db.CheckConstraint('minimum_qualifying_amount >= 0', name='chk_min_qualifying_amount'),
#         db.CheckConstraint('maximum_bonus_amount IS NULL OR maximum_bonus_amount >= 0', name='chk_max_bonus_amount'),
#         db.CheckConstraint('plan_version >= 1', name='chk_plan_version_positive'),
#         db.CheckConstraint('effective_until IS NULL OR effective_until > effective_from', name='chk_effective_dates'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def is_currently_effective(self) -> bool:
#         """Check if bonus plan is currently effective"""
#         now = db.func.now()
#         return (
#             self.is_active and
#             self.effective_from <= now and
#             (self.effective_until is None or self.effective_until > now)
#         )
    
#     def calculate_bonus_amount(self, purchase_amount: Decimal) -> Decimal:
#         """Calculate bonus amount for given purchase amount"""
#         from decimal import Decimal, ROUND_DOWN
        
#         if purchase_amount < self.minimum_qualifying_amount:
#             return Decimal('0')
        
#         raw_bonus = purchase_amount * self.bonus_percentage
        
#         # Apply maximum cap if set
#         if self.maximum_bonus_amount and raw_bonus > self.maximum_bonus_amount:
#             return self.maximum_bonus_amount
        
#         return raw_bonus.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    
#     def deactivate(self, deactivated_by: int, reason: str = None):
#         """Deactivate bonus plan"""
#         self.is_active = False
#         self.last_modified_by = deactivated_by
#         self.modification_reason = reason or "Plan deactivated"
    
#     def create_new_version(self, created_by: int, **updates) -> 'ReferralBonusPlan':
#         """Create a new version of this bonus plan"""
#         new_plan = ReferralBonusPlan(
#             level=self.level,
#             bonus_percentage=updates.get('bonus_percentage', self.bonus_percentage),
#             minimum_qualifying_amount=updates.get('minimum_qualifying_amount', self.minimum_qualifying_amount),
#             maximum_bonus_amount=updates.get('maximum_bonus_amount', self.maximum_bonus_amount),
#             plan_name=updates.get('plan_name', self.plan_name),
#             plan_version=self.plan_version + 1,
#             package_catalog_id=updates.get('package_catalog_id', self.package_catalog_id),
#             created_by=created_by,
#             effective_from=updates.get('effective_from', db.func.now()),
#         )
#         return new_plan
    
#     def to_dict(self) -> dict:
#         """Serialize bonus plan"""
#         return {
#             "id": self.id,
#             "level": self.level,
#             "bonus_percentage": float(self.bonus_percentage),
#             "minimum_qualifying_amount": float(self.minimum_qualifying_amount),
#             "maximum_bonus_amount": float(self.maximum_bonus_amount) if self.maximum_bonus_amount else None,
#             "plan_name": self.plan_name,
#             "plan_version": self.plan_version,
#             "is_active": self.is_active,
#             "is_default": self.is_default,
#             "effective_from": self.effective_from.isoformat() if self.effective_from else None,
#             "effective_until": self.effective_until.isoformat() if self.effective_until else None,
#             "package_catalog_id": self.package_catalog_id,
#         }
    
#     def __repr__(self):
#         return f"<ReferralBonusPlan(level={self.level}, percentage={self.bonus_percentage}, active={self.is_active})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(ReferralBonusPlan, 'before_insert')
#     def generate_uuid(mapper, connection, target):
#         """Generate UUID before insert"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())




# #------------------------------------
# #NETWORK TABLE
# class NetworkSnapshot(db.Model, BaseMixin):
#     """
#     Production-grade network analytics snapshot system
#     Supports trend analysis and performance reporting
#     """
#     __tablename__ = 'network_snapshots'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.BigInteger, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # SNAPSHOT IDENTIFICATION
#     # ===========================================================
#     user_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     snapshot_date = db.Column(db.Date, nullable=False, index=True)
#     snapshot_type = db.Column(
#         db.Enum('daily', 'weekly', 'monthly', 'on_demand', name='snapshottype'),
#         nullable=False,
#         default='daily',
#         index=True
#     )
    
#     # ===========================================================
#     # NETWORK GROWTH METRICS
#     # ===========================================================
#     total_downline = db.Column(db.Integer, nullable=False, default=0)
#     active_downline = db.Column(db.Integer, nullable=False, default=0)
#     direct_referrals = db.Column(db.Integer, nullable=False, default=0)
#     active_direct_referrals = db.Column(db.Integer, nullable=False, default=0)
    
#     # ===========================================================
#     # FINANCIAL METRICS
#     # ===========================================================
#     network_investment = db.Column(db.Numeric(18, 2), nullable=False, default=0)
#     network_bonus_paid = db.Column(db.Numeric(18, 2), nullable=False, default=0)
#     network_bonus_earned = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    
#     # ===========================================================
#     # PERFORMANCE METRICS
#     # ===========================================================
#     conversion_rate = db.Column(db.Numeric(5, 4), default=0)  % of referrals that purchased
#     average_investment = db.Column(db.Numeric(12, 2), default=0)
#     network_growth_rate = db.Column(db.Numeric(8, 4), default=0)  % growth from previous period
    
#     # ===========================================================
#     # LEVEL-WISE BREAKDOWN
#     # ===========================================================
#     level_breakdown = db.Column(db.JSON, nullable=False)  # {"1": 5, "2": 25, "3": 120}
#     active_level_breakdown = db.Column(db.JSON)  # Active users per level
#     investment_level_breakdown = db.Column(db.JSON)  # Investment per level
    
#     # ===========================================================
#     # SNAPSHOT METADATA
#     # ===========================================================
#     calculation_duration = db.Column(db.Integer)  # Milliseconds taken to calculate
#     data_quality_score = db.Column(db.SmallInteger, default=100)  # 0-100 score
#     notes = db.Column(db.Text)
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     user = db.relationship(
#         'User', 
#         backref=db.backref('network_snapshots', lazy='dynamic', cascade='all, delete-orphan')
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('user_id', 'snapshot_date', 'snapshot_type', name='uq_user_snapshot_date_type'),
#         UniqueConstraint('uuid', name='uq_snapshot_uuid'),
        
#         # Composite indexes
#         Index('idx_snapshot_user_date', 'user_id', 'snapshot_date'),
#         Index('idx_snapshot_date_type', 'snapshot_date', 'snapshot_type'),
#         Index('idx_snapshot_network_growth', 'user_id', 'total_downline', 'snapshot_date'),
#         Index('idx_snapshot_financial', 'user_id', 'network_investment', 'network_bonus_earned'),
        
#         # Partial indexes
#         Index('idx_snapshot_recent', 'snapshot_date', postgresql_where=text("snapshot_date > CURRENT_DATE - INTERVAL '90 days'")),
#         Index('idx_snapshot_daily', 'snapshot_type', postgresql_where=text("snapshot_type = 'daily'")),
#         Index('idx_snapshot_weekly', 'snapshot_type', postgresql_where=text("snapshot_type = 'weekly'")),
        
#         # Check constraints
#         db.CheckConstraint('total_downline >= 0', name='chk_total_downline_positive'),
#         db.CheckConstraint('active_downline >= 0 AND active_downline <= total_downline', name='chk_active_downline_range'),
#         db.CheckConstraint('direct_referrals >= 0', name='chk_direct_referrals_positive'),
#         db.CheckConstraint('network_investment >= 0', name='chk_network_investment_positive'),
#         db.CheckConstraint('data_quality_score >= 0 AND data_quality_score <= 100', name='chk_data_quality_range'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def calculate_growth_metrics(self, previous_snapshot: 'NetworkSnapshot' = None):
#         """Calculate growth metrics compared to previous snapshot"""
#         if not previous_snapshot:
#             return
        
#         if previous_snapshot.total_downline > 0:
#             self.network_growth_rate = (
#                 (self.total_downline - previous_snapshot.total_downline) / 
#                 previous_snapshot.total_downline
#             )
        
#         if previous_snapshot.direct_referrals > 0:
#             self.conversion_rate = self.active_direct_referrals / self.direct_referrals
    
#     def get_level_count(self, level: int) -> int:
#         """Get user count for specific level"""
#         return self.level_breakdown.get(str(level), 0) if self.level_breakdown else 0
    
#     def get_active_level_count(self, level: int) -> int:
#         """Get active user count for specific level"""
#         return self.active_level_breakdown.get(str(level), 0) if self.active_level_breakdown else 0
    
#     def to_dict(self) -> dict:
#         """Serialize snapshot data"""
#         return {
#             "id": self.id,
#             "user_id": self.user_id,
#             "snapshot_date": self.snapshot_date.isoformat(),
#             "snapshot_type": self.snapshot_type,
#             "total_downline": self.total_downline,
#             "active_downline": self.active_downline,
#             "direct_referrals": self.direct_referrals,
#             "network_investment": float(self.network_investment),
#             "network_bonus_earned": float(self.network_bonus_earned),
#             "level_breakdown": self.level_breakdown,
#             "network_growth_rate": float(self.network_growth_rate) if self.network_growth_rate else 0,
#         }
    
#     def __repr__(self):
#         return f"<NetworkSnapshot(user={self.user_id}, date={self.snapshot_date}, downline={self.total_downline})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(NetworkSnapshot, 'before_insert')
#     def generate_uuid(mapper, connection, target):
#         """Generate UUID before insert"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())


#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# BONUS PAYOUT
# class BonusPayoutQueue(db.Model, BaseMixin):
#     """
#     Production-grade bonus payout queue with retry logic and failure handling
#     Supports asynchronous processing of bonus payments
#     """
#     __tablename__ = 'bonus_payout_queue'
    
#     # ===========================================================
#     # PRIMARY IDENTIFIERS
#     # ===========================================================
#     id = db.Column(db.BigInteger, primary_key=True)
#     uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
#     # ===========================================================
#     # PAYOUT RELATIONSHIPS
#     # ===========================================================
#     referral_bonus_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('referral_bonuses.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
#     user_id = db.Column(
#         db.Integer, 
#         db.ForeignKey('users.id', ondelete='CASCADE'), 
#         nullable=False,
#         index=True
#     )
    
#     # ===========================================================
#     # PAYOUT DETAILS
#     # ===========================================================
#     amount = db.Column(db.Numeric(12, 2), nullable=False)
#     currency = db.Column(db.String(3), nullable=False, default='UGX')
    
#     # ===========================================================
#     # PAYOUT STATUS & LIFECYCLE
#     # ===========================================================
#     status = db.Column(
#         db.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', name='payoutstatus'),
#         nullable=False,
#         default='pending',
#         index=True
#     )
    
#     # Status timestamps
#     queued_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
#     processing_started_at = db.Column(db.DateTime(timezone=True))
#     completed_at = db.Column(db.DateTime(timezone=True))
#     failed_at = db.Column(db.DateTime(timezone=True))
#     cancelled_at = db.Column(db.DateTime(timezone=True))
    
#     # ===========================================================
#     # RETRY LOGIC & FAILURE HANDLING
#     # ===========================================================
#     attempt_count = db.Column(db.SmallInteger, nullable=False, default=0)
#     max_attempts = db.Column(db.SmallInteger, nullable=False, default=5)
#     next_attempt = db.Column(db.DateTime(timezone=True), index=True)
#     last_attempt = db.Column(db.DateTime(timezone=True))
    
#     # Failure tracking
#     last_error = db.Column(db.Text)
#     error_code = db.Column(db.String(50))  # Systematic error classification
#     error_details = db.Column(db.JSON)  # Structured error information
    
#     # ===========================================================
#     # PAYOUT METHOD & DESTINATION
#     # ===========================================================
#     payout_method = db.Column(db.String(50), nullable=False, default='wallet')  # wallet, bank, mobile
#     destination_reference = db.Column(db.String(255))  # Account number, phone number, etc.
#     payout_reference = db.Column(db.String(128), unique=True, index=True)  # External reference
    
#     # ===========================================================
#     # FRAUD & COMPLIANCE
#     # ===========================================================
#     risk_score = db.Column(db.SmallInteger, default=0)
#     flagged = db.Column(db.Boolean, default=False, index=True)
#     manual_review_required = db.Column(db.Boolean, default=False, index=True)
#     reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
#     review_notes = db.Column(db.Text)
    
#     # ===========================================================
#     # PERFORMANCE METRICS
#     # ===========================================================
#     processing_duration = db.Column(db.Integer)  # Milliseconds
#     queue_wait_time = db.Column(db.Integer)  # Milliseconds in queue
    
#     # ===========================================================
#     # RELATIONSHIPS
#     # ===========================================================
#     referral_bonus = db.relationship(
#         'ReferralBonus', 
#         backref=db.backref('payout_queue_entries', lazy='dynamic', cascade='all, delete-orphan')
#     )
    
#     user = db.relationship(
#         'User', 
#         backref=db.backref('bonus_payouts', lazy='dynamic')
#     )
    
#     reviewer = db.relationship(
#         'User', 
#         foreign_keys=[reviewed_by],
#         backref='reviewed_payouts'
#     )
    
#     # ===========================================================
#     # TABLE ARGUMENTS & INDEXES
#     # ===========================================================
#     __table_args__ = (
#         # Unique constraints
#         UniqueConstraint('uuid', name='uq_payout_queue_uuid'),
#         UniqueConstraint('payout_reference', name='uq_payout_reference'),
        
#         # Composite indexes
#         Index('idx_pqueue_status_attempt', 'status', 'next_attempt', 'attempt_count'),
#         Index('idx_pqueue_user_status', 'user_id', 'status'),
#         Index('idx_pqueue_retry_schedule', 'next_attempt', 'status', 'attempt_count'),
#         Index('idx_pqueue_created_status', 'created_at', 'status'),
#         Index('idx_pqueue_risk_status', 'risk_score', 'status', 'flagged'),
        
#         # Partial indexes for performance
#         Index('idx_pqueue_pending', 'status', 'next_attempt', postgresql_where=text("status = 'pending'")),
#         Index('idx_pqueue_processing', 'status', postgresql_where=text("status = 'processing'")),
#         Index('idx_pqueue_failed_retry', 'status', 'attempt_count', 'next_attempt', 
#               postgresql_where=text("status = 'failed' AND attempt_count < max_attempts")),
#         Index('idx_pqueue_manual_review', 'manual_review_required', 'status', 
#               postgresql_where=text("manual_review_required = true")),
        
#         # Check constraints
#         db.CheckConstraint('amount > 0', name='chk_payout_amount_positive'),
#         db.CheckConstraint('attempt_count >= 0 AND attempt_count <= max_attempts', name='chk_attempt_count_range'),
#         db.CheckConstraint('max_attempts >= 1 AND max_attempts <= 10', name='chk_max_attempts_range'),
#         db.CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='chk_risk_score_range'),
#     )
    
#     # ===========================================================
#     # METHODS
#     # ===========================================================
#     def mark_processing(self):
#         """Mark payout as processing"""
#         self.status = 'processing'
#         self.processing_started_at = db.func.now()
#         self.attempt_count += 1
#         self.last_attempt = db.func.now()
        
#         # Calculate queue wait time
#         if self.queued_at:
#             self.queue_wait_time = int((self.processing_started_at - self.queued_at).total_seconds() * 1000)
    
#     def mark_completed(self, payout_reference: str):
#         """Mark payout as completed"""
#         self.status = 'completed'
#         self.completed_at = db.func.now()
#         self.payout_reference = payout_reference
        
#         # Calculate processing duration
#         if self.processing_started_at:
#             self.processing_duration = int((self.completed_at - self.processing_started_at).total_seconds() * 1000)
    
#     def mark_failed(self, error_message: str, error_code: str = None, retry_after: timedelta = None):
#         """Mark payout as failed and schedule retry"""
#         self.status = 'failed'
#         self.failed_at = db.func.now()
#         self.last_error = error_message
#         self.error_code = error_code
        
#         # Schedule next attempt
#         if self.attempt_count < self.max_attempts and retry_after:
#             self.next_attempt = db.func.now() + retry_after
#         else:
#             self.next_attempt = None
    
#     def can_retry(self) -> bool:
#         """Check if payout can be retried"""
#         return (
#             self.status == 'failed' and
#             self.attempt_count < self.max_attempts and
#             self.next_attempt is not None and
#             self.next_attempt <= db.func.now()
#         )
    
#     def calculate_next_attempt_delay(self) -> timedelta:
#         """Calculate delay for next attempt using exponential backoff"""
#         base_delay = timedelta(minutes=5)  # 5 minutes base
#         return base_delay * (2 ** (self.attempt_count - 1))  # Exponential backoff
    
#     def to_dict(self) -> dict:
#         """Serialize payout queue entry"""
#         return {
#             "id": self.id,
#             "user_id": self.user_id,
#             "referral_bonus_id": self.referral_bonus_id,
#             "amount": float(self.amount),
#             "status": self.status,
#             "attempt_count": self.attempt_count,
#             "max_attempts": self.max_attempts,
#             "next_attempt": self.next_attempt.isoformat() if self.next_attempt else None,
#             "last_error": self.last_error,
#             "queued_at": self.queued_at.isoformat() if self.queued_at else None,
#         }
    
#     def __repr__(self):
#         return f"<BonusPayoutQueue(id={self.id}, user={self.user_id}, amount={self.amount}, status={self.status})>"
    
#     # ===========================================================
#     # HOOKS AND VALIDATION
#     # ===========================================================
#     @staticmethod
#     @event.listens_for(BonusPayoutQueue, 'before_insert')
#     def generate_uuid_and_schedule(mapper, connection, target):
#         """Generate UUID and schedule first attempt"""
#         import uuid
#         if not target.uuid:
#             target.uuid = str(uuid.uuid4())
        
#         # Set initial next_attempt for pending items
#         if target.status == 'pending' and not target.next_attempt:
#             target.next_attempt = db.func.now()