from datetime import datetime, timedelta

from tzlocal import get_localzone


def epoch():
    return datetime.fromtimestamp(0)


def timestamp(naive_dt):
    return int((naive_dt - epoch()).total_seconds())


def datetime_now():
    return datetime.now()


def datetime_from_timestamp(seconds_since_epoch):
    return epoch() + timedelta(seconds=seconds_since_epoch)


def local_datetime_now():
    return to_local_datetime(datetime_now())


def to_local_datetime(naive_dt):
    tz = get_localzone()
    return tz.localize(naive_dt)
