from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, Email, EqualTo, ValidationError
from app.models import User
from app import db

# Register form for new users
class RegisterForm(FlaskForm):
    email = StringField(validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    first_name = StringField(validators=[InputRequired()], render_kw={"placeholder": "First Name"})
    last_name = StringField(validators=[InputRequired()], render_kw={"placeholder": "Last Name"})
    password = PasswordField(validators=[InputRequired(), Length(min=8)], render_kw={"placeholder": "Password"})
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('password')], render_kw={"placeholder": "Re-enter Password"})
    submit = SubmitField('Register')

    # validator to check if the username already exists in the database.
    def validate_username(self, username):
        user = User.get_user(username.data)
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    # validator to check if the email already exists in the database.
    def validate_email(self, email):
        user = User.get_user(email.data)
        if user:
            raise ValidationError('Email already exists. Please choose a different one.')

# login form for existing users.
class LoginForm(FlaskForm):
    email_or_username = StringField(validators=[InputRequired()], render_kw={"placeholder": "Email or Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=8)], render_kw={"placeholder": "Password"})
    submit = SubmitField('Login')

# form for requesting a password reset.
class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()], render_kw={"placeholder": "Email"})
    submit = SubmitField('Reset Password')

# form for updating the password after a password reset.
class UpdatePasswordForm(FlaskForm):
    password = PasswordField(validators=[InputRequired(), Length(min=8)], render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField(validators=[InputRequired(), EqualTo('password')], render_kw={"placeholder": "Confirm New Password"})
    submit = SubmitField('Update Password')