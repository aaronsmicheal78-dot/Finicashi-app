from flask import Blueprint, request, jsonify
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash
from blueprints.password_services import password_reset_service
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

password_bp = Blueprint('password', __name__)

@password_bp.route('/password/reset', methods=['POST'])
def request_password_reset():
    """
    Step 1: Request password reset code
    Validates user and sends reset code via SMS and email
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        phone = data.get('phone')
        email = data.get('email')
        
        if not phone or not email:
            return jsonify({'success': False, 'error': 'Phone and email are required'}), 400
        
        # Find user by phone AND email (both must match)
        user = User.query.filter_by(phone=phone, email=email).first()
        if not user:
            # Don't reveal whether user exists for security
            logger.warning(f"Password reset attempt for non-existent user: {phone}, {email}")
            return jsonify({
                'success': True,  # Still return success for security
                'message': 'If your account exists, reset codes have been sent to your phone and email.'
            }), 200
        
        # Generate reset code
        reset_code = password_reset_service.generate_reset_code()
        
        # Store reset code
        password_reset_service.store_reset_code(user.id, reset_code)
        
        # Send codes via SMS and email
        sms_sent = password_reset_service.send_sms_reset_code(phone, reset_code)
        email_sent = password_reset_service.send_email_reset_code(email, reset_code)
        
        # Log the action
        logger.info(f"Password reset code generated for user {user.id}: {reset_code}")
        
        return jsonify({
            'success': True,
            'message': 'Reset codes have been sent to your phone and email.'
        }), 200
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@password_bp.route('/password/register', methods=['POST'])
def register_new_password():
    """
    Step 2: Verify reset code and register new password
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
        
        phone = data.get('phone')
        email = data.get('email')
        reset_code = data.get('reset_code')
        new_password = data.get('new_password')
        
        if not all([phone, email, reset_code, new_password]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        
        # Find user
        user = User.query.filter_by(phone=phone, email=email).first()
        if not user:
            return jsonify({'success': False, 'error': 'Invalid user credentials'}), 400
        
        # Validate reset code
        is_valid, message = password_reset_service.validate_reset_code(user.id, reset_code)
        if not is_valid:
            return jsonify({'success': False, 'error': message}), 400
        
        # Check if new password is different from current
        if check_password_hash(user.password, new_password):
            return jsonify({'success': False, 'error': 'New password must be different from current password'}), 400
        
        # Hash and update password
        user.password = generate_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Mark reset code as used
        password_reset_service.mark_code_used(user.id)
        
        db.session.commit()
        
        # Log the password change
        logger.info(f"Password successfully reset for user {user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Password has been reset successfully. You can now login with your new password.'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Password registration error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500