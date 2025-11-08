import os
from flask import Flask, render_template, session, g, jsonify
from config import Config
from models import User
from flask_login import LoginManager
from flask_migrate import Migrate
from extensions import db

# --------------------------------------------------------------------------------------------------------
#       Global instances
# --------------------------------------------------------------------------------------------------------
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    if app.config.get("DEBUG", False):
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.jinja_env.auto_reload = True
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        app.config['DEBUG'] = True

    @app.route("/debug/routes", methods=["GET"])
    def debug_routes():
          """
          Returns a JSON list of all registered routes with their methods.
           Useful for debugging 404s and endpoint registration issues.
          """
          routes = []
          for rule in app.url_map.iter_rules():
            routes.append({
               "endpoint": rule.endpoint,
            "url": rule.rule,
            "methods": list(rule.methods)
         })
          return jsonify(routes), 200
     
    
    # ------------------------------------------------------------------------------------------
    # Basic logging setup
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
    
    
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

        print("Using DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])

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
        from blueprints.payment_webhooks import bp as payment_webhooks_bp 
        from blueprints.payment_callback import bp as payment_callbacks_bp 

        app.register_blueprint(auth_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(payment_bp)
        app.register_blueprint(payment_webhooks_bp)
        app.register_blueprint(payment_callbacks_bp)

    register_blueprints(app)

    # ----------------------
    # Global before_request
    # ----------------------
    @app.before_request
    def load_logged_in_user():
        g.user = None
        user_id = session.get("user_id")
        if user_id:
            g.user = User.query.get(user_id)

    # ----------------------
    # Basic routes
    # ----------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}, 200
    
     #----------------------------------------------------------------------------------------------------------
    @app.route("/debug/config")
    def debug_config():
        """⚠️ Development-only route to inspect loaded configuration."""
        safe_keys = [
            "FLASK_ENV",
            "DEBUG",
            "SQLALCHEMY_DATABASE_URI",
            "MARZ_BASE_URL",
            "APP_BASE_URL"
        ]

        config_snapshot = {key: app.config.get(key) for key in safe_keys}

        # Add a small check to see if sensitive keys are loaded
        secrets_loaded = {
            "SECRET_KEY": bool(app.config.get("SECRET_KEY")),
            "MARZ_API_KEY": bool(app.config.get("MARZ_API_KEY")),
            "MARZ_API_SECRET": bool(app.config.get("MARZ_API_SECRET")),
        }

        return {
            "config": config_snapshot,
            "secrets_loaded": secrets_loaded,
            "environment": dict(
                FLASK_ENV=os.getenv("FLASK_ENV"),
                DATABASE_URL=os.getenv("DATABASE_URL"),
            )
        }, 200
    #----------------------------------------------------------------------------------------------------------------------------------------


    return app

# ----------------------
# Flask-Login user_loader
# ----------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------
# WSGI entrypoint - DO NOT OVERWRITE THIS!
# ----------------------
app = create_app()

# ----------------------
# Local development
# ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = app.config.get("DEBUG", False)
    print(f"🚀 Starting Flask app on port {port}...")
    app.run(debug=True, host="0.0.0.0", port=port)