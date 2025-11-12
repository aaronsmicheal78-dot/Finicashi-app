# fix_database.py
import os
import sys
from sqlalchemy import create_engine, text

# Direct database connection - no models, no app
DATABASE_URI = "postgresql+pg8000://finicashi_db_user:8OCk4GypHpsh3KQH3oPq7bBSVylwVD96@dpg-d433kjmuk2gs738mgej0-a.oregon-postgres.render.com/finicashi_db"

engine = create_engine(DATABASE_URI)

try:
    with engine.connect() as conn:
        # Add the missing column - use text() for SQL statements
        conn.execute(text("ALTER TABLE payments ADD COLUMN transaction_type VARCHAR(50)"))
        conn.commit()
    print("✅ Added transaction_type column to payments")
except Exception as e:
    print(f"❌ Error: {e}")