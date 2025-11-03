import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Render Postgres fix for pg8000
    #if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
      #  DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

    # Final URI
       # SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{os.path.join(basedir, 'instance', 'fincash.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
