from flask import redirect, url_for, request
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from wtforms import PasswordField
from sqlalchemy.orm.attributes import get_history

from ..models import Sensor, SensorType, Device, Contact, Notification, Relay, User
from .. import admin, db


class MyView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated()

    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            return redirect(url_for('auth.login', next=request.url))


class UserView(MyView):
    column_list = ('email', 'password', 'last_seen', 'locale')

    form_excluded_columns = ('password_hash',)
    form_extra_fields = {
        'password': PasswordField('Password')
    }

    def on_model_change(self, form, model, is_created):
        if form.password.data is None or len(form.password.data) < 3:
            prev_hash = get_history(model, 'password_hash')[2][0]
            model.password_hash = prev_hash
            db.session.commit()

        pass

admin.add_view(MyView(SensorType, db.session))
admin.add_view(MyView(Device, db.session))
admin.add_view(MyView(Sensor, db.session))
admin.add_view(MyView(Contact, db.session))
admin.add_view(MyView(Notification, db.session))
admin.add_view(MyView(Relay, db.session))
admin.add_view(UserView(User, db.session))