# -*- coding: utf-8 -*-

import datetime
import dateutil.tz as datetz
import itertools
import numpy as np

_epoch = datetime.datetime(1970,1,1,0,0,0)
_epochUTC = datetime.datetime(1970,1,1,0,0,0, tzinfo=datetz.tzutc())

def date2seconds(t):
    try:
        return (t - _epoch).total_seconds()
    except TypeError:
        return (t - _epochUtc).total_seconds()

def alternate(*args):
    for iterable in itertools.izip_longest(*args):
        for item in iterable:
            if item is not None:
                yield item

class Locator(object):
    def __init__(self, D, **search):
        self.search = search
        self.D = D
        self.tofs = datetime.timedelta(minutes=5)
    def at(self, t):
        ts = date2seconds(t)
        search = self.search.copy()
        search['date_min'] = t-self.tofs
        search['date_max'] = t+self.tofs
        res = list(self.D.search(**search))
        splitpoint = int(len(res)/2)
        for r in alternate(reversed(res[:splitpoint]), res[splitpoint:]):
            time = r.time[:]
            if time[0] <= ts and time[-1] >= ts:
                return r, np.argmin(np.abs(time-ts))
