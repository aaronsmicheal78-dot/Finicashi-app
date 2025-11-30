# models.py — Canonical Flask-SQLAlchemy models (production-ready)
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, Index, event, Numeric, text
from extensions import db
from werkzeug.security import check_password_hash, generate_password_hash
from enum import Enum
from sqlalchemy.orm import joinedload

# ===========================================================
# ENUM DEFINITIONS
# ===========================================================

class TransactionType(Enum):
    PACKAGE = "package"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BONUS = "bonus"
    OTHER = "other"


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    

class KycStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ===========================================================
# BASE MIXIN FOR COMMON FIELDS
# ===========================================================

class BaseMixin:
    """Provides created_at and updated_at timestamps to inheriting models."""
    created_at = db.Column(db.DateTime(timezone=True), default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=db.func.now(),
                           onupdate=db.func.now())

# ===========================================================
# USER MODELS
# ===========================================================

class User(db.Model, BaseMixin):
    """Core user entity — one wallet, one profile, many transactions via wallet."""
    __tablename__ = 'users'
    __table_args__ = {"extend_existing": True}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=True, default="user", index=True)
    actual_balance = db.Column(db.Numeric(18, 2), default=0.00, server_default=text("0.00"))
    available_balance = db.Column(db.Numeric(18, 2), default=0.00, server_default=text("0.00"))
  
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # ID of user who referred this user
    referral_code_used = db.Column(db.String(20), nullable=True)  # The referral code used during signup
    referral_code = db.Column(db.String(20), unique=True, nullable=True)  # User's own referral code
    referral_bonus_eligible = db.Column(db.Boolean, default=True)  # Track if user is eligible for referral bonuses


    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    member_since = db.Column(db.DateTime(timezone=True), default=db.func.now())

    # Relationships
    profile = db.relationship('UserProfile', uselist=False, back_populates='user', cascade="all,delete-orphan")
    wallet = db.relationship('Wallet', uselist=False, back_populates='user', cascade="all,delete-orphan")
    referrals = db.relationship('Referral', back_populates='referrer', foreign_keys='Referral.referrer_id')
    
    bonuses = db.relationship('Bonus', back_populates='user', lazy='dynamic')
    packages = db.relationship('Package', back_populates='user')
    
    # Add these new fields for network tracking
    network_depth = db.Column(db.Integer, default=0)  # User's depth in the network
    direct_referrals_count = db.Column(db.Integer, default=0)  # Count of direct referrals
    total_network_size = db.Column(db.Integer, default=0)  # Total downline size
    
    # Network performance metrics
    network_total_investment = db.Column(db.Numeric(18, 2), default=0)
    network_active_members = db.Column(db.Integer, default=0)
    last_network_calculation = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    network_ancestors = db.relationship(
        'ReferralNetwork',
        foreign_keys='ReferralNetwork.descendant_id',
        backref='descendant_user',
        lazy='dynamic'
    )
    network_descendants = db.relationship(
        'ReferralNetwork',
        foreign_keys='ReferralNetwork.ancestor_id',
        backref='ancestor_user',
        lazy='dynamic'
    )

    __table_args__ = (
    # For User
    Index('idx_user_phone', 'phone'),
    Index('idx_user_referral_code', 'referral_code')

    )
    
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    


    def to_dict(self, include_packages=True, include_bonus=True):
        """Serialize user for JSON responses with optimized queries."""
        print(f"DEBUG to_dict: actual_balance={self.actual_balance}, available_balance={self.available_balance}")
        base_url = "https://finicashi-app.onrender.com/"
        referral_link = f"{base_url}?ref={self.referral_code}"         
        # 1. First create the basic dictionary
        result = {
            "id": self.id,
            "role": self.role,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "referralCode": self.referral_code,
            "referralLink": referral_link, 
            "memberSince": self.member_since.isoformat() if self.member_since else None,
            "isActive": self.is_active,
            "isVerified": self.is_verified,
          #  "actual_balance" : float(self.actual_balance) if self.actual_balance is not None else 0.0,
          #  "available_balance" : float(self.available_balance) if self.available_balance is not None else 0.0,
            "actualBalance": float(self.actual_balance) if hasattr(self, 'actual_balance') else Decimal("0"),
            "availableBalance": float(self.available_balance) if hasattr(self, 'available_balance') else Decimal("0"),
        }
        
        # 2. THEN add additional fields OUTSIDE the dict literal
        # FIXED: Use Python list filtering instead of SQLAlchemy query methods
        if hasattr(self, 'referrals') and self.referrals:
            active_referrals = [ref for ref in self.referrals if getattr(ref, 'status', None) == 'active']
            result["referralBonus"] = float(sum(ref.bonus_amount for ref in active_referrals if hasattr(ref, 'bonus_amount')))
        else:
            result["referralBonus"] = 0  

        if include_bonus and hasattr(self, 'bonuses'):
            # Since bonuses is a 'dynamic' relationship, it should work with filter_by
            try:
                result["bonus"] = float(self.bonuses.filter_by(status='active')
                                    .with_entities(db.func.sum(Bonus.amount))
                                    .scalar() or 0)
            except AttributeError:
                # Fallback to Python filtering if it's a list
                active_bonuses = [b for b in self.bonuses if getattr(b, 'status', None) == 'active']
                result["bonus"] = float(sum(b.amount for b in active_bonuses if hasattr(b, 'amount')))
        else:
            result["bonus"] = 0

        if include_packages and hasattr(self, 'packages'):
            active_packages = [p for p in self.packages if getattr(p, 'status', None) == 'active']
            result["packages"] = [
                {
                    "id": p.id,
                    "name": p.catalog.name if p.catalog else getattr(p, 'package', 'Unknown'),
                    "amount": p.catalog.amount if p.catalog else None,
                    "status": getattr(p, 'status', 'unknown'),
                    "bonus_percentage": float(p.catalog.bonus_percentage) if p.catalog and p.catalog.bonus_percentage else 0,
                    "duration_days": p.catalog.duration_days if p.catalog else None,
                    "activated_at": p.activated_at.isoformat() if getattr(p, 'activated_at', None) else None,
                    "expires_at": (
                        (p.expires_at.replace(tzinfo=timezone.utc) if p.expires_at.tzinfo is None else p.expires_at).isoformat()
                        if getattr(p, 'expires_at', None) else None
                    ),
                    "days_remaining": (
                        ((p.expires_at.replace(tzinfo=timezone.utc) if p.expires_at.tzinfo is None else p.expires_at)
                        - datetime.now(timezone.utc)).days
                        if getattr(p, 'expires_at', None) else None
                    )
                }
                for p in active_packages
            ]
        else:
            result["packages"] = []
        
        print(f"DEBUG: Final result keys: {list(result.keys())}")
        print(f"DEBUG: actualBalance in result: {'actualBalance' in result}")
        print(f"DEBUG: availableBalance in result: {'availableBalance' in result}")
        
        return result
   #========================================================
# USER PROFILE
# ===========================================================

class UserProfile(db.Model, BaseMixin):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    full_name = db.Column(db.String(150))
    national_id = db.Column(db.String(50), index=True)
    address = db.Column(db.String(255))
    kyc_status = db.Column(db.Enum(KycStatus), default=KycStatus.PENDING, nullable=True)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))

    user = db.relationship('User', back_populates='profile')

# ===========================================================
# WALLET & TRANSACTIONS
# ===========================================================

class Wallet(db.Model, BaseMixin):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    balance = db.Column(db.Numeric(precision=18, scale=2), nullable=False, default=0)
    currency = db.Column(db.String(10), default='UGX')

    user = db.relationship('User', back_populates='wallet')
    transactions = db.relationship('Transaction', back_populates='wallet', cascade="all,delete-orphan")

class Transaction(db.Model, BaseMixin):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # deposit, withdrawal, bonus, referral, payment
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)
    reference = db.Column(db.String(120), unique=True, nullable=True, index=True)

    wallet = db.relationship('Wallet', back_populates='transactions')

    Index('idx_transaction_created', 'created_at'),

# ===========================================================
# PAYMENTS & WITHDRAWALS
# ===========================================================

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete='SET NULL'), nullable=True)
    package_catalog_id = db.Column(db.Integer, db.ForeignKey('packagecatalog.id'), nullable=True)
    reference = db.Column(db.String(128), nullable=False)
    
    transaction_type = db.Column(db.String(50)) 
    balance_type_used = db.Column(db.String(20), default=None)
    transaction_id = db.Column(
        db.Integer,
        db.ForeignKey('transactions.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    provider = db.Column(db.String(50))
    method = db.Column(db.String(50))
    external_ref = db.Column(db.String(128), index=True)
    idempotency_key = db.Column(db.String(128), index=True)
   
    verified = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum('pending', 'completed', 'failed', 'cancelled', 
                              name='paymentstatus'), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default='UGX')
    amount = db.Column(db.Numeric(precision=10, scale=2), nullable=False)
    raw_response = db.Column(db.Text)
    phone_number = db.Column(db.String(32))
    payment_type = db.Column(db.String(50), default='package', nullable=False)

    user = db.relationship('User', backref=db.backref('payments', lazy=True))
    package_catalog = db.relationship('PackageCatalog', backref='payments')
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    purchase_id = db.Column(db.String(100), nullable=True)
    
    __table_args__ = (
       
        UniqueConstraint('reference', name='uq_payments_reference'),
        UniqueConstraint('idempotency_key', 'external_ref', name='uq_payments_idempotency_external'),
    )

class PackageCatalog(db.Model):
    __tablename__ = 'packagecatalog'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reward_description = db.Column(db.Text)
    bonus_percentage = db.Column(db.Numeric(5, 2), default=0)
    duration_days = db.Column(db.Integer, default=30)
    features = db.Column(db.JSON)  
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), 
                          onupdate=db.func.current_timestamp())

class Withdrawal(db.Model, BaseMixin):
    __tablename__ = 'withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))  
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True, index=True)
    destination = db.Column(db.String(255))  # mobile number or bank account
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(50), default='pending')
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    fee = db.Column(db.Numeric(12,2), default=0)
    actual_balance_deducted = db.Column(db.Float, default=0.0)
    available_balance_deducted = db.Column(db.Float, default=0.0)
    hold_period_applied = db.Column(db.Boolean, default=False) 
    reference = db.Column(db.String(255), nullable=True)
    external_ref = db.Column(db.String(128), index=True)
    net_amount = db.Column(db.Numeric(precision=18, scale=2), nullable=True)
    #provider_reference = db.Column(db.String(255), nullable=True)
    net_amount = db.Column(
    db.Numeric(18, 2),   # or db.DECIMAL(18, 2)
    nullable=True,
    index=True
)



# ===========================================================
# BONUS & REFERRALS
# ===========================================================

class Bonus(db.Model, BaseMixin):
    __tablename__ = 'bonuses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=18, scale=2),  nullable=True)
    type = db.Column(db.String(50)) # signup, daily, 
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=db.func.now())
    package_id = db.Column(db.Integer, db.ForeignKey('packages.id'))
    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)


    user = db.relationship('User', back_populates='bonuses')
   
#==========================================================================
#for temporary testing the dynamic admin dashboard

class Package(db.Model, BaseMixin):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    catalog_id = db.Column(db.Integer, db.ForeignKey('packagecatalog.id', ondelete='SET NULL'), nullable=True)
    package = db.Column(db.String(50),  nullable=True)
    type = db.Column(db.String(50))  
    status = db.Column(db.String(20), default='active')
    package_amount = db.Column(db.Numeric(10, 2), nullable=False)  
    total_bonus_received = db.Column(db.Numeric(10, 2), default=0) 
    
    activated_at = db.Column(db.DateTime, default=db.func.now())
    expires_at = db.Column(db.DateTime, nullable=True)
    daily_bonus_rate = db.Column(db.Numeric(10, 5), nullable=False, default=0.05)  
    total_bonus_paid = db.Column(db.Numeric(10, 2), default=0)

    # New columns for Package model
    last_bonus_date = db.Column(db.DateTime, nullable=True)
    next_bonus_date = db.Column(db.DateTime, nullable=True)
    bonus_count = db.Column(db.Integer, default=0)
    max_bonus_amount = db.Column(db.Numeric(15, 2), default=0)  
    
    total_days_paid = db.Column(db.Integer, default=0)
    is_bonus_locked = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', back_populates='packages')
    catalog = db.relationship('PackageCatalog', backref='user_packages')

    Index('idx_package_user_status', 'user_id', 'status'),
    Index('idx_package_expires', 'expires_at'),


class ReferralBonus(db.Model, BaseMixin):
    __tablename__ = 'referral_bonuses'  # Fixed table name
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    type = db.Column(db.String(50))  # 'direct', 'indirect', 'level_bonus'
    status = db.Column(db.String(20), default='active')
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True, index=True)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    level = db.Column(db.Integer, nullable=False)  # 1-20
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bonus_amount = db.Column(db.Float, nullable=False)
    ancestor_id = db.Column(db.Integer, nullable=True)
    amount = db.column_property(bonus_amount)
   

    qualifying_amount = db.Column(db.Numeric(18, 2), nullable=False)  # Amount that triggered bonus
    bonus_percentage = db.Column(db.Numeric(5, 4), nullable=False)  # Actual percentage applied
    calculated_on = db.Column(db.DateTime, default=db.func.now())
    transaction_reference = db.Column(db.String(120), index=True)  # Link to original transaction
    security_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    processing_id = db.Column(db.String(64), unique=False, nullable=True, index=True)
    threat_level = db.Column(db.String(50), default='low')

    
  
    network_path = db.Column(db.String(500))  # Store the referral path as string (e.g., "1->5->12")
    is_paid_out = db.Column(db.Boolean, default=False)
    paid_out_at = db.Column(db.DateTime, nullable=True)
    

    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referral_earnings')
    referred_user = db.relationship('User', foreign_keys=[referred_id], backref='referred_by_me')
    payment = db.relationship('Payment', backref='referral_bonus')
    
    __table_args__ = (
        Index('idx_bonus_level_payout', 'level', 'is_paid_out'),
        Index('idx_bonus_calculated', 'calculated_on'),
       db.UniqueConstraint('payment_id', 'user_id', 'level', name='unique_payment_user_level'),
    )
    

class Referral(db.Model, BaseMixin):
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True) # who referred
    referred_email = db.Column(db.String(120))
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True) # who was referred
    reward_issued = db.Column(db.Boolean, default=False)
    ReferralBonus = db.Column(db.Integer, default=0)
    
    status = db.Column(db.String(20), default='pending')  
    created_at = db.Column(db.DateTime, default=db.func.now())
    completed_at = db.Column(db.DateTime, nullable=True)

    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referrals_made')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referrals_received')

    
# ===========================================================
# AUDITING & WEBHOOKS
# ===========================================================

class AuditLog(db.Model, BaseMixin):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(255))
    ip_address = db.Column(db.String(50))

class WebhookEvent(db.Model, BaseMixin):
    __tablename__ = 'webhook_events'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    event_type = db.Column(db.String(100))
    payload = db.Column(db.JSON, nullable=False)
    signature = db.Column(db.String(255))
    reference = db.Column(db.String(120), index=True)
    processed = db.Column(db.Boolean, default=False)
    processed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(50), default='pending')
    remarks = db.Column(db.String(255))

    def mark_processed(self, success=True, remarks=None):
        self.processed = True
        self.status = 'success' if success else 'failed'
        self.remarks = remarks
        self.processed_at = datetime.now(timezone.utc)

# ===========================================================
# SUPPORT & SESSIONS
# ===========================================================

class SupportTicket(db.Model, BaseMixin):
    __tablename__ = 'support_tickets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    subject = db.Column(db.String(255))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='open')

class LoginSession(db.Model, BaseMixin):
    __tablename__ = 'login_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    device = db.Column(db.String(100))
    location = db.Column(db.String(120))
    logout_time = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)

    def end_session(self):
        self.is_active = False
        self.logout_time = datetime.now(timezone.utc)

class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))

# ===========================================================
#   ------------IDEMPOTENCY KEY TRACKING
# ===========================================================

class IdempotencyKey(db.Model, BaseMixin):
    __tablename__ = 'idempotency_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    @staticmethod
    def make_expires(ttl_seconds: int = 3600):
        return datetime.utcnow() + timedelta(seconds=ttl_seconds)

    @staticmethod
    def cleanup_expired():
        """Remove expired idempotency keys."""
        now = datetime.utcnow()
        db.session.query(IdempotencyKey).filter(IdempotencyKey.expires_at < now).delete()
        db.session.commit()

class ReferralNetwork(db.Model, BaseMixin):
    """Tracks hierarchical relationships up to 20 levels"""
    __tablename__ = 'referral_network'
    
    id = db.Column(db.Integer, primary_key=True)
    ancestor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # Parent/upper level user
    descendant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # Child/lower level user
    depth = db.Column(db.Integer, nullable=False)  # Level distance (1-20)
    path_length = db.Column(db.Integer, nullable=False)  # Direct path length
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp)
    
    # Index for efficient tree traversal
    __table_args__ = (
        Index('idx_network_ancestor_depth', 'ancestor_id', 'depth'),
        Index('idx_network_descendant_ancestor', 'descendant_id', 'ancestor_id'),
        UniqueConstraint('ancestor_id', 'descendant_id', name='uq_network_relationship'),
            #-- Indexes for performance
 
    )

class ReferralBonusPlan(db.Model):
    """Configurable bonus percentages for each level (1-20)"""
    __tablename__ = 'referral_bonus_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.Integer, nullable=False, unique=True)  # 1 to 20
    bonus_percentage = db.Column(db.Numeric(5, 4), nullable=False)  # e.g., 0.10 for 10%
    minimum_qualifying_amount = db.Column(db.Numeric(18, 2), default=0)  # Min package amount to qualify
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    
    __table_args__ = (
        db.CheckConstraint('level >= 1 AND level <= 20', name='chk_level_range'),
        db.CheckConstraint('bonus_percentage >= 0 AND bonus_percentage <= 1', name='chk_bonus_range'),
    )

class NetworkSnapshot(db.Model):
    """Periodic snapshots of network growth for analytics"""
    __tablename__ = 'network_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    
    # Network metrics
    total_downline = db.Column(db.Integer, default=0)
    active_downline = db.Column(db.Integer, default=0)
    direct_referrals = db.Column(db.Integer, default=0)
    network_investment = db.Column(db.Numeric(18, 2), default=0)
    
    # Level-wise breakdown (store as JSON for flexibility)
    level_breakdown = db.Column(db.JSON)  # {1: 5, 2: 25, 3: 120, ...}
    
    __table_args__ = (
        UniqueConstraint('user_id', 'snapshot_date', name='uq_daily_snapshot'),
    )

class BonusPayoutQueue(db.Model):
    """Queue for processing bonus payouts"""
    __tablename__ = 'bonus_payout_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    referral_bonus_id = db.Column(db.Integer, db.ForeignKey('referral_bonuses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(18, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    attempt_count = db.Column(db.Integer, default=0)
    next_attempt = db.Column(db.DateTime, nullable=True)
    last_error = db.Column(db.Text)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_pqueue_status_attempt', 'status', 'next_attempt'),


    )
    
    def to_dict(self):
        """Convert activity to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'currency': self.currency
        }
    
    def __repr__(self):
        return f'<Activity {self.id} {self.type} {self.title}>'

# Index for better query performance
__table_args__ = (
    db.Index('idx_activities_timestamp_type', 'timestamp', 'type'),
    db.Index('idx_activities_user_timestamp', 'user_id', 'timestamp'),
)

# Add these indexes to ensure performance with large networks
additional_indexes = [
    # For network traversal
    Index('idx_network_ancestor_depth_desc', 'ancestor_id', 'depth', 'descendant_id'),
    Index('idx_network_descendant_depth', 'descendant_id', 'depth'),
    
    # For bonus calculations
    Index('idx_user_network_stats', 'user_id', 'total_network_size', 'network_total_investment'),
    Index('idx_bonus_calculation', 'level', 'status', 'calculated_on'),
    
    # For reporting
    Index('idx_snapshot_user_date', 'user_id', 'snapshot_date'),
]

