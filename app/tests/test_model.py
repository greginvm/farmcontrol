from unittest import TestCase

from app.models import *


class TestModel(TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_to_json(self):
        # TODO:
        pass

    def test_sensor(self):
        s = Sensor()
        s.rrd_db_path = '../debug/zgt.rrd'

        print s.can_save_into_rrddb()

        print path.dirname(s.rrd_db_path)
