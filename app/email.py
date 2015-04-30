from flask import current_app, render_template
from flask.ext.mail import Message

from . import mail, thread_monitor


def send_email(to, subject, template, **kwargs):
    log_message = 'Sending e-mail to %s (%s)' % (to, subject)
    current_app.logger.info(log_message)
    msg = Message(current_app.config['APP_EMAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)

    thread_monitor.start_thread(log_message, False, mail.send, (msg,))

