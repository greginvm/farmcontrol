from flask import Blueprint

dashboard = Blueprint('dashboard', __name__)
socketio_namespace = '/dashboard'

from . import views