import os
import threading
from flask import render_template, url_for, redirect, flash, request, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from app.models import User, ChatHistory, Document
from app.forms import RegisterForm, LoginForm, ResetPasswordForm, UpdatePasswordForm
from app.utils import initialize_retrievers, extract_text_from_pdf, check_for_new_files, initialize_chroma
from datetime import datetime, timezone
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import secrets
from app import app, db, bcrypt, login_manager, mail
from flask_mail import Message
from itsdangerous.serializer import Serializer
from itsdangerous.exc import BadSignature
import logging
from bson.objectid import ObjectId

# Load environment variables from .env file
load_dotenv()

# Retrieve the CLIENT_ID and CLIENT_SECRET 
# for login through google
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

# Create uploads folder if it doesn't exist
# for saving the uploaded files
UPLOAD_FOLDER = './uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize retrievers for document processing
rag_chain, retriever = initialize_retrievers()

# Global variable for processing status
processing_status = {'status': 'complete'}

# Generate a signed token for the given email address
def generate_token(email):
    serializer = Serializer(app.config['SECRET_KEY'], salt=app.config['SECURITY_PASSWORD_SALT'])
    return serializer.dumps(email)

# Verify a signed token and extract the email address
def verify_token(token, expiration=600):
    serializer = Serializer(app.config['SECRET_KEY'], salt=app.config['SECURITY_PASSWORD_SALT'])
    try:
        email = serializer.loads(token, max_age=expiration)
    except BadSignature:
        return False
    return email

# Send an email using Flask-Mail for reseting the password
def send_email(to, subject, template, **kwargs):
    msg = Message(subject, recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    mail.send(msg)

# Load user from user ID
@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    return User.from_mongo(user_data) if user_data else None

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(
            email=form.email.data,
            username=form.username.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        new_user.set_password(form.password.data)
        new_user.save()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_user(form.email_or_username.data)
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('post_login'))
        else:
            flash('Login Unsuccessful. Please check email/username and password', 'danger')
    return render_template('login.html', form=form)

# Google login route
@app.route('/login/google')
def login_google():
    try:
        redirect_uri = url_for('authorize_google', _external=True)
        nonce = secrets.token_urlsafe()
        session['nonce'] = nonce
        return google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        return "Error occurred during login", 500

# Google authorization route
@app.route('/authorize/google')
def authorize_google():
    try:
        # authorization code for an access token
        token = google.authorize_access_token()
        userinfo = google.parse_id_token(token, nonce=session['nonce'])

        # If the user information not retrieved, flash an error message and redirects to login page
        if not userinfo:
            flash('Failed to log in with Google.', 'danger')
            return redirect(url_for('login'))

        # Retrieve the user from the database using the email from userinfo
        user = User.get_user(userinfo['email'])

        # If the user does not exist in db, creates a new user with the information from Google
        if not user:
            user = User(
                username=userinfo['email'],
                email=userinfo['email'],
                first_name=userinfo.get('given_name', ''),
                last_name=userinfo.get('family_name', '')
            )
            user.save()
        
        # If the user exists, set the password_hash to None (since Google login does not use a password)
        else:
            user.password_hash = None
            user.save()

        login_user(user)
        flash('Login successful!', 'success')
        return redirect(url_for('post_login'))
    except Exception as e:
        app.logger.error(f"Error during authorization: {str(e)}")
        flash('An error occurred during Google login. Please try again.', 'danger')
        return redirect(url_for('login'))

# Password reset route
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.get_user(form.email.data)
        if user:
            token = generate_token(user.email)
            reset_url = url_for('reset_with_token', token=token, _external=True)
            try:
                send_email(user.email, 'Password Reset Requested', 'email/reset_password', reset_url=reset_url)
                flash('Password reset link has been sent to your email.', 'info')
            except Exception as e:
                app.logger.error(f"Error sending email: {e}")
                flash('An error occurred while sending the reset email. Please try again later.', 'danger')
            return redirect(url_for('login'))
        else:
            flash('Email not found', 'danger')
            return redirect(url_for('reset_password'))
    return render_template('reset_password.html', form=form)

# Password reset with token route
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_with_token(token):

    # Verifies the token and extract the email address
    email = verify_token(token)
    
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('reset_password'))
    
    # If the form is valid and submitted, update the user's password
    form = UpdatePasswordForm()
    if form.validate_on_submit():
        user = User.get_user(email)
        if user:
            user.set_password(form.password.data)  # Use set_password method to ensure correct hashing
            user.save()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('login'))
    
    return render_template('update_password.html', form=form, token=token)

# Post-login route
@app.route('/post_login')
@login_required
def post_login():
    
    # Retrieve the documents uploaded by the current logged-in user
    # if we want restrict the user to go to chat page
    user_documents = list(db.documents.find({'owner_email': current_user.email}))
    return render_template('post_login.html', user_documents=user_documents)

# Upload route
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Get the list of uploaded files
        files = request.files.getlist('file')
        new_files = []
        for file in files:
            # Check if the file is a PDF
            if file and file.filename.endswith('.pdf'):
                # Checks new files and adds them to the new files
                new_files.extend(check_for_new_files(UPLOAD_FOLDER, file, current_user.email))
        
        # If there are new files need to be processed
        if new_files:
            def process_files():
                global retriever
                retriever = initialize_chroma(UPLOAD_FOLDER, new_files)
                processing_status['status'] = 'complete'  # Update the processing status when done

            # Starts the file processing in a separate thread
            processing_thread = threading.Thread(target=process_files)
            processing_thread.start()

            # Sets the processing status
            processing_status['status'] = 'processing'
            return redirect(url_for('loading'))  # Redirect to the loading page
        else:
            # If no new files were uploaded or already existed
            flash('No new files uploaded or files already exist', 'info')
        
        return redirect(url_for('chat'))

    # GET request to fetch all the documents from the database for displaying in the "Previously Uploaded Documents" section
    user_documents = db.documents.find()
    return render_template('upload.html', documents=user_documents)

# Loading page route for processing the file
@app.route('/loading')
@login_required
def loading():
    return render_template('loading.html')

# Processing status route to check the status of file processing
@app.route('/processing_status')
@login_required
def processing_status_route():
    status = processing_status['status']
    return {'status': status}       # Return the status as a JSON response

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# chat route
@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    global retriever  # Ensure retriever is used globally
    chat_history = list(db.chat_histories.find({'owner_email': current_user.email}))  # Retrieve chat history for the current user

    if request.method == 'POST':
        query = request.form['query']   # Get the user query from the form
        formatted_history = [
            {"role": "user", "content": msg['user_input']} if 'user_input' in msg else {"role": "assistant", "content": msg['ai_response']}
            for msg in chat_history
        ]
        logger.info(f"User query: {query}")
        logger.info(f"Chat history: {formatted_history}")
        try:
             # Invoke the rag_chain
            result = rag_chain.invoke({"input": query, "chat_history": formatted_history})
            ai_response = result.get('answer', "No response from AI.")
            logger.info(f"AI response: {ai_response}")
        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            ai_response = "An error occurred during retrieval."

        # Save the new chat interaction to the database
        new_chat = ChatHistory(user_input=query, ai_response=ai_response, owner_email=current_user.email)
        new_chat.save()
        chat_history.append(new_chat)

        return jsonify(user_input=query, ai_response=ai_response)  # Return response as JSON

    return render_template('chat.html', chat_history=chat_history)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# List users route only for admin
@app.route('/users')
@login_required
def list_users():
    if not current_user.is_admin:
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('home'))
    
    users = list(db.users.find())
    return render_template('users.html', users=users)