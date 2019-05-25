from wtforms import TextField
from main.models import User
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired

class PostForm(FlaskForm):
    content = TextAreaField('',validators=[DataRequired()])
    submit = SubmitField('Send')