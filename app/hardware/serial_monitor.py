from time import sleep

import serial
from flask import current_app

from ..models import Measurement
from .. import thread_monitor
from .. import date_util


def start(callback):
    target = listen_real if current_app.config['RADIO_LISTEN'] else listen_dummy
    thread_monitor.start_thread(name='Serial watch', restart_on_exit=True, target=target, args=(callback,))


def get_sensor_value(stream):
    char = stream.read(1)
    measurement = None
    if char == 'a':

        """
        Structure of expected LLAP message:
        Max length 11 bytes
        Example message: aZGB150.1---
        0 - a - start of the message
        1,2 - XX - device id (ZA/SA/...)
        3 - H/T/B.. - sensor is (humidity/temperature)
        4-11  -  Value (max 8 chars, trailed in the end with '-' (if number string is shorter))
        When battery level meter is disabled LLAP looks like: ZGBc0------
        """

        llap_msg = stream.read(11)

        measurement = Measurement(llap_msg[:3])

        val = None
        try:
            # Remove trailing
            val = float(llap_msg[3:].rstrip('-'))
        except ValueError as e:
            current_app.logger.log(7, 'Error parsing number from LLAP %s', llap_msg)

        if val is None:
            measurement = None
        else:
            measurement.value = val
            measurement.read_ts = date_util.datetime_now()

    return measurement


def listen_real(callback):
    with serial.Serial(port=current_app.config['RADIO_LISTEN_ON_PORT'],
                       baudrate=current_app.config['RADIO_LISTEN_ON_BAUD']) as ser:

        current_app.logger.info('Opening Slice of Pi serial port %s:%s',
                                current_app.config['RADIO_LISTEN_ON_PORT'],
                                current_app.config['RADIO_LISTEN_ON_BAUD'])

        # wait for a moment before doing anything else
        sleep(0.2)

        # clear out the serial input buffer to ensure there are 
        # no old messages lying around
        ser.flushInput()

        while True:
            current_app.logger.debug('Start read loop')

            while ser.inWaiting():
                measurement = get_sensor_value(ser)
                if measurement is not None:
                    callback(measurement)

            current_app.logger.debug('Finish read loop')
            sleep(current_app.config['RADIO_LISTEN_WAIT_SECONDS'])


"""
    Only use for dev enviroment, generates random values or values put to DUMMY_VALUES
"""
import random
from io import StringIO
from .. import models

DUMMY_VALUES = {}


def listen_dummy(callback):
    sensors = models.Sensor.query.all()
    threads = []
    for sensor in sensors:
        t = thread_monitor.start_thread('Listen for sensor %s' % (sensor.sensor_code,), False,
                                        listen_dummy_sensor,
                                        (callback,
                                         sensor.min_possible_value,
                                         sensor.max_possible_value,
                                         sensor.sensor_code,
                                         sensor.emit_every,))
        threads.append(t)

    [t.join() for t in threads]


def listen_dummy_sensor(callback, min_possible_value, max_possible_value, sensor_code, emit_every):
    while True:
        # get a dummy value or generate a random one
        val = DUMMY_VALUES.get(sensor_code, round(random.uniform(min_possible_value, max_possible_value), 2))
        llap_str = u'a{}{:.2f}'.format(sensor_code, val)
        llap_str += '-' * (12 - len(llap_str))
        llap_stream = StringIO(llap_str)
        m = get_sensor_value(llap_stream)
        callback(m)
        sleep(emit_every)