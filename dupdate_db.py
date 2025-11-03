# dupdate_db.py
import os
import sqlite3

# 🔧 CORRECT PATH: 'instance/fincash.db' relative to THIS script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "instance", "fincash.db")

def add_role_column_to_users():
    """Adds 'role' column to 'users' table if missing."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}\n"
                                "Please run your app first to create the database.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if 'role' column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "role" in columns:
            print("✅ Column 'role' already exists.")
            return

        # Add column
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT")
        print("➕ Added 'role' column.")

        # Backfill existing users
        cursor.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
        updated = cursor.rowcount
        print(f"🔄 Set role='user' for {updated} existing user(s).")

        conn.commit()
        print("✅ Database updated successfully!")

    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_role_column_to_users()