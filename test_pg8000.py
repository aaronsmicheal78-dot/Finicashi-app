import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Load DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug: print the raw URL
print("Raw DATABASE_URL:", DATABASE_URL)

# Make sure pg8000 is used
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

print("Final DATABASE_URL used for engine:", DATABASE_URL)

# Create engine
try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT NOW()"))
        now = result.fetchone()[0]
        print("✅ Connection successful! Database time:", now)
except Exception as e:
    print("❌ Connection failed:", e)
