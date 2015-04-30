from unittest import TestCase

from app.hardware.serial_monitor import *
from app.date_util import *


class TestSerialWatch(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_sensor_value(self):
        llap_stream = StringIO(u'aABT152.123-')
        base_ts = datetime.datetime.utcnow()
        m = get_sensor_value(llap_stream)

        self.assertTrue(m is not None)
        self.assertEqual(m.sensor_code, 'ABT')
        self.assertEqual(m.device_code, 'AB')
        self.assertEqual(m.measurement_code, 'T')
        self.assertAlmostEqual(m.value, 152.123)
        self.assertAlmostEqual(timestamp(m.read_ts), timestamp(base_ts))