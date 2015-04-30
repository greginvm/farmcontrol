from os import path

from flask import Flask
from flask.ext.socketio import SocketIO
from flask.ext.babel import Babel
from flask.ext.babel import lazy_gettext
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from flask.ext.login import LoginManager
from flask.ext.admin import Admin
from flask.json import JSONEncoder
from config import config


mail = Mail()
socketio = SocketIO()
babel = Babel()
db = SQLAlchemy()
admin = Admin()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
login_manager.login_message = lazy_gettext('Please log in to access this page.')


class CustomJSONEncoder(JSONEncoder):
    """This class adds support for lazy translation texts to Flask's
    JSON encoder. This is necessary when flashing translated texts.

    source: http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiv-i18n-and-l10n
    """

    def default(self, obj):
        from speaklater import is_lazy_string

        if is_lazy_string(obj):
            try:
                return unicode(obj)  # python 2
            except NameError:
                return str(obj)  # python 3
        return super(CustomJSONEncoder, self).default(obj)


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config.from_pyfile(path.join(app.instance_path, config[config_name].CUSTOM_CONFIG), silent=True)
    config[config_name].init_app(app)

    mail.init_app(app)
    socketio.init_app(app)
    babel.init_app(app)
    login_manager.init_app(app)
    db.init_app(app)
    admin.init_app(app)

    import assets

    assets.init_app(app)

    app.json_encoder = CustomJSONEncoder

    from .dashboard import dashboard as dashboard_blueprint

    app.register_blueprint(dashboard_blueprint)

    from .auth import auth as auth_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import adminbp as adminbp_blueprint

    app.register_blueprint(adminbp_blueprint, url_prefix='/admin')

    from flask.ext.login import current_user

    @babel.localeselector
    def get_locale():
        if current_user is not None and hasattr(current_user, 'locale') and current_user.locale is not None:
            locale = current_user.locale
        else:
            locale = app.config['BABEL_DEFAULT_LOCALE']
            # or select best match:
            # request.accept_languages.best_match(current_app.config['LANGUAGES'].keys())
        return locale

    return app
