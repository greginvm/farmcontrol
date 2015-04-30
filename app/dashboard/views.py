# -*- coding: utf-8 -*-
# TODO: Auth for socket.io

from flask import render_template, current_app, jsonify, request
from flask.ext.login import login_required
from os import getpid

from . import dashboard, socketio_namespace
from . import controller
from .. import thread_monitor
from app import socketio


def start_routines():
    current_app.logger.info('Startup monitoring')
    thread_monitor.start_monitor()
    controller.init()


@dashboard.route('/')
@dashboard.route('/index.html')
@login_required
def index():
    charts_enabled = request.cookies.get('charts_enabled')
    return render_template('index.html', pid=getpid(), charts_enabled=charts_enabled)


@dashboard.route('/charts.html')
@login_required
def charts():
    return render_template('charts.html')


@dashboard.route('/history.json')
@login_required
def history():
    data = controller.process_history_json()
    return jsonify(data)


@socketio.on('connect', namespace=socketio_namespace)
def test_connect():
    current_app.logger.info('Client connected')
    controller.process_initialization_data()


@socketio.on('sensor update warning values', namespace=socketio_namespace)
def update_warning_values(data):
    controller.process_change_warning_values(data)


@socketio.on('call cancel', namespace=socketio_namespace)
def call_cancel(data):
    controller.process_cancel_call(data)


@socketio.on('relay switch', namespace=socketio_namespace)
def relay_switch(data):
    controller.process_relay_switch(data)


@socketio.on('relay refresh state', namespace=socketio_namespace)
def relay_switch(data):
    controller.process_relay_update_state(data)


@socketio.on('contact notification update', namespace=socketio_namespace)
def update_contact(data):
    controller.process_contact_update(data)


@socketio.on('disconnect', namespace=socketio_namespace)
def test_disconnect():
    current_app.logger.info('Client disconnected')


@socketio.on('apply dummy', namespace=socketio_namespace)
def apply_dummy(data):
    controller.process_apply_dummy(data)


