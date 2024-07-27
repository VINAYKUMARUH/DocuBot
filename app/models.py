from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from pymongo import ASCENDING
from bson.objectid import ObjectId
from app import db

# User related data
class User(UserMixin):
    def __init__(self, email, username, first_name, last_name, password_hash=None, is_admin=False, _id=None):
        self.email = email
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.password_hash = password_hash
        self.is_admin = is_admin
        self._id = _id if _id else ObjectId()  # MongoDB ObjectId

    # password hashing
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    # check the user's password against the stored hash
    def check_password(self, password):
        if not self.password_hash:
            print(f"Password hash for user {self.email} is None or empty!")
            return False
        return check_password_hash(self.password_hash, password)

    # get the user's ID
    def get_id(self):
        return str(self._id)  

    # Static method to create a User object from MongoDB data
    @staticmethod
    def from_mongo(data):
        return User(
            email=data['email'],
            username=data['username'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            password_hash=data.get('password_hash', None),  # Use get to avoid KeyError
            is_admin=data.get('is_admin', False),
            _id=data['_id']
        )

    # Static method to get a user by email or username
    @staticmethod
    def get_user(email_or_username):
        user = db.users.find_one({'$or': [{'email': email_or_username}, {'username': email_or_username}]})
        if user:
            return User.from_mongo(user)
        return None

    # save the user to the database
    def save(self):
        db.users.update_one(
            {'_id': self._id},  # Use _id for identifying the document
            {'$set': self.__dict__},
            upsert=True
        )

# document related data
class Document:
    def __init__(self, filename, owner_email, upload_date=None):
        self.filename = filename
        self.upload_date = upload_date or datetime.now(timezone.utc)
        self.owner_email = owner_email

    # Static method to create a Document object from MongoDB data
    @staticmethod
    def from_mongo(data):
        return Document(
            filename=data['filename'],
            owner_email=data['owner_email'],
            upload_date=data['upload_date']
        )
    
    # Static method to check if a document exists in the database by filename
    @staticmethod
    def document_exists(filename):
        return db.documents.find_one({'filename': filename}) is not None

    # Method to save the document to the database
    def save(self):
        db.documents.update_one(
            {'filename': self.filename},
            {'$set': self.__dict__},
            upsert=True
        )

# chat history data
class ChatHistory:
    def __init__(self, user_input, ai_response, owner_email, timestamp=None):
        self.user_input = user_input
        self.ai_response = ai_response
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.owner_email = owner_email

    # Static method to create a ChatHistory object from MongoDB data
    @staticmethod
    def from_mongo(data):
        return ChatHistory(
            user_input=data['user_input'],
            ai_response=data['ai_response'],
            owner_email=data['owner_email'],
            timestamp=data['timestamp']
        )

    # save the chat history to the database
    def save(self):
        db.chat_histories.update_one(
            {'user_input': self.user_input, 'owner_email': self.owner_email},
            {'$set': self.__dict__},
            upsert=True
        )

# for unique constraints on email and username fields
db.users.create_index([('email', ASCENDING)], unique=True)
db.users.create_index([('username', ASCENDING)], unique=True)