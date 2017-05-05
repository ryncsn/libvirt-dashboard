"""
"""
import stomp
import datetime
import time
import sys
import signal
import json

from app import app
from app import logger as LOGGER
from app.model import Run
from config import ActiveConfig


BUS_HOST = ActiveConfig.BUS_HOST
BUS_PORT = ActiveConfig.BUS_PORT
BUS_USER = ActiveConfig.BUS_USER
BUS_PASSWORD = ActiveConfig.BUS_PASSWORD
BUS_TIMEOUT = ActiveConfig.BUS_TIMEOUT
BUS_DISTINATION = ActiveConfig.BUS_DISTINATION


class MessageRouter(object):
    def __init__(self):
        self.listenning = True
        self.conn = None

    def connect(self):
        self.conn = stomp.Connection([(BUS_HOST, BUS_PORT)])
        self.conn.set_listener('CI Listener', self)
        self.conn.start()
        self.conn.connect(login=BUS_USER, passcode=BUS_PASSWORD)
        self.conn.subscribe(
            destination=BUS_DISTINATION,
            id=1,
            ack='auto',
            headers={'selector': "(libvirt_dashboard_submitted = 'true')"}
        )

    def start(self):
        def _signal_handler(*_):
            """
            Handler on signal
            """
            LOGGER.info('Terminating subscription.')
            self.listenning = False
            self.conn.disconnect()
            sys.exit(0)

        self.connect()
        signal.signal(signal.SIGINT, _signal_handler)
        signal.pause()

    def on_message(self, headers, message):
        """
        Handler on message
        """
        LOGGER.info("=" * 72)
        LOGGER.info('Message headers:\n%s', headers)
        LOGGER.info('Message body:\n%s', message)
        libvirt_dashboard_build = headers.get('libvirt_dashboard_build')
        libvirt_dashboard_id = headers.get('libvirt_dashboard_id')
        polarion_testrun = headers.get('polarion_testrun')
        message = json.loads(message)
        status = message.get('status')
        log_url = message.get('log-url')
        with app.app_context():
            if status == "passed":
                count = Run.query.filter(Run.id == libvirt_dashboard_id).update({
                    "submit_status": status,
                    "submit_log": log_url,
                    "submit_date": datetime.datetime.now()
                })
            else:
                count = Run.query.filter(Run.id == libvirt_dashboard_id).update({
                    "submit_status": status,
                    "submit_log": log_url,
                })
            Run.query.session.commit()
            if not count:
                LOGGER.error("No matching test run for ID: {}".format(libvirt_dashboard_id))
            else:
                LOGGER.info("Updated Test run ID: {}".format(libvirt_dashboard_id))

        # TODO: a task to set Polarion build id?

    def on_error(self, headers, message):
        LOGGER.info('Got an error:\n%s', headers)
        LOGGER.info("=" * 72)
        LOGGER.info('Message headers:\n%s', headers)
        LOGGER.info('Message body:\n%s', message)
        time.sleep(10)
        self.conn.disconnect()
        self.connect()


if __name__ == "__main__":
    router = MessageRouter()
    router.start()
