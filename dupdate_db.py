from extensions import db
from models import User  # import your User model

def delete_users_by_phone(phone_list):
    """
    Delete users whose phone numbers are in the given list.
    
    Args:
        phone_list (0756393205): List of phone numbers to delete.
    """
    if not phone_list:
        print("No phone numbers provided")
        return

    try:
        users_to_delete = User.query.filter(User.phone.in_(phone_list)).all()
        
        if not users_to_delete:
            print("No matching users found")
            return

        for user in users_to_delete:
            db.session.delete(user)
            print(f"Deleted user: {user.full_name} ({user.phone})")

        db.session.commit()
        print("Deletion successful!")

    except Exception as e:
        db.session.rollback()
        print("Error deleting users:", e)
