from threading import Lock
import random
from time import sleep

import serial
from flask import current_app

from ..models import RelayState
from .. import thread_monitor


switch_lock = Lock()


class InvalidSerialResponseException(Exception):
    pass


def switch(relay, next_relay_state, callback):
    thread_monitor.start_thread('Relay switch',
                                restart_on_exit=False,
                                target=perform_switch,
                                args=(relay.id, relay.arduino_pin, next_relay_state, callback))


def perform_switch(relay_id, arduino_pin, next_relay_state, callback):
    try:
        if next_relay_state not in [RelayState.PendingOff, RelayState.PendingOn]:
            raise Exception('Invalid state passed <{:d}> for relay {:d}'.format(next_relay_state, relay_id))

        query = create_query(arduino_pin, next_relay_state)
        response = perform_query(query)

    except Exception as e:
        current_app.logger.exception(e)
        response = RelayState(arduino_pin, RelayState.Error)

    callback(relay_id, response)


def get_relay_state(relay_id, arduino_pin, callback, onerror=None):
    thread_monitor.start_thread('Get relay state %d' % (relay_id,),
                                restart_on_exit=False,
                                target=perform_get_relay_state,
                                args=(relay_id, arduino_pin, callback),
                                onerror=onerror)


def perform_get_relay_state(relay_id, arduino_pin, callback):
    query = create_query(arduino_pin, 'STATE')
    response = perform_query(query)
    callback(relay_id, response)


def perform_query(query, max_repeat=5):
    if not current_app.config['RELAY_BOARD']:
        return perform_dummy_query(query)
    repeat = False
    response = None
    with switch_lock:
        with serial.Serial(port=current_app.config['RELAY_BOARD_PORT'],
                           baudrate=current_app.config['RELAY_BOARD_BAUD'],
                           timeout=2, writeTimeout=2) as ser:

            sleep(.20)

            ser.flushInput()
            # Call for action
            current_app.logger.debug('Performing relay query %s', query)
            ser.write(query)
            sleep(.30)
            response_str = ser.readline()

            try:
                response = parse_relay_state_response(response_str)
                current_app.logger.debug('Result of query %s = %s' % (query, response_str))
            except InvalidSerialResponseException as e:
                current_app.logger.info('Could not parse response %s, repeat times %s' % (response_str, max_repeat))
                if max_repeat in (0, None):
                    raise e
                else:
                    repeat = True
                    max_repeat -= 1
                    sleep(.3)

    if repeat is True:
        return perform_query(query[:query.find('_') + 1] + '2-', max_repeat)
    return response


def perform_dummy_query(query):
    with switch_lock:
        sleep(0.5)

        # Call for action
        current_app.logger.log(8, 'Performing relay DUMMY query %s', query)
        query = query.split('_')
        pin = int(query[0].lstrip('a'))
        q = int(query[1].rstrip('-'))

        if q == 0:
            q = 'OF'
        elif q == 1:
            q = 'ON'
        elif q == 2:
            q = random.choice(['ON', 'OF'])
        dummy_response = '{}_{}'.format(pin, q)
        response = parse_relay_state_response(dummy_response)
    return response


def parse_relay_state_response(response_str):
    response_str = response_str.strip(' \t\r\n')
    response = response_str.split('_')
    if len(response) is not 2:
        raise InvalidSerialResponseException('Invalid serial response string %s' % (response_str,))

    try:
        pin = int(response[0])
    except ValueError as e:
        raise InvalidSerialResponseException('Invalid pin number %s' % (response[0],))

    try:
        state = {'ON': RelayState.On, 'OF': RelayState.Off}[response[1]]
    except (KeyError, IndexError) as e:
        raise InvalidSerialResponseException('Invalid state string %s' % (response[1],))
    return RelayState(pin, state)


def create_query(arduino_pin, query):
    if arduino_pin is None:
        raise Exception('Arduino pin for relay is not defined')
    if query is RelayState.PendingOff:
        query = 0
    if query is RelayState.PendingOn:
        query = 1
    if query is 'STATE':
        query = 2
    return 'a{}_{}-'.format(arduino_pin, query)
