from app import app, db
from app.models import User, Document, ChatHistory

with app.app_context():
    # Find the user by username
    user_to_delete = User.query.filter_by(username='cerebra1234').first()
    
    if user_to_delete:
        # Delete related documents
        Document.query.filter_by(user_id=user_to_delete.id).delete()
        
        # Delete related chat history
        ChatHistory.query.filter_by(user_id=user_to_delete.id).delete()
        
        # Delete the user
        db.session.delete(user_to_delete)
        db.session.commit()
        print(f"User {user_to_delete.username} and related data have been deleted successfully.")
    else:
        print("User not found.")