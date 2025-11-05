# make_admin.py
# Usage: python make_admin.py

from werkzeug.security import generate_password_hash
from sqlalchemy.exc import IntegrityError

# adjust these imports to match your project layout if needed
from app import create_app
from models import db, User

PHONE = "0789621299"
DEFAULT_EMAIL = "aaronssamara@gmail.com"
DEFAULT_PASSWORD = "admin123"  # only used if you create the user — change after creation

def make_admin():
    app = create_app()
    with app.app_context():
        # Try to find existing user by phone
        user = User.query.filter_by(phone=PHONE).first()

        if user:
            print(f"Found user id={user.id}, phone={user.phone}. Promoting to admin...")
        else:
            # Create a new user if none exists (adjust fields to match your User model)
            print(f"No user with phone {PHONE} found — creating a new user.")
            try:
                user = User(
                    phone=PHONE,
                    email=DEFAULT_EMAIL,            # change or remove if your model differs
                    password_hash=generate_password_hash(DEFAULT_PASSWORD),
                    is_admin=False                  # set False first, we'll promote below
                )
                db.session.add(user)
                db.session.commit()
                print(f"Created user id={user.id} with phone={PHONE}.")
            except IntegrityError as e:
                db.session.rollback()
                print("IntegrityError while creating user (maybe phone already exists):", e)
                user = User.query.filter_by(phone=PHONE).first()
                if not user:
                    raise RuntimeError("Failed to create or find user after IntegrityError.") from e

        # Now promote to admin (adapt attribute name to your model, e.g. is_admin or role)
        # If your model uses roles instead, set user.role = 'admin' accordingly.
        if getattr(user, "is_admin", None) is not None:
            user.is_admin = True
        else:
            # fallback: if model has a 'role' string field
            if hasattr(user, "role"):
                user.role = "admin"
            else:
                raise AttributeError(
                    "User model has no 'is_admin' boolean and no 'role' field. "
                    "Update this script to match your model."
                )

        db.session.add(user)
        db.session.commit()
        print(f"User (id={user.id}, phone={PHONE}) is now admin.")

if __name__ == "__main__":
    make_admin()
