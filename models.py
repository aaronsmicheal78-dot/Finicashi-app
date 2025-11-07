# models.py — Canonical Flask-SQLAlchemy models (production-ready)
from datetime import datetime, timedelta
from decimal import Decimal
import enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint, Index, event
from extensions import db
from werkzeug.security import check_password_hash, generate_password_hash


# ===========================================================
# ENUM DEFINITIONS
# ===========================================================

class PaymentStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
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
    balance = db.Column(db.Float, default=2000)

    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)

    referral_code = db.Column(db.String(50), unique=True, index=True)
    member_since = db.Column(db.DateTime(timezone=True), default=db.func.now())

    # Relationships
    profile = db.relationship('UserProfile', uselist=False, back_populates='user', cascade="all,delete-orphan")
    wallet = db.relationship('Wallet', uselist=False, back_populates='user', cascade="all,delete-orphan")
    referrals = db.relationship('Referral', back_populates='referrer', foreign_keys='Referral.referrer_id')

  
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Serialize user for JSON responses."""
        base_url = "https://finicashi-app.onrender.com/"
        referral_link = f"{base_url}/{self.username}/{self.referral_code}" if self.referral_code else None

        return {
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
            "balance": float(self.wallet.balance) if self.wallet else 2000,
            "bonus": float(sum([b.amount for b in self.bonuses if b.status == 'active'])) if hasattr(self, 'bonuses') else 5000,
            #"package": [p.package for p in self.packages] if hasattr(self, 'packages') else ['buy_one_get_one'] 
            "package": [p.package for p in self.packages] if (hasattr(self, 'packages') and self.packages) else ["buy_one_get_bonus"]
        }
# ===========================================================
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
    reference = db.Column(db.String(120), unique=True, nullable=False, index=True)

    wallet = db.relationship('Wallet', back_populates='transactions')

# ===========================================================
# PAYMENTS & WITHDRAWALS
# ===========================================================

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    
    # Allow multiple payments per user, unique constraint removed
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete='SET NULL'), nullable=True)
    
    reference = db.Column(db.String(128), nullable=False)
    
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
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default='UGX')
    raw_response = db.Column(db.Text)
    phone_number = db.Column(db.String(32))

    __table_args__ = (
        # Unique constraints with explicit names to prevent Alembic batch errors
        UniqueConstraint('reference', name='uq_payments_reference'),
        UniqueConstraint('idempotency_key', 'external_ref', name='uq_payments_idempotency_external'),
       # Index('ix_payments_external_ref', 'external_ref'),
    )
class Withdrawal(db.Model, BaseMixin):
    __tablename__ = 'withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True, index=True)
    destination = db.Column(db.String(255))  # mobile number or bank account
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    processed_at = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(50), default='pending')
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    fee = db.Column(db.Numeric(12,2), default=0) 

# ===========================================================
# BONUS & REFERRALS
# ===========================================================

class Bonus(db.Model, BaseMixin):
    __tablename__ = 'bonuses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=18, scale=2),  nullable=True)
    type = db.Column(db.String(50))  # e.g. 'referral', 'signup', etc.
    status = db.Column(db.String(20), default='active')
#==========================================================================
#for temporary testing the dynamic admin dashboard

class Package(db.Model, BaseMixin):
    __tablename__ = 'packages'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    package = db.Column(db.String(50),  nullable=True)
    type = db.Column(db.String(50))  
    status = db.Column(db.String(20), default='active')
class ReferralBonus(db.Model, BaseMixin):
    __tablename__ = 'Referralbonuses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=18, scale=2), nullable=False)
    type = db.Column(db.String(50))  # e.g. 'referral', 'signup', etc.
    status = db.Column(db.String(20), default='active')

    # optional metadata for auditability
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True, index=True)
    referred_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    level = db.Column(db.Integer, nullable=True)

class Referral(db.Model, BaseMixin):
    __tablename__ = 'referrals'

    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), index=True)
    referred_email = db.Column(db.String(120))
    referred_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    reward_issued = db.Column(db.Boolean, default=False)
    ReferralBonus = db.Column(db.Integer, default=False)
    referrer = db.relationship('User', back_populates='referrals', foreign_keys=[referrer_id])

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
        self.processed_at = datetime.utcnow()

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
        self.logout_time = datetime.utcnow()

class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(45))
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ===========================================================
# IDEMPOTENCY KEY TRACKING
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
