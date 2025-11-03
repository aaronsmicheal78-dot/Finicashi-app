import os

basedir = os.path.abspath(os.path.dirname(__file__))
instance_dir = os.path.join(basedir, "instance")
os.makedirs(instance_dir, exist_ok=True)

class Config:
    # Flask settings
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

    # Marz API settings (if used)
    MARZ_BASE_URL = os.getenv("MARZ_BASE_URL", "https://wallet.wearemarz.com/api/v1")
    MARZ_BASIC_TOKEN = os.getenv("MARZ_BASIC_TOKEN")
    MARZ_ACCOUNT_ID = os.getenv("MARZ_ACCOUNT_ID")
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    WEBHOOK_SIGNATURE_HEADER = os.getenv("WEBHOOK_SIGNATURE_HEADER", "Marz-Signature")
    WEBHOOK_TIMESTAMP_HEADER = os.getenv("WEBHOOK_TIMESTAMP_HEADER", "Marz-Timestamp")
    REQUIRE_WEBHOOK_SIGNATURE = True

    # DATABASE
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Fix Render's postgres:// URL to use pg8000
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # fallback for local dev
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_dir, 'fincash.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
