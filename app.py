import os
from flask import Flask, render_template, session, g
from config import Config
from extensions import db
from models import User
from blueprints.auth import bp as auth_bp
from blueprints.profile import bp as profile_bp
from blueprints.admin import admin_bp as admin_bp
from flask_login import LoginManager
from flask_migrate import Migrate

# ----------------------
# Global instances
# ----------------------
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Load config from Config class
    app.config.from_object(Config)

    # ----------------------
    # DATABASE URI Fix
    # ----------------------
    # Ensure DATABASE_URL exists
    database_url = app.config.get("SQLALCHEMY_DATABASE_URI")
    # if database_url is None:
    #     # Fallback to SQLite locally
    #     basedir = os.path.abspath(os.path.dirname(__file__))
    #     instance_dir = os.path.join(basedir, "instance")
    #     os.makedirs(instance_dir, exist_ok=True)
    #     database_url = f"sqlite:///{os.path.join(instance_dir, 'fincash.db')}"
    #     app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    # Render PostgreSQL fix: pg8000 instead of psycopg2
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+pg8000://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    print("Using DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])

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
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)

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
# WSGI entrypoint
# ----------------------
app = create_app()

# ----------------------
# Local development
# ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = app.config.get("DEBUG", False)
    app.run(debug=debug_mode, host="0.0.0.0", port=port)















































# import os
# from flask import Flask, render_template, session, g
# from config import Config
# from extensions import db
# from models import User
# from blueprints.auth import bp as auth_bp
# from blueprints.profile import bp as profile_bp
# from blueprints.admin import admin_bp as admin_bp
# from flask_login import LoginManager
# from flask_migrate import Migrate


# login_manager = LoginManager()  # create a global instance
# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)
#     migrate = Migrate(app, db)
#     print("Using DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])


#     # Initialize extensions
#     db.init_app(app)
   
#     # Register blueprints
#     app.register_blueprint(auth_bp)
#     app.register_blueprint(profile_bp)
#     app.register_blueprint(admin_bp)

#     login_manager.init_app(app)
#     login_manager.login_view = "auth.login" 

#     # ----------------------
#     # Global before_request
#     # ----------------------
#     @app.before_request
#     def load_logged_in_user():
#         g.user = None
#         user_id = session.get("user_id")
#         if user_id:
#             g.user = User.query.get(user_id)

#     # ----------------------
#     # Basic routes
#    # ----------------------
#     @app.route("/")
#     def home():
#         return render_template("index.html")


#     @app.route("/healthz")
#     def healthz():
#         return {"status": "ok"}, 200
    

#     return app
# @login_manager.user_loader
# def load_user(user_id):
#     return User.query.get(int(user_id))
# # ======================
# # Create app for Gunicorn / WSGI
# # ======================
# app = create_app()  # THIS is the fully configured app

# # for rule in app.url_map.iter_rules():
# #     print("🛣️ Route:", rule)
  
# # ======================
# # Local dev
# # ======================
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(debug=True, host="0.0.0.0", port=port)
