import os
from flask import Flask, render_template, session, g
from config import Config
from extensions import db
from models import User
from flask_login import LoginManager
from flask_migrate import Migrate

# ----------------------
# Global instances
# ----------------------
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Debug settings
    if app.config.get("DEBUG", False):
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.jinja_env.auto_reload = True
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        app.config['DEBUG'] = True
     
    

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
    
   
    # ----------------------
    # DATABASE URI Fix
    # ----------------------
    DATABASE_URI = app.config.get("SQLALCHEMY_DATABASE_URI")
    
    if not DATABASE_URI:
        basedir = os.path.abspath(os.path.dirname(__file__))
        instance_dir = os.path.join(basedir, "instance")
        os.makedirs(instance_dir, exist_ok=True)
        DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'fincash.db')}"
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI 

    # if DATABASE_URI.startswith("postgres://"):
    #     DATABASE_URI = DATABASE_URI.replace("postgres://", "postgresql+pg8000://", 1)
    #     app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI

    # print("Using DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])

    # ----------------------
    # Initialize extensions
    # ----------------------
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # ----------------------
    # Register blueprints
    # ----------------------
    def register_blueprints(app):
        from blueprints.auth import bp as auth_bp
        from blueprints.profile import bp as profile_bp
        from blueprints.admin import admin_bp as admin_bp
        from blueprints.payments import bp as payment_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(profile_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(payment_bp)

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