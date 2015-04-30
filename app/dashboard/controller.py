from datetime import timedelta

from flask import current_app

from .. import db, socketio
from app import rrddb
from app.hardware import serial_monitor, relay_controller
from ..models import Relay, Notification, Contact, Sensor, SensorType
from . import sensor_state
from . import informer
from ..models_jsonapi import to_json_dict, encode_dict
from . import socketio_namespace
from .. import date_util as du
from .. import callcenter


def _cast_or_default(converter, value, default=None):
    val = default
    try:
        val = converter(value)
    except ValueError:
        pass
    except TypeError:
        pass
    return val


def init():
    serial_monitor.start(process_measurement)


def process_measurement(measurement):
    try:
        measurement.init_sensor()

        if measurement.sensor is None:
            raise Exception('Sensor is not defined for received measurement %s'
                            % measurement)

        if measurement.sensor.can_save_into_rrddb():
            rrddb.add(measurement, measurement.sensor.get_rrd_definition())

        warnings = sensor_state.update_and_get_warnings(measurement)

        if warnings is not None and measurement.sensor.enable_warnings:
            notification = informer.send_warnings(warnings, process_emit_call_in_progress, process_emit_call_ended)
            db.session.add(notification)
            db.session.commit()
            measurement.has_notification = True
            socketio.emit('notification update', notification.to_json_dict(), namespace=socketio_namespace)

        db.session.commit()

        measurement.init_has_warning()
        socketio.emit('sensor update', measurement.to_json_dict(), namespace=socketio_namespace)

        db.session.remove()

    except Exception, e:
        current_app.logger.exception(e)


def process_history_json():
    sensors = Sensor.query.all()
    types = SensorType.query.all()

    data = {'yAxes': [], 'series': []}
    for t in types:
        data['yAxes'].append({
            'label': t.description,
            'unit': t.unit
        })

    for s in sensors:
        rrddef = s.get_rrd_definition()
        if rrddb.is_rrd_initialized(rrddef):
            data['series'].append({
                'name': s.description,
                'yAxis': s.type.description,
                'data': rrddb.fetch(rrddef, 'AVERAGE', timedelta(days=365), use_real_start=True).to_json_dict(
                    only_data=True)
            })

    return data


def process_initialization_data():
    sensors = []

    for s in Sensor.query.all():
        d = to_json_dict(s)
        rrddef = s.get_rrd_definition()
        if rrddb.is_rrd_initialized(rrddef):
            last = rrddb.fetch_last(rrddef)
            d['read_ts'] = du.timestamp(last[0])
            d['value'] = last[1]
            d['history'] = rrddb.fetch(rrddef, 'AVERAGE', timedelta(days=1),
                                       timedelta(minutes=5)).to_json_dict()

        sensors.append(d)

    relays = to_json_dict(Relay.query.all())
    notifications = to_json_dict(Notification.query.order_by(
        Notification.created_ts.desc()).limit(6).all())
    contacts = to_json_dict(Contact.query.all())
    calls = callcenter.get_calls_in_progress()
    socketio.emit('initial data', {
        'sensors': sensors,
        'relays': relays,
        'notifications': notifications,
        'contacts': contacts,
        'calls': calls
    }, namespace=socketio_namespace)

    # delayed initialization
    for r in relays:
        relay_controller.get_relay_state(r['id'], r['arduino_pin'], process_emit_relay_state)


def process_relay_update_state(data):
    relay_controller.get_relay_state(data['id'], data['arduino_pin'], process_emit_relay_state)


def process_emit_relay_state(relay_id, relay_state):
    socketio.emit('relay update', encode_dict({
        'id': relay_id,
        'state': relay_state.state,
        'changed_ts': relay_state.changed_ts,
        'is_initialized': True,
        'pending_refresh': False
    }), namespace=socketio_namespace)


def process_emit_call_in_progress(call_id, contact_id):
    socketio.emit('call in progress', encode_dict({
        'id': call_id,
    }), namespace=socketio_namespace)
    emit_contact(contact_id)


def process_emit_call_ended(call_id, contact_id):
    socketio.emit('call ended', encode_dict({
        'id': call_id,
    }), namespace=socketio_namespace)
    emit_contact(contact_id)


def process_cancel_call(data):
    callcenter.cancel_call(data['id'])


def emit_contact(contact_id):
    contact = db.session.query(Contact).filter(Contact.id == contact_id).first()
    socketio.emit('contact update', contact.to_json_dict(), namespace=socketio_namespace)


def process_relay_switch(data):
    # emit pending event
    socketio.emit('relay switch', {'id': data['id'], 'state': data['state']}, namespace=socketio_namespace)

    relay = db.session.query(Relay).filter(Relay.id == data['id']).first()

    if relay is None:
        raise Exception('Relay is not defined for received request %s' % (data,))
    relay_controller.switch(relay, data['state'], process_relay_response)


def process_relay_response(relay_id, relay_state):
    socketio.emit('relay switch',
                  encode_dict({'id': relay_id, 'state': relay_state.state, 'changed_ts': relay_state.changed_ts}),
                  namespace=socketio_namespace)


def process_contact_update(data):
    contact = db.session.query(Contact).filter(Contact.id == data['id']).first()
    if contact is None:
        raise Exception('Contact is not defined for received request %s' % (data,))

    if 'enable_sms_warnings' in data:
        contact.enable_sms_warnings = data['enable_sms_warnings']

    if 'enable_email_warnings' in data:
        contact.enable_email_warnings = data['enable_email_warnings']

    if 'enable_phone_call_warnings' in data:
        contact.enable_phone_call_warnings = data['enable_phone_call_warnings']

    if 'phone' in data:
        contact.phone = data['phone']
    if 'email ' in data:
        contact.email = data['email']
    if 'name' in data:
        contact.name = data['name']
    if 'call_wait_minutes' in data:
        contact.call_wait_minutes = _cast_or_default(int, (data['call_wait_minutes']))

    db.session.commit()
    socketio.emit('contact update', contact.to_json_dict(), namespace=socketio_namespace)


def process_change_warning_values(data):
    sensor = db.session.query(Sensor).filter(Sensor.id == data['id']).first()
    if sensor is None:
        raise Exception('Sensor is not defined for received request %s' % (data,))
    sensor.min_warning_value = data['min_warning_value']
    sensor.max_warning_value = data['max_warning_value']
    sensor.enable_warnings = data['enable_warnings'] is True
    sensor.observable_measurements = _cast_or_default(int, data['observable_measurements'])
    sensor.observable_alarming_measurements = _cast_or_default(int, data['observable_alarming_measurements'])
    sensor.warning_wait_minutes = _cast_or_default(int, data['warning_wait_minutes'])
    db.session.commit()
    d = sensor.to_json_dict(included_keys=['id', 'sensor_code',
                                           'min_warning_value', 'max_warning_value', 'enable_warnings',
                                           'observable_measurements', 'observable_alarming_measurements',
                                           'observable_alarming_measurements', 'warning_wait_minutes'])
    d['pending_max_warning_input'] = False
    d['pending_min_warning_input'] = False
    socketio.emit('sensor update warning values', d, namespace=socketio_namespace)


def process_apply_dummy(data):
    for i in range(4):
        print 'apply dummy'
    print 'apply dummy', data
    serial_monitor.DUMMY_VALUES[data['sensor_code']] = _cast_or_default(float, data['value'])