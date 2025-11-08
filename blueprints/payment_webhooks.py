from flask import request, jsonify, current_app
from extensions import db
from models import Payment, User, PaymentStatus
from flask import Blueprint
#from blueprints.payments import PACKAGE_MAP
from models import Package

bp = Blueprint('payment_webhooks', __name__)

@bp.route('/payments/webhook', methods=['POST'])
def payment_webhook():
    """
    Secure Marz Pay webhook handler for production
    """
    try:
        current_app.logger.info("Marz Pay webhook received")
        
        # Validate JSON data
        webhook_data = request.get_json()
        if not webhook_data:
            current_app.logger.error("Webhook: No JSON data received")
            return jsonify({"status": "acknowledged"}), 200
        
        # Extract and validate required fields
        event_type = webhook_data.get('event_type')
        transaction_data = webhook_data.get('transaction', {})
        reference = transaction_data.get('reference')
        status = transaction_data.get('status')
        
        if not all([event_type, reference, status]):
            current_app.logger.error(f"Webhook: Missing required fields - event_type: {event_type}, reference: {reference}, status: {status}")
            return jsonify({"status": "acknowledged"}), 200
        
        current_app.logger.info(f"Webhook processing: {event_type} for {reference}")
        
        # Find payment by reference
        payment = Payment.query.filter_by(reference=reference).first()
        if not payment:
            current_app.logger.warning(f"Webhook: Unknown reference {reference}")
            return jsonify({"status": "acknowledged"}), 200
        
        # Idempotency check
        if payment.status == PaymentStatus.COMPLETED and event_type == 'collection.completed':
            current_app.logger.info(f"Webhook: Already processed {reference}")
            return jsonify({"status": "acknowledged"}), 200
        
        # Process webhook events
        if event_type == 'collection.completed' and status == 'completed':
            return handle_successful_payment(webhook_data, payment)
        elif event_type in ['collection.failed', 'collection.cancelled']:
            return handle_failed_payment(webhook_data, payment)
        else:
            current_app.logger.info(f"Webhook: Unhandled event {event_type} for {reference}")
            return jsonify({"status": "acknowledged"}), 200
            
    except Exception as e:
        current_app.logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
        return jsonify({"status": "acknowledged"}), 200

def handle_successful_payment(webhook_data, payment):
    """Handle successful payment webhook"""
    try:
        transaction_data = webhook_data.get('transaction', {})
        collection_data = webhook_data.get('collection', {})
        
        # Update payment record
        payment.status = PaymentStatus.COMPLETED
        payment.transaction_id = transaction_data.get('uuid')
        payment.provider_reference = collection_data.get('provider_reference')
        payment.provider = collection_data.get('provider')
        
        # Update user balance
        user = User.query.get(payment.user_id)
        if user:
            user.balance += payment.amount
            current_app.logger.info(f"Payment {payment.reference}: User {user.id} balance updated")
        
        # Update related records if any (e.g., subscriptions, orders)
        user = User.query.get(Package.user_id)
        if user:
           # user.package = PACKAGE_MAP.get(Package.package_name, user.package)
            current_app.logger.info(f"Package{payment.reference}: User {user.id} package updated")

        db.session.commit()
        current_app.logger.info(f"Payment {payment.reference} completed successfully")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to process successful payment {payment.reference}: {str(e)}")
        return jsonify({"status": "acknowledged"}), 200

def handle_failed_payment(webhook_data, payment):
    """Handle failed payment webhook"""
    webhook_data = request.get_json()
    try:
        payment.status = PaymentStatus.FAILED
        db.session.commit()
        current_app.logger.warning(f"Payment {payment.reference} marked as failed")
        return jsonify({"status": "acknowledged"}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to process failed payment {payment.reference}: {str(e)}")
        return jsonify({"status": "acknowledged"}), 200