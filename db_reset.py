from app import app
from extensions import db

with app.app_context():
    db.drop_all()
    print("DROPING TABLES")
    print("All DB tables dropped sucessfully")
    print("Creating Fresh DB tables")
    db.create_all()
    print("DB tables created sucessfully")
   