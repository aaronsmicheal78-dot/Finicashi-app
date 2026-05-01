
import gevent.monkey
gevent.monkey.patch_all()
from blueprints.payments import logger
import os
from flask import Flask, render_template, session, g, jsonify
from config import Config
from models import User
from flask_login import LoginManager
from flask_migrate import Migrate
from extensions import db
from sqlalchemy import text
from datetime import datetime
from flask_cors import CORS

login_manager = LoginManager()
migrate = Migrate()

def create_app():
   # force_ipv4_dns()
    app = Flask(__name__)
    
    app.config.from_object(Config)
    if app.config.get("DEBUG", False):
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.jinja_env.auto_reload = True
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        app.config['DEBUG'] = True
        app.config["PROPAGATE_EXCEPTIONS"] = True
        app.config["DEBUG"] = False

    if not app.debug:
        app.config.update(
            SESSION_COOKIE_SECURE=True,        
            SESSION_COOKIE_HTTPONLY=True,
            SESSION_COOKIE_SAMESITE="None",   
            REMEMBER_COOKIE_SECURE=True,
            REMEMBER_COOKIE_HTTPONLY=True,
            REMEMBER_COOKIE_SAMESITE="None",
        )

    CORS(app, supports_credentials=True)

        # ------------------------------------------------------------------------------------------
    # SIMPLIFIED LOGGING - No rotation to avoid permission errors
    # ------------------------------------------------------------------------------------------
    import logging
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Use simple FileHandler instead of RotatingFileHandler
    file_handler = logging.FileHandler('logs/app.log', mode='a', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Clear any existing handlers and add our simple handler
    app.logger.handlers.clear()
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False  # Prevent duplicate logs
    
    # Also add console handler for development
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
    
    # ----------------------------------------------------------------------------------------------------------------------------------
    # DATABASE URI Fix
    # --------------------------------------------------------------------------------------------------------------------------------------------
    DATABASE_URI = app.config.get("SQLALCHEMY_DATABASE_URI")
    
    if not DATABASE_URI:
        basedir = os.path.abspath(os.path.dirname(__file__))
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'fincash.db')}"
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI 

    if DATABASE_URI.startswith("postgres://"):
        DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql+pg8000://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
    
    # --------------------------------------------------------------------------------------------------------------------------
    # Initialize extensions
    # ----------------------------------------------------------------------------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ------------------------------------------------------------------------------------------------------------------------
    # Register blueprints
    # -----------------------------------------------------------------------------------------------------------------------
    def register_blueprints(app):
        from blueprints.auth import bp as auth_bp
        from blueprints.profile import bp as profile_bp
        from blueprints.admin import admin_bp as admin_bp
        from blueprints.payments import bp as payment_bp
        from activity import activity_bp as activity_bp
        from notification.notification import notification_bp
       
        app.register_blueprint(auth_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(payment_bp)
        app.register_blueprint(activity_bp)
        app.register_blueprint(notification_bp)
     
    register_blueprints(app) 
    # ------------------------------------------------------------------------------------------------------------------------
    # Flask-Login user_loader - MOVED INSIDE create_app to avoid circular imports
    # ------------------------------------------------------------------------------------------------------------------------
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id)) 
    # ----------------------
    # Global before_request
    # ----------------------
    @app.before_request
    def load_logged_in_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = User.query.get(user_id)
    @app.route("/api/whoami")
    def whoami():
        user_id = session.get("user_id")
        return jsonify({"user_id": user_id})
    
    @app.route('/policy')
    def policy():
        return render_template('partials/policy.html')

    # ----------------------
    # Basic routes
    # ----------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200
    
    @app.after_request
    def cleanup_transactions(response):
        """Ensure no open transactions after each request"""
        try:
            if db.session.is_active:
                # Rollback any uncommitted transactions
                db.session.rollback()
                # Or commit if you want to persist
                # db.session.commit()
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            db.session.rollback()
        return response

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Always remove session at the end of request"""
        db.session.remove()
 
    return app

# ----------------------
# Create app instance
# ----------------------
app = create_app()

# ----------------------
# Local development
# ----------------------
if __name__ == "__main__":
    app.config.update(
        DEBUG=True,
        ENV="development",
        PROPAGATE_EXCEPTIONS=True
    )
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

#=======================================================================================================
#------------------------THE END OF APP----------------------------------------------------------------
#==========================================================================================================