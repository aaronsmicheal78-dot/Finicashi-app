"""
Safely migrate all data from SQLite (fincash.db)
to PostgreSQL (Render-hosted database).
"""

import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# === STEP 1: Configure your database URLs ===

# Path to your local SQLite DB
sqlite_path = "instance/fincash.db"
sqlite_url = f"sqlite:///{sqlite_path}"

# Your Render PostgreSQL connection string (replace with your actual Render details)
# Example format:
# postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE
postgres_url = "postgresql://finicashi_db_user:8OCk4GypHpsh3KQH3oPq7bBSVylwVD96@dpg-d433kjmuk2gs738mgej0-a.oregon-postgres.render.com/finicashi_db"

# === STEP 2: Set up SQLAlchemy engines ===
sqlite_engine = create_engine(sqlite_url)
postgres_engine = create_engine(postgres_url)

sqlite_meta = MetaData(bind=sqlite_engine)
postgres_meta = MetaData(bind=postgres_engine)

# Reflect all existing tables in SQLite
sqlite_meta.reflect()

# Create same tables in Postgres if not existing
sqlite_meta.create_all(postgres_engine)

# === STEP 3: Set up sessions ===
SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

sqlite_session = SQLiteSession()
postgres_session = PostgresSession()

# === STEP 4: Migrate data table by table ===
print("🚀 Starting migration...")

for table_name in sqlite_meta.tables.keys():
    table = sqlite_meta.tables[table_name]
    print(f"🔹 Migrating table: {table_name}")

    rows = sqlite_session.execute(table.select()).fetchall()

    if not rows:
        print("  ⚠️ No rows found, skipping.")
        continue

    try:
        postgres_session.execute(table.insert(), [dict(row._mapping) for row in rows])
        postgres_session.commit()
        print(f"  ✅ Migrated {len(rows)} rows.")
    except IntegrityError as e:
        postgres_session.rollback()
        print(f"  ⚠️ Skipped duplicates or constraint errors in {table_name}: {e.orig}")

print("🎉 Migration completed successfully!")

# === STEP 5: Close sessions ===
sqlite_session.close()
postgres_session.close()
