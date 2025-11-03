from app import create_app
from extensions import db

app = create_app()
with app.app_context():
    result = db.engine.execute("SELECT version();")
    print(result.fetchone())
