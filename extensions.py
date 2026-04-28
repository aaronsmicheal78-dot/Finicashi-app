# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Initialize rate limiter
# Uses Redis in production, memory in development
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=["200 per day", "50 per hour"],  # Global fallback limits
    storage_uri=os.getenv("REDIS_URL", "memory://"),  # Redis or memory
    strategy=os.getenv("RATE_LIMIT_STRATEGY", "fixed-window"),  # or "moving-window"
    application_limits=[
        "1000 per day",  # Higher limit for API clients with API key
    ],
    headers_enabled=True,  # Return rate limit headers in responses
    retry_after="http-date",  # Format Retry-After header as HTTP date
)


def init_extensions(app):
    """Initialize Flask extensions with app context"""
    db.init_app(app)
    
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"  # Security: protect session from hijacking
    
    # Initialize limiter with app
    limiter.init_app(app)
    
    return app
