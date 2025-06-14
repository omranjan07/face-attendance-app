# create_admin.py
from app import app
from models import db, User

with app.app_context():
    admin = User(username='admin')
    admin.set_password('admin123')
    admin.role = 'admin'
    db.session.add(admin)
    db.session.commit()
    print("Admin created.")
