# -*- coding: utf-8 -*-

from flask import current_app

from .. import db, email, callcenter
from ..models import Notification, Contact
from datetime import timedelta
from .. import date_util


def send_warnings(warnings, call_in_progress_callback, call_ended_callback):
    notification = Notification.create_notification(warnings)

    current_app.logger.info('Sending notifications to contacts')

    contacts = db.session.query(Contact).all()

    for c in contacts:
        if c.phone and c.enable_sms_warnings:
            callcenter.send_sms(c.phone, notification.text)
        if c.email and c.enable_email_warnings:
            email.send_email(c.email, notification.subject,
                             'mail/notification',
                             notification=notification,
                             warnings=warnings)

        if c.phone and c.enable_phone_call_warnings \
                and (c.last_phone_call_ts is None or c.call_wait_minutes is None
                     or (date_util.datetime_now() - c.last_phone_call_ts) > timedelta(minutes=c.call_wait_minutes)):

            c.last_phone_call_ts = date_util.datetime_now()
            callcenter.make_a_call(c.phone, call_in_progress_callback, call_ended_callback, (c.id,))

    return notification
