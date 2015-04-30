import threading
import Queue
from time import sleep
from collections import namedtuple

from flask import current_app


ThreadInfo = namedtuple('ThreadInfo', 'name target args previous_thread')

threads_for_restart = Queue.Queue()


def start_monitor():
    start_thread('Thread monitor',
                 restart_on_exit=True,
                 target=_monitor,
                 args=(current_app._get_current_object(),))


def _monitor(app):
    with app.app_context():
        while True:
            current_app.logger.log(2, 'Waiting for threads to restart')
            ti = threads_for_restart.get()
            current_app.logger.log(8, 'Executing thread restart %s' % ti.name)
            start_thread(ti.name, True, ti.target, ti.args)
            threads_for_restart.task_done()

            sleep(5)


def any_threads_by_name(name):
    return any(t.name == name for t in threading.enumerate())


def get_thread(name):
    thread = next(t for t in threading.enumerate() if t.name == name)
    if thread is not None:
        return ThreadInfo(thread.name, None, thread._Thread__args[4], None)
    return None

# Threads with "restart_on_exit" enabled will be restarted if failed.
def start_thread(name, restart_on_exit, target, args=(), onerror=None):
    # allow only one thread of same name (enumerate returns only alive ones)

    if restart_on_exit:
        for t in threading.enumerate():
            if t.name == name:
                current_app.logger.info('Can not start thread, already running %s' % name)
                return

    current_app.logger.log(2, 'Starting thread %s' % name)
    t = threading.Thread(name=name,
                         target=_start_thread,
                         args=(name, restart_on_exit, target,
                               current_app._get_current_object(), args, onerror))
    t.setDaemon(True)
    t.start()
    return t


def _start_thread(name, restart, target, app, args, onerror):
    with app.app_context():
        current_app.logger.log(2, 'Thread %s started' % name)
        try:
            target(*args)
        except Exception as e:
            if onerror is None:
                current_app.logger.info('Exception in thread ' + name)
                current_app.logger.exception(e)
            else:
                onerror(e, *args)
        finally:
            if restart:
                if current_app.config['RESTART_FAILED_THREADS']:
                    current_app.logger.info('Put thread in queue for restart')
                    threads_for_restart.put(ThreadInfo(name, target, args, threading.current_thread))
                else:
                    current_app.logger.info('Wont put thread for restart. Check config option RESTART_FAILED_THREADS')
