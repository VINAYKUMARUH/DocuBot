from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# MongoDB connection URI
uri = os.getenv('MONGO_URI')

# Connect to MongoDB
client = MongoClient(uri)

# Get the database
db_name = os.getenv('DB_NAME')
db = client[db_name]

# Define the admin user details
admin_email = 'cerebra1234@gmail.com'
admin_username = 'cerebra1234'
admin_first_name = 'Admin'
admin_last_name = 'User'
admin_password = 'cerebra1234'  

# Check if the admin user already exists
existing_user = db.users.find_one({'email': admin_email})
if existing_user:
    print("Admin user already exists.")
else:
    # Create a new admin user
    admin_user = {
        'email': admin_email,
        'username': admin_username,
        'first_name': admin_first_name,
        'last_name': admin_last_name,
        'password_hash': generate_password_hash(admin_password, method='pbkdf2:sha256'),
        'is_admin': True
    }
    db.users.insert_one(admin_user)
    print("Admin user created successfully.")