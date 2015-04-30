from collections import deque

from flask import current_app

from ..models import StateWarning
from .. import date_util


class SensorState:
    def __init__(self, sensor):
        self.sensor = sensor
        self.measurements = deque(maxlen=sensor.observable_measurements)
        self.last_notification = None

    def update(self, measurement):

        # update sensor settings
        if measurement.sensor is not None:
            self.sensor = measurement.sensor

        # update collection to current size
        if len(self.measurements) != measurement.sensor.observable_measurements:
            self.measurements = deque(self.measurements,
                                      maxlen=self.sensor.observable_measurements)

        self.measurements.append(measurement)

    def check_alarming_values(self):
        """ Returns alarming values if there are any, else return None
        """
        now = date_util.datetime_now()

        # When was the last warning
        if self.last_notification is not None and self.sensor.warning_wait_minutes is not None and \
                        (now - self.last_notification).total_seconds() < self.sensor.warning_wait_minutes * 60:
            return None

        # Decide whether conditions are alarming and proceed
        # 1. Do we have enough measurements
        if len(self.measurements) < self.measurements.maxlen:
            return None

        # 2. Do we have enough alarming measurements
        alarming_low = [m for m in self.measurements if
                        self.sensor.is_value_too_low(m.value)]
        alarming_high = [m for m in self.measurements if self.sensor.is_value_too_high(m.value)]
        if (len(alarming_low) + len(alarming_high)) < self.sensor.observable_alarming_measurements:
            return None

        # State is alarming
        # Which value is alarming
        max_value = max(m.value for m in alarming_low + alarming_high)
        min_value = min(m.value for m in alarming_low + alarming_high)

        # clear measurements
        self.measurements.clear()

        warnings = []

        # Is it too low or too high or both (if limits are wrongly set)
        if self.sensor.is_value_too_low(min_value):
            warnings.append(StateWarning(limit=self.sensor.min_warning_value,
                                         value=min_value,
                                         created_ts=now,
                                         sensor=self.sensor,
                                         alarming_measurements=alarming_low))
            current_app.logger.info('Alarming values: too low %r' % (warnings[-1],))

        if self.sensor.is_value_too_high(max_value):
            warnings.append(StateWarning(limit=self.sensor.max_warning_value,
                                         value=max_value,
                                         created_ts=now,
                                         sensor=self.sensor,
                                         alarming_measurements=alarming_high))
            current_app.logger.info('Alarming values: too high %r' % (warnings[-1],))
        self.last_notification = now
        return warnings


CURRENT_SENSOR_STATES = {}


def update_and_get_warnings(measurement):
    current_state = CURRENT_SENSOR_STATES.setdefault(measurement.sensor.id,
                                                     SensorState(measurement.sensor))

    current_state.update(measurement)

    return current_state.check_alarming_values()
