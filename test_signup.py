# manage.py
import os
from extensions import db
from flask_migrate import Migrate
from app import create_app

# Create Flask app
app = create_app()

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Optional: for shell context
@app.shell_context_processor
def make_shell_context():
    from models import User  # import your models here
    return {"db": db, "User": User}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
