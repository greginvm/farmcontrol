# -*- coding: utf-8 -*-
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    CUSTOM_CONFIG = 'application.cfg'
    SECRET_KEY = 'secret!'  # remember to install secret key
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    WTF_CSRF_ENABLED = True
    SHOW_DEBUG_GUI = False
    LANGUAGES = {
        'en': 'English',
        'sl': 'Slovene'
    }
    BABEL_DEFAULT_LOCALE = 'sl'

    ASSETS_AUTO_BUILD = False
    ASSETS_DEBUG = False

    DATETIME_FORMAT = '%d.%m.%Y %H:%M:%S'
    DATETIME_FORMAT_W_TZ = '%d.%m.%Y %H:%M:%S <%Z%z>'  # with timezone

    RADIO_LISTEN = True
    RADIO_LISTEN_WAIT_SECONDS = 1
    RADIO_LISTEN_ON_PORT = '/dev/ttyAMA0'
    RADIO_LISTEN_ON_BAUD = 115200

    RELAY_BOARD = True
    RELAY_BOARD_PORT = '/dev/ttyACM0'
    RELAY_BOARD_BAUD = 9600

    TWILIO_SID = None
    TWILIO_TOKEN = None
    TWILIO_FROM_PHONE = None

    # the message does not need say anything, this is just a dummy
    # the point is only to call on users number
    TWILIO_CALL_TWIML = "http://demo.twilio.com/docs/voice.xml"

    # use with second Twilio account (SMS works for free :))
    TWILIO_SMS_SID = None
    TWILIO_SMS_TOKEN = None
    TWILIO_SMS_FROM_PHONE = None

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = None

    APP_EMAIL_SUBJECT_PREFIX = '[Nardi Farma]'
    APP_ADMIN = None

    RRDTOOL_DEFAULT_CFS = ['AVERAGE']

    RESTART_FAILED_THREADS = True

    @staticmethod
    def database_dir(env):
        return os.environ.get(env) or os.path.join(basedir, 'db/')

    @classmethod
    def init_app(cls, app):
        from logging import Formatter

        fmt = Formatter(
            fmt='[%(asctime)s] %(levelname)s %(filename)s: %(lineno)d (%(funcName)s, %(threadName)s):\n %(message)s')

        app.logger.setLevel(10)
        [h.setFormatter(fmt) for h in app.logger.handlers]


class DevelopmentConfig(Config):
    DEBUG = True
    SHOW_DEBUG_GUI = True
    DATABASE_DIR = Config.database_dir('DEV_DATABASE_DIR')

    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATABASE_DIR, 'data-dev.sqlite')
    SQLALCHEMY_RECORD_QUERIES = True

    RRDTOOL_DATABASE_NAME_TEMPLATE = '%s-%d-dev.rrd'  #
    RRDTOOL_DATABASE_RESOLUTIONS = [(1, 1), (2, 2), (30, 7)]  #

    ASSETS_AUTO_BUILD = True
    ASSETS_DEBUG = True

    # REMEMBER: when enabled it might hurt your wallet
    SEND_SMS = False
    MAKE_CALLS = False
    MAIL_SUPPRESS_SEND = True

    RADIO_LISTEN = False

    RELAY_BOARD = False

    RESTART_FAILED_THREADS = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


class ProductionConfig(Config):
    DATABASE_DIR = Config.database_dir('DATABASE_DIR')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(DATABASE_DIR, 'data.sqlite')
    RRDTOOL_DATABASE_NAME_TEMPLATE = '%s-%d.rrd'
    RRDTOOL_DATABASE_RESOLUTIONS = [(1, 2), (5, 30), (7, 60), (30, 366)]

    SEND_SMS = True
    MAIL_SUPPRESS_SEND = False
    MAKE_CALLS = True
    RADIO_LISTEN = True
    RELAY_BOARD = True
    RESTART_FAILED_THREADS = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler, RotatingFileHandler

        fmt = logging.Formatter(
            fmt='[%(asctime)s] %(levelname)s %(filename)s: %(lineno)d (%(funcName)s, %(threadName)s):\n %(message)s')

        credentials = None
        secure = None
        if app.config.get('MAIL_USERNAME') is not None:
            credentials = (app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD'))
            if app.config.get('MAIL_USE_TLS'):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr=app.config['MAIL_DEFAULT_SENDER'],
            toaddrs=[app.config['APP_ADMIN']],
            subject=app.config['APP_EMAIL_SUBJECT_PREFIX'] + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(fmt)
        app.logger.addHandler(mail_handler)

        filehandler = RotatingFileHandler(
            filename=os.path.join(app.config['DATABASE_DIR'], 'farmatempapp.log'), maxBytes=10000000,
            backupCount=10)
        filehandler.setLevel(logging.INFO)
        filehandler.setFormatter(fmt)
        app.logger.addHandler(filehandler)


class UnixProductionConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        import logging
        from logging.handlers import SysLogHandler

        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'unix': UnixProductionConfig,
    'default': DevelopmentConfig
}