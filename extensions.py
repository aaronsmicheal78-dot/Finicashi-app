#
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager  # Add this import
# from flask_mail import Mail
# from flask_bcrypt import Bcrypt
from logging.handlers import RotatingFileHandler
import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()  # Add this line
# mail = Mail()
# bcrypt = Bcrypt()

# SQLAlchemy setup (if you're using raw SQLAlchemy alongside Flask-SQLAlchemy)
Base = declarative_base()
engine = create_engine('sqlite:///instance/fincash.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Logger setup
def setup_logger(name):
    """Set up a logger with file rotation"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    file_handler = RotatingFileHandler(
        f'logs/{name}.log', 
        maxBytes=10240, 
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    return logger

# Create loggers
logger = setup_logger('app')
payments_logger = setup_logger('payments')













































# #extensions.py - initialize shared extensions (DB, logging, migrations)
# import logging                                                   # core logging module
# from logging.handlers import RotatingFileHandler                 # for log rotation in prod
# from sqlalchemy import create_engine                              # low-level engine creator
# from sqlalchemy.orm import sessionmaker, declarative_base         # ORM base classe
# from config import Config                                        # load config values
# import os
# from flask_sqlalchemy import SQLAlchemy

# db = SQLAlchemy()  # ← THIS must exist


# Base = declarative_base()                                         # declarative base for models

# # Logging setup - production ready
# logger = logging.getLogger("medconnect_marz")                     # main logger for this app
# #logger.setLevel(getattr(logging, Config.LOG_LEVEL))               # set log level from config

# # Rotating file handler (keeps logs manageable) - adjust path in prod
# file_handler = RotatingFileHandler("medconnect_marz.log", maxBytes=10*1024*1024, backupCount=5)
# #file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))         # file handler level
# formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
# file_handler.setFormatter(formatter)                              # attach formatter to handler
# logger.addHandler(file_handler)                                   # attach file handler to logger

# # Also print to console for Docker logs / systemd journal
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(formatter)
# logger.addHandler(console_handler)


# class Config:
#     SECRET_KEY = os.environ.get("SECRET_KEY", "dev_key_change_me")
#     SQLALCHEMY_DATABASE_URI = os.environ.get(
#         "DATABASE_URL", "sqlite:///fincashitoday.db"
#     )
#SQLALCHEMY_TRACK_MODIFICATIONS = False

