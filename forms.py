from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import DataRequired, Length, Email, NumberRange, URL

class CreatePostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    subtitle = StringField('Subtitle', validators=[DataRequired()])
    location = StringField('Destination ✈️ (e.g. City, Prov/State, Country)', validators=[DataRequired()])
    num_times_visited = IntegerField('How many times have you visited?', validators=[NumberRange(min=1, message="Value must be above 0."), DataRequired()])
    body = TextAreaField('Tell us about it', validators=[DataRequired()])
    visit_again = BooleanField('Would you visit again?')
    rating = SelectField('How many stars?', choices=["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"], validators=[DataRequired()])
    img_url = StringField('Image URL', validators=[URL(), DataRequired()])
    submit = SubmitField('Add Post')
