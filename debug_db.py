import os
from dotenv import load_dotenv

# Load .env
load_dotenv()  # <-- this must be called BEFORE reading env variables

DATABASE_URL = os.getenv("DATABASE_URL")
print("Raw DATABASE_URL:", DATABASE_URL)

# Only replace if DATABASE_URL is not None
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///instance/fincash.db"  # fallback

print("Final DATABASE_URL used for engine:", DATABASE_URL)

