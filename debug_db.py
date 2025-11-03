import os
from sqlalchemy import create_engine
from config import Config

# Get the DATABASE_URL from your config
DATABASE_URL = Config.DATABASE_URL

print("Raw DATABASE_URL:", DATABASE_URL)

# Check if SQLAlchemy sees a postgres:// scheme anywhere
if DATABASE_URL.startswith("postgres://"):
    print("WARNING: Database URL still uses 'postgres://', will force pg8000")
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

print("Final DATABASE_URL used for engine:", DATABASE_URL)

try:
    # Try creating engine without initializing Flask
    engine = create_engine(DATABASE_URL)
    print("✅ Engine created successfully, pg8000 should be used.")
except Exception as e:
    print("❌ Engine creation failed:")
    print(e)

# Optional: check which dialect SQLAlchemy picked
from sqlalchemy.engine import url as sa_url
dialect_name = sa_url.make_url(DATABASE_URL).get_dialect().name
print("SQLAlchemy dialect detected:", dialect_name)
