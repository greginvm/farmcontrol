from unittest import TestCase
from os import path, makedirs, remove, removedirs
import datetime as dt

from app.rrddb import *
from app.models import RRDDef, Measurement


def create_measurement(base_ts, delta_seconds, value):
    m = Measurement('DATA')
    m.value = value
    m.read_ts = base_ts + dt.timedelta(seconds=delta_seconds)
    return m


def insert_values(base_ts, nr, rrddef):
    m_last = None
    for i in xrange(nr):
        m_last = create_measurement(base_ts, i * 10, i)
        add(create_measurement(base_ts, i * 10, i), rrddef)
    return m_last


class TestRRDDB(TestCase):
    def setUp(self):
        self.def_statements = ['DS:data:GAUGE:60:-30:60', 'RRA:AVERAGE:0.5:1:20160',
                               'RRA:AVERAGE:0.5:2:86400', 'RRA:AVERAGE:0.5:30:35040']
        self.rrd_path = 'temp/data.rrd'
        self.rrddef = RRDDef(step=30, name='data', mmin=-30, mmax=60, definition='\n'.join(self.def_statements),
                             path=self.rrd_path)

        if not path.exists(path.dirname(self.rrd_path)):
            makedirs(path.dirname(self.rrd_path))

    def tearDown(self):
        if path.isfile(self.rrd_path):
            remove(self.rrd_path)

        if path.exists(path.dirname(self.rrd_path)):
            removedirs(path.dirname(self.rrd_path))

    def test_generate_definition(self):
        df = generate_definition(self.rrddef)

        # TODO: it actually checks characters (soo wrong)
        for s in self.rrddef.definition:
            self.assertIn(s, df)

    def test_generate_rra(self):
        rra = generate_rra(self.rrddef.step, cf='AVERAGE', days_to_keep=7, values_to_summarize=1)
        self.assertEqual(rra, 'RRA:AVERAGE:0.5:1:20160')

    def test_init(self):
        self.assertFalse(is_rrd_initialized(self.rrddef))
        init(self.rrddef)
        self.assertTrue(is_rrd_initialized(self.rrddef))

    def test_init_with_add(self):
        self.assertFalse(is_rrd_initialized(self.rrddef))
        base_ts = dt.datetime.utcnow()
        add(create_measurement(base_ts, 0, 10), self.rrddef)
        self.assertTrue(is_rrd_initialized(self.rrddef))

    def test_add(self):
        base_ts = dt.datetime.utcnow()
        m_last = insert_values(base_ts, 50, self.rrddef)

        info = rrdtool.info(self.rrddef.path)
        self.assertEqual(info['last_update'], timestamp(m_last.read_ts))
        print info

    def test_fetch(self):
        base_ts = dt.datetime.utcnow()
        insert_values(base_ts, 100, self.rrddef)
        print fetch_last(self.rrddef)
        to_dt = base_ts + datetime.timedelta(seconds=500)
        f = fetch(self.rrddef, cf='AVERAGE', resolution_td=datetime.timedelta(seconds=10),
                  period_td=datetime.timedelta(seconds=500),
                  to_dt=to_dt)

        self.assertEqual('data', f.name)
        print f.result

