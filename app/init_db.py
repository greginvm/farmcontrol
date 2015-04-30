# -*- coding: utf-8 -*-
"""
Sets the default DB rows
"""
from models import Sensor, SensorType, Device, Contact, Relay, User


def init(db):
    try:
        db.session.query(SensorType).delete()
        db.session.query(Device).delete()
        db.session.query(Sensor).delete()
        db.session.query(Contact).delete()
        db.session.query(Relay).delete()
    except:
        pass

    st_t = SensorType(unit=u'°C', description=u'Temperatura', name='temperature')
    st_h = SensorType(unit=u'%', description=u'Vlažnost', name='humidity')
    st_b = SensorType(unit=u'V', description=u'Baterija', name='battery')

    d_zg = Device(description='Zgoraj')
    d_sp = Device(description='Spodaj')

    zgt = Sensor(sensor_code='ZGT', description='Temperatura (zgoraj)',
                 max_possible_value=40, max_warning_value=33,
                 min_possible_value=-10, min_warning_value=20,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=True, device=d_zg, type=st_t,
                 emit_every=5)

    zgb = Sensor(sensor_code='ZGB', description='Baterija (zgoraj)',
                 max_possible_value=6,
                 min_possible_value=0, min_warning_value=3.3,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=True, device=d_zg, type=st_b,
                 emit_every=10)

    spb = Sensor(sensor_code='SPB', description='Baterija (spodaj)',
                 max_possible_value=6,
                 min_possible_value=0, min_warning_value=3.3,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=True, device=d_sp, type=st_b,
                 emit_every=10)

    spt = Sensor(sensor_code='SPT', description='Temperatura (spodaj)',
                 max_possible_value=40, max_warning_value=34,
                 min_possible_value=-10, min_warning_value=20,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=True, device=d_sp, type=st_t,
                 emit_every=5)

    zgh = Sensor(sensor_code='ZGH', description=u'Vlažnost (zgoraj)',
                 max_possible_value=100, max_warning_value=90,
                 min_possible_value=0, min_warning_value=10,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=False, device=d_zg, type=st_h,
                 emit_every=5)

    sph = Sensor(sensor_code='SPH', description=u'Vlažnost (spodaj)',
                 max_possible_value=100, max_warning_value=90,
                 min_possible_value=0, min_warning_value=10,
                 observable_measurements=3, observable_alarming_measurements=2,
                 enable_warnings=False, device=d_sp, type=st_h,
                 emit_every=5)

    c = Contact(name='Admin', phone='+123456789', email='admin')
    user = User(email='admin')
    user.password = 'admin'
    user.ping()

    for l in ['A', 'B']:
        for i in range(8):
            code = '%s%d' % (l, i)
            description = 'Rele %s' % code
            db.session.add(Relay(description=description, switch_on_text='ON', switch_off_text='OFF'))

    db.session.add(zgt)
    db.session.add(spt)
    db.session.add(zgh)
    db.session.add(sph)
    db.session.add(spb)
    db.session.add(zgb)
    db.session.add(c)
    db.session.add(user)

    db.session.commit()

