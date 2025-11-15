from bonus.services import BonusService
from bonus.refferral_tree import validate_referrer, store_referral_path
from models import User,Payment
from extensions import db

# 1. User registration with referral
def register_user_with_referral(user_data, referrer_id=None):
    if referrer_id:
        # Validate referrer
        validate_referrer(referrer_id, user_data['id'])
    
    # Create user...
    user = User(**user_data)
    db.session.add(user)
    db.session.commit()
    
    # Store referral path
    store_referral_path(user.id)
    
    return user

# 2. Process purchase bonuses (call from payment webhook)
def handle_payment_webhook(payment_data):
    payment = Payment(**payment_data)
    db.session.add(payment)
    db.session.commit()
    
    if payment.status == 'completed':
        result = BonusService.process_purchase_bonuses(payment.id)
        # Handle result...

# 3. Get user bonus dashboard
def get_user_dashboard(user_id):
    bonus_summary = BonusService.get_user_bonus_summary(user_id)
    # Return to frontend...

# 4. Admin fraud monitoring
def admin_fraud_report():
    fraud_data = BonusService.run_fraud_checks()
    # Display in admin panel...