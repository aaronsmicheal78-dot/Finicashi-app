# #=======================================================================================================
# # Extensions for the Finicashi Flask Application
# #=======================================================================================================
# import os
# import logging
# from logging.handlers import RotatingFileHandler
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# # -------------------------------------------------------------------------------------
# # Flask Extensions
# # -------------------------------------------------------------------------------------
# db = SQLAlchemy()
# login_manager = LoginManager()

# # -------------------------------------------------------------------------------------
# # SQLAlchemy Core Setup (for raw queries)
# # -------------------------------------------------------------------------------------
# Base = declarative_base()
# engine = None            # Will be initialized in init_extensions()
# SessionLocal = None      # Will be initialized in init_extensions()

# # -------------------------------------------------------------------------------------
# # Logger setup
# # -------------------------------------------------------------------------------------
# def setup_logger(name):
#     """Set up a logger with file rotation"""
#     if not os.path.exists("logs"):
#         os.makedirs("logs")

#     logger = logging.getLogger(name)
#     logger.setLevel(logging.INFO)

#     file_handler = RotatingFileHandler(
#         f"logs/{name}.log",
#         maxBytes=10240,
#         backupCount=10
#     )
#     file_handler.setFormatter(logging.Formatter(
#         "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
#     ))
#     file_handler.setLevel(logging.INFO)
#     logger.addHandler(file_handler)
#     return logger

# logger = setup_logger("app")
# payments_logger = setup_logger("payments")

# # -------------------------------------------------------------------------------------
# # Initialization helper
# # -------------------------------------------------------------------------------------
# def init_extensions(app):
#     """Initialize Flask extensions and SQLAlchemy engine/session"""
#     global engine, SessionLocal

    
#     db.init_app(app)
#     login_manager.init_app(app)

   
#     db_uri = app.config.get("SQLALCHEMY_DATABASE_URI")

#     if db_uri and db_uri.startswith("postgres://"):
        
#         db_uri = db_uri.replace("postgres://", "postgresql+pg8000://", 1)
#         app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

   
#     engine = create_engine(db_uri, pool_pre_ping=True)
#     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#     app.logger.info(f"Database initialized: {db_uri}")
#     return app


from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


db = SQLAlchemy()
login_manager = LoginManager()



def init_extensions(app):
    """Initialize Flask extensions"""
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    
    return app