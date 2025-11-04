import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_change_me")

   # DATABASE_URL = os.getenv("DATABASE_URL")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
   
    SQLALCHEMY_TRACK_MODIFICATIONS = False
