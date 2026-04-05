from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField, PasswordField, EmailField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import DataRequired, Length, Email, NumberRange, URL, Optional


class CommentForm(FlaskForm):
    comment = TextAreaField("Write a comment below", validators=[DataRequired()],
                             render_kw={"placeholder": "Enter your thoughts", "class": "form-control"})
    submit = SubmitField('Post', render_kw={"class": "mb-3"})

class RegisterForm(FlaskForm):
    first_name = StringField('First Name*', validators=[DataRequired()], render_kw={"placeholder": "First name", "class": "form-control"})
    last_name = StringField('Last Name*', validators=[DataRequired()], render_kw={"placeholder": "Last name", "class": "form-control"})
    email = EmailField('Email*', validators=[Email(), DataRequired()], render_kw={"placeholder": "Email", "class": "form-control"})
    password = PasswordField('Password*', validators=[DataRequired()], render_kw={"placeholder": "Password", "class": "form-control mb-4"})
    submit = SubmitField('Sign Up', render_kw={"class": "mb-4"})


class LoginForm(FlaskForm):
    email = EmailField('Email*', validators=[Email(), DataRequired()], render_kw={"placeholder": "Email", "class": "form-control"})
    password = PasswordField('Password*', validators=[DataRequired()], render_kw={"placeholder": "Password", "class": "form-control mb-4"})
    submit = SubmitField('Login', render_kw={"class": "mb-4"})


class ContactForm(FlaskForm):
    name = EmailField('Full Name*', validators=[DataRequired()],
                       render_kw={"placeholder": "Full Name", "class": "form-control"})
    email = EmailField('Email*', validators=[Email(), DataRequired()],
                       render_kw={"placeholder": "Email", "class": "form-control"})
    message = TextAreaField('Message*', validators=[DataRequired()],
                             render_kw={"placeholder": "Enter your message", "class": "form-control mb-4"})
    submit = SubmitField('Send', render_kw={"class": "mb-4"})


class CreatePostForm(FlaskForm):
    title = StringField('Title*', validators=[DataRequired()], render_kw={"placeholder": "Title", "class": "form-control"})
    subtitle = StringField('Subtitle*', validators=[DataRequired()], render_kw={"placeholder": "Subtitle", "class": "form-control"})
    location = StringField('Destination ✈️ (e.g. City, Prov/State, Country)*', validators=[DataRequired()], render_kw={"placeholder": "Where", "class": "form-control"})
    num_times_visited = IntegerField('How many times have you visited?*', validators=[NumberRange(min=1, message="Value must be above 0."), DataRequired()], render_kw={"placeholder": "How often", "class": "form-control"})
    body = TextAreaField('Body*', validators=[DataRequired()], render_kw={"placeholder": "Tell us about it", "class": "form-control"})
    visit_again = BooleanField('Would you visit again?')
    rating = SelectField('How many stars?', choices=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"], validators=[DataRequired()], render_kw={"class": "form-control"})
    img_url = StringField('Image URL', validators=[Optional(), URL()], render_kw={"placeholder": "Image Link", "class": "form-control mb-4"})
    submit = SubmitField('Submit', render_kw={"class": "mb-3"})
