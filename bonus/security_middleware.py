# security_middleware.py
from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime, timedelta
import hashlib
import hmac
from redis import Redis

class BonusSecurityMiddleware:
    """Security middleware for bonus engine endpoints"""
    
    def __init__(self):
        self.redis = Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.rate_limit_window = 60  # 1 minute
        self.max_requests = 100
    
    def rate_limit(self, f):
        """Rate limiting decorator for bonus endpoints"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP + endpoint as rate limit key
            key = f"rate_limit:{request.remote_addr}:{request.endpoint}"
            current = self.redis.get(key)
            
            if current and int(current) > self.max_requests:
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": self.rate_limit_window
                }), 429
            
            pipeline = self.redis.pipeline()
            pipeline.incr(key, 1)
            pipeline.expire(key, self.rate_limit_window)
            pipeline.execute()
            
            return f(*args, **kwargs)
        return decorated_function
    
    def validate_webhook_signature(self, f):
        """Validate webhook signatures for payment callbacks"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            signature = request.headers.get('X-Webhook-Signature')
            timestamp = request.headers.get('X-Webhook-Timestamp')
            
            if not signature or not timestamp:
                return jsonify({"error": "Missing security headers"}), 401
            
            # Check timestamp (prevent replay attacks)
            request_time = datetime.fromtimestamp(int(timestamp))
            if datetime.utcnow() - request_time > timedelta(minutes=5):
                return jsonify({"error": "Expired request"}), 401
            
            # Verify signature
            expected_signature = hmac.new(
                current_app.config['WEBHOOK_SECRET_KEY'].encode(),
                request.data + timestamp.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                current_app.logger.warning(f"Invalid webhook signature from {request.remote_addr}")
                return jsonify({"error": "Invalid signature"}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    
    def idempotency_check(self, f):
        """Ensure idempotent operations for bonus processing"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            idempotency_key = request.headers.get('X-Idempotency-Key')
            
            if not idempotency_key:
                return jsonify({"error": "Idempotency key required"}), 400
            
            # Check if this operation was already processed
            existing = self.redis.get(f"idempotency:{idempotency_key}")
            if existing:
                return jsonify({
                    "status": "already_processed",
                    "original_result": existing
                }), 200
            
            # Store the key to prevent duplicate processing
            self.redis.setex(
                f"idempotency:{idempotency_key}",
                timedelta(hours=24),
                "processing"
            )
            
            response = f(*args, **kwargs)
            
            # Update with actual result
            if response[1] == 200:  # Success
                self.redis.setex(
                    f"idempotency:{idempotency_key}",
                    timedelta(hours=24),
                    response[0].get_data(as_text=True)
                )
            
            return response
        return decorated_function

# Initialize middleware
security_middleware = BonusSecurityMiddleware()