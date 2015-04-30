import textwrap
from os.path import isfile
from datetime import timedelta

import rrdtool
from flask import current_app
from .models import RrdFetchResults
from .date_util import timestamp
from . import date_util


class RrdDefinitionException(Exception):
    pass


def _get_start_file_name(rrddef):
    return str(rrddef.path) + '.startts'


def generate_definition(rrddef):
    step = rrddef.step
    rras = []
    cfs = current_app.config['RRDTOOL_DEFAULT_CFS']
    for resolution in current_app.config['RRDTOOL_DATABASE_RESOLUTIONS']:
        for cf in cfs:
            rras.append(generate_rra(step, cf, resolution[1], resolution[0]))

    return '\n'.join(['DS:{name:s}:GAUGE:{missed:d}:{mmin:f}:{mmax:f}'.format(name=rrddef.name, missed=step * 2,
                                                                              mmin=rrddef.mmin,
                                                                              mmax=rrddef.mmax)] + rras)


def generate_rra(step, cf, days_to_keep, values_to_summarize):
    return 'RRA:{cf:s}:0.5:{values_to_summarize:d}:{rows:d}'.format(
        cf=cf, values_to_summarize=values_to_summarize,
        rows=(days_to_keep * 24 * 60 * 60) / (step * values_to_summarize))


def init(rrddef, start=None):
    if rrddef.step is None or not rrddef.step > 0:
        raise RrdDefinitionException('Step for RRD is not defined')

    if rrddef.path is None:
        raise RrdDefinitionException('Path for RRD is not defined')

    definition = generate_definition(rrddef)

    rrd_args = textwrap.dedent(definition).split('\n')
    rrd_args = filter(len, rrd_args)

    if start is not None:
        rrd_args.insert(0, '--start')
        rrd_args.insert(1, str(timestamp(start)))

    current_app.logger.info('Initializing RRD DB')

    if isfile(rrddef.path):
        current_app.logger.info('Using existing RRD DB')
    else:
        if start is not None:
            start_file = _get_start_file_name(rrddef)
            # write the timestamp
            with open(start_file, mode='w') as sf:
                sf.write(str(timestamp(start)))
        rrdtool.create(rrddef.path, '--step', str(rrddef.step), '--no-overwrite', *rrd_args)
        current_app.logger.info('RRD DB initialized')


def is_rrd_initialized(rrddef):
    return isfile(rrddef.path)


def add(measurement, rrddef):
    # Check if initialization is needed
    if not is_rrd_initialized(rrddef):
        # Warning at initialization with start time:
        # RRDtool will not accept any data timed before or at the time specified.
        # source: http://oss.oetiker.ch/rrdtool/doc/rrdcreate.en.html#___top

        init(rrddef, measurement.read_ts - timedelta(seconds=1))

    query = generate_update_query(measurement.read_ts, measurement.value)

    # current_app.logger.debug('Write command for RRD %s', query)

    rrdtool.update(rrddef.path, query)

    current_app.logger.log(6, 'Command %s written. Last inserted value in RRD at timestamp %s', query,
                           rrdtool.last(rrddef.path))


def generate_update_query(ts, value):
    return '{:d}:{:f}'.format(timestamp(ts), value)


def fetch_last(rrddef):
    info = rrdtool.info(rrddef.path)
    try:
        value = info['ds[%s].last_ds' % (rrddef.name,)]
    except ValueError, e:
        current_app.logger.exception(e)
        value = None
    ts = date_util.datetime_from_timestamp(int(info['last_update']))
    return ts, value


def fetch(rrddef, cf, period_td, resolution_td=None, to_dt=None, use_real_start=False):
    if to_dt is None:
        to_dt = date_util.datetime_now()

    if resolution_td is None:
        resolutions = current_app.config['RRDTOOL_DATABASE_RESOLUTIONS']
        possible_periods = [pair[0] for pair in resolutions if pair[1] >= period_td.days]
        if len(possible_periods) == 0:
            possible_periods = [resolutions[-1][0]]
        resolution_td = timedelta(seconds=rrddef.step * min(possible_periods))

    resolution = int(resolution_td.total_seconds())
    """
     end time == int(t/900)*900,
     start time == end time - 1hour,
     resolution == 900.
    """

    to_ts = int(timestamp(to_dt) / resolution) * resolution
    from_ts_base = to_ts - period_td.total_seconds()

    if use_real_start:
        if isfile(_get_start_file_name(rrddef)):
            # read the timestamp
            with open(_get_start_file_name(rrddef), 'r') as sf:
                from_ts_base = int(sf.read())

    from_ts = int(from_ts_base / resolution) * resolution

    assert (to_ts > from_ts)

    return RrdFetchResults(rrdtool.fetch(rrddef.path, cf, '-r', str(resolution), '-s', str(from_ts), '-e', str(to_ts)))
