from flask import Blueprint

adminbp = Blueprint('adminbp', __name__)

from . import views
