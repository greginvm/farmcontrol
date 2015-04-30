from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required, Length
from flask.ext.babel import lazy_gettext


class LoginForm(Form):
    email = StringField(lazy_gettext('Email/Username'), validators=[Required(), Length(1, 64)])
    password = PasswordField(lazy_gettext('Password'), validators=[Required()])
    remember_me = BooleanField(lazy_gettext('Keep me logged in'))
    charts_enabled = BooleanField(lazy_gettext('Enable charts'), default=True)
    submit = SubmitField(lazy_gettext('Log In'))