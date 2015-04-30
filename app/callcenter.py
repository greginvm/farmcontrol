from time import sleep
import threading

from flask import current_app
from twilio import TwilioRestException
from twilio.rest import TwilioRestClient
from . import thread_monitor


def get_call_thread_name(to):
    return 'Calling %s' % (to,)


def get_calls_in_progress():
    thread_names = [t.name for t in threading.enumerate() if t.name.startswith('Calling ')]
    calls = []
    for tn in thread_names:
        thread = thread_monitor.get_thread(tn)
        if thread is not None:
            calls.append({
                'id': thread.args[0]
            })

    return calls


def cancel_call(to):
    thread_name = get_call_thread_name(to)
    current_app.logger.info('Finding a call in progress to cancel (%s)!' % (thread_name,))
    thread = thread_monitor.get_thread(thread_name)
    if thread is not None:
        current_app.logger.info('Canceling call in progress (%s)!' % (thread_name,))
        thread.args[2].set()


def make_a_call(to, start_call_callback, call_finished_callback, args):
    log_msg = get_call_thread_name(to)
    current_app.logger.info(log_msg)

    if not current_app.config['MAKE_CALLS']:
        current_app.logger.exception('Calling disabled')
    else:
        if thread_monitor.any_threads_by_name(log_msg):
            current_app.logger.info('Call in progress (%s), skip call!' % (log_msg,))
        else:
            start_call_callback(to, *args)
            cancel_event = threading.Event()
            thread_monitor.start_thread(log_msg, False, _make_a_call, (to, call_finished_callback, cancel_event, args))


def _make_a_call(to, call_finished_callback, cancel_event, args):
    client = TwilioRestClient(current_app.config['TWILIO_SID'],
                              current_app.config['TWILIO_TOKEN'])
    try:
        call_successful = False
        nr_attempts = 0
        max_attempts = 30
        while not call_successful and nr_attempts < max_attempts:
            nr_attempts += 1
            call = client.calls.create(to=to, from_=current_app.config['TWILIO_FROM_PHONE'],
                                       url=current_app.config["TWILIO_CALL_TWIML"])
            current_app.logger.info('Call (SID %s, TO %s) attempt nr %d/%d' % (call.sid, to, nr_attempts, max_attempts))

            # check what is happening with the call
            call_is_ended = False
            while not call_is_ended:
                call_info = client.calls.get(call.sid)

                # If call has to be canceled
                if cancel_event.is_set():
                    call_successful = True
                    client.calls.update(call.sid, status="completed")
                    current_app.logger.info('Call (SID %s, TO %s) canceled "%s"' % (call.sid, to, call_info.status))
                    break

                # Call had been seen
                if call_info.status in ('canceled', 'completed', 'in-progress'):
                    call_successful = True
                    current_app.logger.info('Call (SID %s, TO %s) successful "%s"' % (call.sid, to, call_info.status))
                    break

                # Call could not be made
                if call_info.status in ('busy', 'no-answer', 'failed'):
                    call_successful = False
                    current_app.logger.info(
                        'Call (SID %s, TO %s) NOT successful "%s"' % (call.sid, to, call_info.status))
                    break

                # Else check again
                sleep(3)

    except TwilioRestException as e:
        current_app.logger.exception(e)
    else:
        current_app.logger.info('Call to %s finished!' % (to,))
    call_finished_callback(to, *args)


def send_sms(to, text):
    log_msg = 'Sending SMS to %s' % (to,)
    current_app.logger.info(log_msg)
    if not current_app.config['SEND_SMS']:
        current_app.logger.exception('SMS sending disabled')
    else:
        thread_monitor.start_thread(log_msg, False, _send_sms, (to, text))


def _send_sms(to, text):
    client = TwilioRestClient(current_app.config['TWILIO_SMS_SID'],
                              current_app.config['TWILIO_SMS_TOKEN'])

    try:
        message = client.messages.create(to=to, body=text,
                                         from_=current_app.config['TWILIO_SMS_FROM_PHONE'])
    except TwilioRestException as e:
        current_app.logger.exception(e)
    else:
        current_app.logger.info('SMS sent to %s (SID: %s)' % (to, message.sid))

