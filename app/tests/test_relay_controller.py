from unittest import TestCase

from app.hardware.relay_controller import *
from app.models import RelayState, Relay


class TestRelayController(TestCase):
    def setUp(self):
        self.relay = Relay(relay_code='R1', arduino_pin=13)

    def tearDown(self):
        pass

    def test_create_query(self):
        state = RelayState.PendingOn
        query = create_query(self.relay, state)
        self.assertEqual(query, '13_ON')

    def test_parse_response(self):
        response = parse_relay_state_response('13_ON---')
        self.assertEqual(response.pin, 13)
        self.assertEqual(response.state, RelayState.On)

    def test_switch(self):
        def check_response(relay, next_relay_state, response):
            self.assertEqual(response.pin, 13)
            self.assertEqual(response.state, RelayState.On)

        switch(self.relay, RelayState.PendingOn, check_response)

    def test_get_relay_state(self):
        def check_response(relay, response):
            self.assertEqual(response.pin, 13)
            self.assertIn(response.state, [RelayState.On, RelayState.Off])

        get_relay_state(self.relay, check_response)
