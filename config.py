import os
from dotenv import load_dotenv

# Load .env only in local development
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, "instance")
os.makedirs(instance_dir, exist_ok=True)  # ensure instance folder exists

class Config:
    # General environment
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    # Secret key
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

    # Marz API configuration
    MARZ_BASE_URL = os.getenv("MARZ_BASE_URL", "https://wallet.wearemarz.com/api/v1")
    MARZ_BASIC_TOKEN = os.getenv("MARZ_BASIC_TOKEN")
    MARZ_ACCOUNT_ID = os.getenv("MARZ_ACCOUNT_ID")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    WEBHOOK_SIGNATURE_HEADER = os.getenv("WEBHOOK_SIGNATURE_HEADER", "Marz-Signature")
    WEBHOOK_TIMESTAMP_HEADER = os.getenv("WEBHOOK_TIMESTAMP_HEADER", "Marz-Timestamp")
    REQUIRE_WEBHOOK_SIGNATURE = True

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # use instance DB if no DATABASE_URL
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'fincash.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
