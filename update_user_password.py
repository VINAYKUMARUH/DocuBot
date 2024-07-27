from app import app, db, bcrypt
from app.models import User

with app.app_context():
    # Find the user by username
    user_to_update = User.query.filter_by(username='qwerty').first()
    
    if user_to_update:
        print("User found. Updating the password.")
        # Update the user's password
        new_password = 'qwertyui'  # The new password
        user_to_update.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        db.session.commit()
        print(f"Password for user {user_to_update.username} has been updated.")
    else:
        print("User not found.")