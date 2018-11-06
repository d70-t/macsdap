# -*- coding: utf-8 -*-
import pydap.lib
import pydap.client
import numpy as np
import os
import json
import httplib2
import datetime
import dateutil.tz as datetz

import macsdap.tools as tools

try:
    import xarray as xr
except ImportError:
    def urls2xarray(_, _2):
        raise ImportError("xarray not found!")
else:
    def preprocess_arrays(array):
        if 'time' not in array.dims and 'frames' in array.dims:
            array = array.swap_dims({'frames': 'time'})
        if 'time' not in array.dims and 'samples' in array.dims:
            array = array.swap_dims({'samples': 'time'})
        return array

    def urls2xarray(urls, engine='pydap'):
        if 'netcdf' in engine.lower():
            urls = map(tools.netcdf_url, urls)
            array = xr.open_mfdataset(urls, preprocess=preprocess_arrays, concat_dim="time")
        else:
            array = xr.open_mfdataset(urls, preprocess=preprocess_arrays, concat_dim="time", engine=engine)
        return array

BASEDIR = os.path.abspath(os.path.dirname(__file__))
CA_CERTS = os.path.join(BASEDIR, 'cacerts.txt')
pydap.lib.CA_CERTS = CA_CERTS


class MACSdapException(Exception):
    ''' General MACSdap exception '''


class MACSdapServerError(MACSdapException):
    ''' Error which occured on the server '''


class MACSdap(object):
    def __init__(self, key=None, host=None):
        if key is None and host is None:
            config_path = os.path.expanduser('~/.macs/macsdap.json')
            try:
                config = json.load(open(config_path))
            except IOError:
                config = {}
            if key is None:
                key = config.get('key', None)
        if host is None:
            try:
                host = config['host']
            except KeyError:
                host = 'https://macsserver.physik.uni-muenchen.de'
        self.key = key
        self.host = host
        self._h = httplib2.Http(ca_certs=CA_CERTS)

    def _mkUrl(self, urlpart):
        url = self.host + urlpart
        if self.key is not None:
            url += '?key=%s' % self.key
        return url

    def _request(self, urlpart, *args, **kwargs):
        return self._h.request(self._mkUrl(urlpart), *args, **kwargs)

    def _getJSON(self, urlpart):
        _, data = self._request(urlpart)
        return json.loads(data)

    def __getitem__(self, oid):
        url = self._mkUrl('/dap/'+oid)
        return MACSdapDS(oid, pydap.client.open_url(url), url)

    def search(self, **kwargs):
        kwargs = kwargs.copy()
        for k, v in kwargs.items():
            if isinstance(v, datetime.datetime):
                kwargs[k] = tools.date2seconds(v) * 1000.
            if isinstance(v, np.datetime64):
                kwargs[k] = (v - np.datetime64("1970-01-01")) / np.timedelta64(1, "ms")
        query_args = ['%s:%s' % i for i in sorted(kwargs.items())]
        return LazySearchResult('/query/%s' % ('/'.join(query_args)), self)

    def open_xarray(self, oids, engine='pydap'):
        return urls2xarray([self._mkUrl('/dap/'+oid) for oid in oids], engine)


class MACSdapDS(object):
    def __init__(self, oid, dataset, url):
        self._oid = oid
        self._dataset = dataset
        self._url = url

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return getattr(self._dataset, name)

    def __getitem__(self, key):
        return MACSdapVariable(self._dataset[key])

    def __repr__(self):
        return repr(self._dataset)

    def __str__(self):
        return str(self._dataset)

    def __dir__(self):
        return dir(self._dataset) + self._dataset.keys()

    def __hash__(self):
        return int(self._oid, 16)

    def __eq__(self, other):
        return self._oid == other._oid

    def to_xarray(self, engine='pydap'):
        return urls2xarray([self._url], engine)

    def show(self, fig1_no=1, fig2_no=2):
        import matplotlib.pyplot as plt
        plt.ion()
        fig1 = plt.figure(fig1_no)
        ax1 = fig1.add_subplot(111)
        previewdata = np.array(self.previewdata).transpose(1, 0, 2)
        if previewdata.shape[-1] == 1:
            previewdata = previewdata[...,0]
        ax1.imshow(previewdata)

        fig2 = plt.figure(fig2_no)
        ax2 = fig2.add_subplot(111)
        xmax, ymax = self.radiance.shape[:2]
        wvlCenter = np.array(self.wavelength[self.wavelength.shape[0]/2])
        ax2.set_xlabel('wavelength [%s]' % self.wavelength.units)
        ax2.set_ylabel('radiance [%s]' % self.radiance.units)

        def onclick(event):
            if not event.dblclick:
                return
            try:
                x = int(event.xdata)
                y = int(event.ydata)
            except TypeError:
                return
            if x >= 0 and x < xmax and y >= 0 and y < ymax:
                print 'loading spectrum @%d,%d' % (x, y)
                data = np.array(self.radiance[x, y])
                ax2.plot(wvlCenter,
                         data,
                         label='@%d,%d' % (x, y))
                print 'drawing...'
                fig2.canvas.draw()

        fig1.canvas.mpl_connect('button_press_event', onclick)

    @property
    def oid(self):
        return self._oid

    @property
    def dapurl(self):
        return self._url

    @property
    def netcdf_url(self):
        return tools.netcdf_url(self.dapurl)

class MACSdapVariable(object):
    def __init__(self, variable):
        self._variable = variable

    def __getattr__(self, name):
        return getattr(self._variable, name)

    def __getitem__(self, key):
        if not isinstance(key, tuple):
            key = (key,)
        for i, el in enumerate(key):
            if el is Ellipsis:
                key = key[:i] \
                      + (slice(None),)*(len(self.shape)-len(key)+1) \
                      + key[i+1:]
                break
        var_slice = tuple((0 if isinstance(k, int) else slice(None))
                          for k in key)
        return self._variable[key][var_slice]

    def __len__(self):
        return self.shape[0]

    def __dir__(self):
        return self._variable.attributes.keys() + dir(self._variable)


class _SearchResult(object):
    def __len__(self):
        return self.count

    def to_xarray(self, engine='pydap'):
        return urls2xarray([ds.dapurl for ds in self], engine)

    def remove_overlapping_datasets(self):
        datasets = list(self)
        timespans = [ds.time[::len(ds.time)-1] for ds in datasets]
        while True:
            for idx1, idx2 in tools.find_overlapping_indices(timespans):
                len1 = len(datasets[idx1].time)
                len2 = len(datasets[idx2].time)
                if len1 < len2:
                    to_remove = idx1
                else:
                    to_remove = idx2
                del datasets[to_remove]
                del timespans[to_remove]
                duplicates = tools.find_overlapping_indices(timespans)
                break
            else:
                break
        return StrictSearchResult(datasets)


class StrictSearchResult(_SearchResult):
    def __init__(self, datasets):
        self._datasets = datasets

    @property
    def count(self):
        return len(self._datasets)

    def limit(self, limit):
        self._datasets = self._datasets[:limit]
        return self

    def __iter__(self):
        return iter(self._datasets)

    def __getitem__(self, index):
        return self._datasets[index]

class LazySearchResult(_SearchResult):
    def __init__(self, baseRequest, macsdap):
        self._baseRequest = baseRequest
        self._macsdap = macsdap
        data = self._macsdap._getJSON(baseRequest)
        if 'error' in data:
            raise MACSdapServerError("{} while requesting: \"{}\"".format(data['error'], baseRequest))
        self._count = data['count']
        self._limit = None

    @property
    def count(self):
        if self._limit is None:
            return self._count
        else:
            return min(self._limit, self._count)

    def limit(self, limit):
        self._limit = limit
        return self

    def __iter__(self):
        ofs = 0
        step = 20
        while True:
            request = self._baseRequest+'/OFS:%d/LIMIT:%d' % (ofs, step)
            data = self._macsdap._getJSON(request)
            if len(data['result']) == 0:
                break
            for i, res in enumerate(data['result'], ofs):
                if self._limit is not None and i >= self._limit:
                    return
                yield self._macsdap[res['_oid']]
            ofs = data['stop']

    def __getitem__(self, index):
        _index = index
        if index < 0:
            index = self.count + index
        if index < 0 or index >= self.count:
            raise IndexError('index %d not found in search result' % _index)
        request = self._baseRequest+'/OFS:%d/LIMIT:%d' % (index, 1)
        data = self._macsdap._getJSON(request)
        return self._macsdap[data['result'][0]['_oid']]
