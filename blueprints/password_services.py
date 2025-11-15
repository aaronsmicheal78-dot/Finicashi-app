import os
import random
import string
from datetime import datetime, timedelta
from flask_mail import Mail, Message
import africastalking
import logging

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self, app=None):
        self.app = app
        self.reset_codes = {}  # In production, use Redis instead
        
        # Initialize Africa's Talking for SMS
        if app:
            self.init_services(app)
    
    def init_services(self, app):
        # Email configuration (Gmail SMTP)
        app.config['MAIL_SERVER'] = 'smtp.gmail.com'
        app.config['MAIL_PORT'] = 587
        app.config['MAIL_USE_TLS'] = True
        app.config['MAIL_USERNAME'] = os.environ.get('GMAIL_USER')
        app.config['MAIL_PASSWORD'] = os.environ.get('GMAIL_APP_PASSWORD')
        
        self.mail = Mail(app)
        
        # Africa's Talking SMS configuration
        africastalking_username = os.environ.get('AT_USERNAME')
        africastalking_api_key = os.environ.get('AT_API_KEY')
        
        if africastalking_username and africastalking_api_key:
            africastalking.initialize(africastalking_username, africastalking_api_key)
            self.sms = africastalking.SMS
        else:
            logger.warning("Africa's Talking credentials not found")
            self.sms = None
    
    def generate_reset_code(self):
        """Generate a 6-digit reset code"""
        return ''.join(random.choices(string.digits, k=6))
    
    def send_sms_reset_code(self, phone, code):
        """Send reset code via SMS using Africa's Talking"""
        try:
            if not self.sms:
                logger.error("SMS service not initialized")
                return False
            
            message = f"Your password reset code is: {code}. It expires in 10 minutes."
            
            response = self.sms.send(message, [phone])
            logger.info(f"SMS sent to {phone}: {response}")
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    def send_email_reset_code(self, email, code):
        """Send reset code via email using Gmail SMTP"""
        try:
            msg = Message(
                subject="Password Reset Code",
                sender=self.app.config['MAIL_USERNAME'],
                recipients=[email],
                body=f"Your password reset code is: {code}\n\nThis code will expire in 10 minutes."
            )
            
            self.mail.send(msg)
            logger.info(f"Email sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    def store_reset_code(self, user_id, code):
        """Store reset code with expiration (10 minutes)"""
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        self.reset_codes[user_id] = {
            'code': code,
            'expires_at': expires_at,
            'used': False
        }
    
    def validate_reset_code(self, user_id, code):
        """Validate reset code"""
        if user_id not in self.reset_codes:
            return False, "Reset code not found"
        
        reset_data = self.reset_codes[user_id]
        
        if reset_data['used']:
            return False, "Reset code already used"
        
        if datetime.utcnow() > reset_data['expires_at']:
            del self.reset_codes[user_id]
            return False, "Reset code expired"
        
        if reset_data['code'] != code:
            return False, "Invalid reset code"
        
        return True, "Valid code"
    
    def mark_code_used(self, user_id):
        """Mark reset code as used"""
        if user_id in self.reset_codes:
            self.reset_codes[user_id]['used'] = True

# Global instance
password_reset_service = PasswordResetService()