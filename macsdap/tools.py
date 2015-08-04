# -*- coding: utf-8 -*-

import datetime
import urlparse
import dateutil.tz as datetz
import itertools
import numpy as np

_epoch = datetime.datetime(1970,1,1,0,0,0)
_epochUTC = datetime.datetime(1970,1,1,0,0,0, tzinfo=datetz.tzutc())

def date2seconds(t):
    try:
        return (t - _epoch).total_seconds()
    except TypeError:
        return (t - _epochUTC).total_seconds()

def alternate(*args):
    for iterable in itertools.izip_longest(*args):
        for item in iterable:
            if item is not None:
                yield item

def find_overlapping_indices(ranges):
    for i, (start1, end1) in enumerate(ranges):
        for j, (start2, end2) in enumerate(ranges[i+1:], i+1):
            if any([start2 >= start1 and start2 <= end1,
                    end2 >= start1 and end2 <= end1,
                    start1 >= start2 and start1 <= end2,
                    end1 >= start2 and end1 <= end2]):
                yield (i, j)

def netcdf_url(dapurl):
    parts = urlparse.urlparse(dapurl)
    query = parts.query.split("&")
    key = None
    for el in query:
        if el.startswith("key="):
            key = el[4:]
    if key is not None:
        key = key + ":a@"
    else:
        key = ""
    query = [el for el in query if not el.startswith("key=")]
    if query:
        query = "?" + "&".join(query)
    else:
        query = ""
    url = parts.scheme + "://" + key + parts.netloc + parts.path + query
    return url

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
