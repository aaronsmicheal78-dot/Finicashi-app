# ==========================================================================================================
# -------------- Configuration file for Finicashi Flask application ----------------------------------------
# ==========================================================================================================

import os
from dotenv import load_dotenv

if os.environ.get("FLASK_ENV") != "production":
    load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class for Flask app (used in all environments)."""

   
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

   
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'fincash.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

  
    MARZ_API_KEY = os.getenv("MARZ_API_KEY")
    MARZ_API_SECRET = os.getenv("MARZ_API_SECRET")
    MARZ_BASE_URL = os.getenv("MARZ_BASE_URL", "https://wallet.wearemarz.com/api/v1")
    MARZ_AUTH_HEADER = os.getenv("MARZ_AUTH_HEADER")

    
    APP_BASE_URL = os.getenv("APP_BASE_URL", "https://bedfast-kamron-nondeclivitous.ngrok-free.dev")
