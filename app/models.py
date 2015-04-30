from collections import namedtuple
from os import access, path, W_OK

from flask import current_app
from recordtype import recordtype
from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

import models_jsonapi as mj
from . import db, login_manager, date_util
from datetime import timedelta


StateWarning = namedtuple('StateWarning', ['limit', 'value', 'created_ts', 'sensor', 'alarming_measurements'])

RRDDef = recordtype('RRDDef', 'name step path mmin mmax')


class Measurement(object):
    def __init__(self, sensor_code):
        self.sensor_code = sensor_code
        self.sensor = None

        self.value = None
        self.read_ts = None
        self.has_warning = False
        self.has_notification = False

    def init_sensor(self):
        self.sensor = db.session.query(Sensor).filter(Sensor.sensor_code == self.sensor_code).first()

    def init_has_warning(self):
        self.has_warning = self.sensor.is_value_out_of_bounds(self.value)

    def local_read_ts_str(self):
        return date_util.to_local_datetime(self.read_ts).strftime(current_app.config['DATETIME_FORMAT_W_TZ'])

    @property
    def device_code(self):
        return self.sensor_code[0:2]

    @property
    def measurement_code(self):
        return self.sensor_code[2]

    def __repr__(self):
        return '<Measurement {}: {} [{}]>'.format(self.sensor_code, self.value, self.read_ts)

    def to_json_dict(self):
        return mj.encode_dict({
            'sensor_id': self.sensor.id,
            'sensor_code': self.sensor_code,
            'value': self.value,
            'read_ts': self.read_ts,
            'has_warning': self.has_warning,
            'has_notification': self.has_notification
        })


class SensorType(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'sensor_type'

    id = db.Column(db.Integer, primary_key=True)
    unit = db.Column(db.Unicode(5))
    description = db.Column(db.String(120))
    name = db.Column(db.String(120))
    sensors = db.relationship('Sensor', backref='type', lazy='dynamic')

    def __repr__(self):
        return '<SensorType[%s] %s}>' % (self.id, self.description)


class Device(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'device'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120))
    sensors = db.relationship('Sensor', backref='device', lazy='dynamic')

    def __repr__(self):
        return '<Device[%s] %s}>' % (self.id, self.description)

    def to_json_dict(self):
        return mj.encode_dict({
            'id': self.id,
            'description': self.description
        })


def _get_rrd_db_path_from_context(context):
    return Sensor.get_rrd_db_path_from_context(context)


class Sensor(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'sensor'
    jsonapi_columns_exclude = ['rrd_db_path']

    @staticmethod
    def get_rrd_db_path(sensor_code, step):
        return path.join(current_app.config['DATABASE_DIR'],
                         current_app.config['RRDTOOL_DATABASE_NAME_TEMPLATE'] % (
                             sensor_code, step))

    @staticmethod
    def get_rrd_db_path_from_context(context):
        return Sensor.get_rrd_db_path(context.current_parameters['sensor_code'],
                                      context.current_parameters['emit_every'])

    id = db.Column(db.Integer, primary_key=True)
    sensor_code = db.Column(db.String(5))
    description = db.Column(db.String(40))

    save_to_rrd_db = db.Column(db.Boolean, default=True)
    rrd_db_path = db.Column(db.String, default=_get_rrd_db_path_from_context)
    emit_every = db.Column(db.Integer)

    max_possible_value = db.Column(db.Float(precision=2, decimal_return_scale=2))
    max_warning_value = db.Column(db.Float(precision=2, decimal_return_scale=2))

    min_possible_value = db.Column(db.Float(precision=2, decimal_return_scale=2))
    min_warning_value = db.Column(db.Float(precision=2, decimal_return_scale=2))

    observable_measurements = db.Column(db.Integer, default=3)
    observable_alarming_measurements = db.Column(db.Integer, default=2)

    warning_wait_minutes = db.Column(db.Integer, default=10)
    enable_warnings = db.Column(db.Boolean, default=True)

    type_id = db.Column(db.Integer, db.ForeignKey('sensor_type.id'))
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))

    def get_current_rrd_db_path(self):
        return Sensor.get_rrd_db_path(self.sensor_code, self.emit_every)

    def is_value_out_of_bounds(self, value):
        return self.is_value_too_high(value) or self.is_value_too_low(value)

    def is_value_too_low(self, value):
        return self.min_warning_value is not None and value < self.min_warning_value

    def is_value_too_high(self, value):
        return self.max_warning_value is not None and value > self.max_warning_value

    def can_save_into_rrddb(self):
        return self.save_to_rrd_db and self.get_current_rrd_db_path() is not None and access(
            path.dirname(self.get_current_rrd_db_path()), W_OK)

    def get_rrd_definition(self):
        return RRDDef(name=self.sensor_code,
                      step=self.emit_every,
                      path=str(self.get_current_rrd_db_path()),
                      mmin=self.min_possible_value,
                      mmax=self.max_possible_value)

    def __repr__(self):
        return '<Sensor[%s] %s}>' % (self.id, self.sensor_code)

    def to_json_dict(self, included_keys=None):
        return mj.encode_dict({
                                  'id': self.id,
                                  'sensor_code': self.sensor_code,
                                  'description': self.description,
                                  'max_possible_value': self.max_possible_value,
                                  'max_warning_value': self.max_warning_value,
                                  'min_possible_value': self.min_possible_value,
                                  'min_warning_value': self.min_warning_value,
                                  'observable_measurements': self.observable_measurements,
                                  'observable_alarming_measurements': self.observable_alarming_measurements,
                                  'warning_wait_minutes': self.warning_wait_minutes,
                                  'enable_warnings': self.enable_warnings,
                                  'type_id': self.type_id,
                                  'device_id': self.device_id,
                                  'type_name': self.type.name,
                                  'value': None,
                                  'd_value': None,
                                  'read_ts': None,
                                  'step': self.emit_every,
                                  'unit': self.type.unit,
                                  'has_warning': False,
                                  'has_notification': False
                              }, included_keys=included_keys)


class Contact(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'contact'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(40))
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))

    enable_sms_warnings = db.Column(db.Boolean, default=False)
    enable_email_warnings = db.Column(db.Boolean, default=False)
    enable_phone_call_warnings = db.Column(db.Boolean, default=False)
    last_phone_call_ts = db.Column(db.DateTime)
    call_wait_minutes = db.Column(db.Integer, default=20)

    def next_available_phone_call(self):
        if self.last_phone_call_ts is not None and self.call_wait_minutes is not None:
            return self.last_phone_call_ts + timedelta(minutes=self.call_wait_minutes)
        return None

    def __repr__(self):
        return '<Contact[%s] %s}>' % (self.id, self.name)

    def to_json_dict(self):
        return mj.encode_dict({
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'enable_sms_warnings': self.enable_sms_warnings,
            'enable_phone_call_warnings': self.enable_phone_call_warnings,
            'enable_email_warnings': self.enable_email_warnings,
            'last_phone_call_ts': self.last_phone_call_ts,
            'next_available_phone_call': self.next_available_phone_call(),
            'call_wait_minutes': self.call_wait_minutes,
            'pending': False
        })


class Notification(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)

    text = db.Column(db.String(160))
    subject = db.Column(db.String(100))
    created_ts = db.Column(db.DateTime)

    def __repr__(self):
        return '<Notification[%s] %s}>' % (self.id, str(self.text))

    @staticmethod
    def create_notification(warnings):
        created_ts = date_util.datetime_now()
        local_dt = date_util.to_local_datetime(created_ts)
        text = Notification.create_text(warnings)
        subject = 'Notification @ ' + local_dt.strftime(
            '%d.%m.%Y:%H:%M')

        return Notification(text=text, subject=subject, created_ts=created_ts)

    @staticmethod
    def create_text(warnings):
        text = 'ALARM! '
        for w in warnings:
            text += u'{:s}@{:s} {:.2f}, {:s}: {:.2f}; '.format(
                w.sensor.description,
                date_util.to_local_datetime(w.created_ts).strftime(current_app.config['DATETIME_FORMAT_W_TZ']),
                w.value,
                ('MAX' if w.limit < w.value else 'MIN'),
                w.limit)
        return text

    def to_json_dict(self):
        return mj.encode_dict({
            'id': self.id,
            'text': self.text,
            'subject': self.subject,
            'created_ts': self.created_ts
        })


class RelayState(object):
    Off, PendingOff, On, PendingOn, Error = range(5)

    def __init__(self, pin, state, changed_ts=None):
        self.state = state
        self.pin = pin
        self.changed_ts = date_util.datetime_now() if changed_ts is None else changed_ts

    def __repr__(self):
        return '<RelayState %d %s>' % (self.pin, ['Off', 'PendingOff', 'On', 'PendingOn', 'Error'][self.state])


class Relay(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'relay'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(40))
    switch_on_text = db.Column(db.String(16))
    switch_off_text = db.Column(db.String(16))
    arduino_pin = db.Column(db.Integer)

    def to_json_dict(self):
        return mj.encode_dict({
            'id': self.id,
            'description': self.description,
            'switch_on_text': self.switch_on_text,
            'switch_off_text': self.switch_off_text,
            'arduino_pin': self.arduino_pin,
            'state': RelayState.Off,
            'is_initialized': False,
            'changed_ts': None,
            'pending_refresh': False
        })

    def __repr__(self):
        return '<Relay[%s] %s pin: %s}>' % (self.id, self.description, str(self.arduino_pin))


class RelayLog(db.Model, mj.ModelJSONAPIMixin):
    __tablename__ = 'relay_log'
    id = db.Column(db.Integer, primary_key=True)
    relay_id = db.Column(db.Integer, db.ForeignKey('relay.id'))
    created_ts = db.Column(db.DateTime)
    from_state = db.Column(db.Integer)
    to_state = db.Column(db.Integer)

    def __repr__(self):
        return '<RelayLog [%s] %s -> %s>' % (self.id, self.from_state, self.to_state)


class RrdFetchResults(object):
    def __init__(self, raw_data):
        self.raw_data = raw_data

    @property
    def from_dt(self):
        return date_util.datetime_from_timestamp(self.raw_data[0][0])

    @property
    def to_dt(self):
        return date_util.datetime_from_timestamp(self.raw_data[0][1])

    @property
    def step(self):
        return int(self.raw_data[0][2])

    @property
    def name(self):
        return self.raw_data[1][0]

    @property
    def result(self):
        return self.raw_data[2]

    def to_json_dict(self, only_data=False):
        if only_data:
            d = []
            start = date_util.timestamp(self.from_dt)
            end = date_util.timestamp(self.to_dt)
            i = 0
            for t in xrange(start, end, self.step):
                d.append((t * 1000, self.raw_data[2][i][0]))
                i += 1
            return d
        else:
            return mj.encode_dict({
                'from': self.from_dt,
                'to': self.to_dt,
                'step': self.step,
                'data': [i[0] for i in self.result]
            })

    def __repr__(self):
        return self.raw_data.__repr__()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    last_seen = db.Column(db.DateTime(), default=date_util.datetime_now)
    locale = db.Column(db.String(2))

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def ping(self):
        self.last_seen = date_util.datetime_now()
        db.session.add(self)

    def __repr__(self):
        return '<User %r>' % (self.nickname,)