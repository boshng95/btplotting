from datetime import datetime
import logging
import math
from typing import Dict, Optional, List, Union

import backtrader as bt

import pandas
import itertools


_logger = logging.getLogger(__name__)


def paramval2str(name, value):
    if value is None:
        return 'None'
    elif name == "timeframe":
        return bt.TimeFrame.getname(value, 1)
    elif isinstance(value, str):
        return value
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, list):
        return ','.join(value)
    elif isinstance(value, type):
        return value.__name__
    else:
        return f"{value:.2f}"


def get_nondefault_params(params: object) -> Dict[str, object]:
    return {key: params._get(key) for key in params._getkeys() if not params.isdefault(key)}


def get_params(params: bt.AutoInfoClass):
    return {key: params._get(key) for key in params._getkeys()}


def get_params_str(params: Optional[bt.AutoInfoClass]) -> str:
    user_params = get_nondefault_params(params)
    plabs = [f"{x}: {paramval2str(x, y)}" for x, y in user_params.items()]
    plabs = '/'.join(plabs)
    return plabs


def nanfilt(x: List) -> List:
    """filters all NaN values from a list"""
    return [value for value in x if not math.isnan(value)]


def convert_by_line_clock(line, line_clk, new_clk):
    """Takes a clock and generates an appropriate line with a value for each entry in clock. Values are taken from another line if the
    clock value in question is found in its line_clk. Otherwise NaN is used"""
    if new_clk is None:
        return line

    new_line = []
    next_idx = len(line_clk) - 1
    for sc in new_clk:
        for i in range(next_idx, -1, -1):  # run from next_idx to -1 (-1 so we actually also catch index 0!)
            v = line_clk[-i]
            if sc == v:
                # exact hit
                new_line.append(line[-i])
                next_idx = i
                break
        else:
            new_line.append(float('nan'))
    return new_line


def convert_to_pandas(strat_clk, obj: bt.LineSeries, start: datetime = None, end: datetime = None, name_prefix: str = "", num_back=None) -> pandas.DataFrame:
    lines_clk = obj.lines.datetime.plotrange(start, end)

    df = pandas.DataFrame()
    # iterate all lines
    for lineidx in range(obj.size()):
        line = obj.lines[lineidx]
        linealias = obj.lines._getlinealias(lineidx)
        if linealias == 'datetime':
            continue

        # get data limited to time range
        data = line.plotrange(start, end)

        ndata = convert_by_line_clock(data, lines_clk, strat_clk)

        df[name_prefix + linealias] = ndata

    df[name_prefix + 'datetime'] = [bt.num2date(x) for x in strat_clk]
    return df


def get_data_obj(obj):
    """obj can be a data object or just a single line (in case indicator was created with an explicit line)"""
    if obj._owner is not None:
        return obj._owner
    else:
        return obj


def find_by_plotid(strategy: bt.Strategy, plotid):
    objs = itertools.chain(strategy.datas, strategy.getindicators(), strategy.getobservers())
    founds = []
    for obj in objs:
        if getattr(obj.plotinfo, 'ploftid', None) == plotid:
            founds.append(obj)

    num_results = len(founds)
    if num_results == 0:
        return None
    elif num_results == 1:
        return founds[0]
    else:
        raise RuntimeError(f'Found multiple objects with plotid "{plotid}"')