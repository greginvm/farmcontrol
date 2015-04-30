from datetime import datetime, date, timedelta

import date_util


def custom_encode(obj):
    if isinstance(obj, datetime):
        return date_util.timestamp(obj)
    elif isinstance(obj, date):
        return date_util.timestamp(obj)
    elif isinstance(obj, timedelta):
        return timedelta.total_seconds()
    elif isinstance(obj, unicode):
        return obj.encode('utf-8')
    raise NotImplementedError('Custom encoder not implemented')


class ModelJSONAPIMixin():
    def to_json_dict(self):
        pass


def to_json_dict(sth):
    if hasattr(sth, 'to_json_dict'):
        sth = encode_dict(sth.to_json_dict())
    else:
        sth = [encode_dict(r.to_json_dict()) for r in sth]
    return sth


def encode_dict(d, included_keys=None):
    d_copy = {}
    for k, v in d.items():
        if included_keys is None or k in included_keys:
            temp = v
            try:
                d_copy[k] = custom_encode(v)
            except:
                d_copy[k] = temp
    return d_copy
