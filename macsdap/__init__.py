# -*- coding: utf-8 -*-
import pydap.lib
import pydap.client
import os
import json
import httplib2
import datetime
import dateutil.tz as datetz

import macsdap.tools as tools

basedir = os.path.abspath(os.path.dirname(__file__))
CA_CERTS = os.path.join(basedir, 'cacerts.txt')
pydap.lib.CA_CERTS = CA_CERTS

class MACSdap(object):
    def __init__(self, key=None, host=None):
        if key is None or host is None:
            try:
                config = json.load(open(os.path.expanduser('~/.macs/macsdap.json')))
            except IOError:
                config = {}
            if key is None:
                key = config.get('key', None)
            if host is None:
                host = config.get('host', 'https://macsserver.physik.uni-muenchen.de')
        self.key = key
        self.host = host
        self._h = httplib2.Http(ca_certs = CA_CERTS)
    def _mkUrl(self, urlpart):
        url = self.host + urlpart
        if self.key is not None:
            url += '?key=%s'%self.key
        return url
    def _request(self, urlpart, *args, **kwargs):
        return self._h.request(self._mkUrl(urlpart), *args, **kwargs)
    def _getJSON(self, urlpart):
        _,data = self._request(urlpart)
        return json.loads(data)
    def __getitem__(self, oid):
        return MACSdapDS(oid, pydap.client.open_url(self._mkUrl('/dap/'+oid)))
    def search(self, **kwargs):
        kwargs = kwargs.copy()
        for k,v in kwargs.items():
            if isinstance(v, datetime.datetime):
                kwargs[k] = tools.date2seconds(v) * 1000.
        return SearchResult('/query/%s'%('/'.join('%s:%s'%i for i in sorted(kwargs.items()))), self)

class MACSdapDS(object):
    def __init__(self, oid, dataset):
        self._oid = oid
        self._dataset = dataset
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
    def show(self, fig1=1, fig2=2):
        import matplotlib.pyplot as plt
        plt.ion()
        fig1 = plt.figure(fig1)
        ax1 = fig1.add_subplot(111)
        ax1.imshow(self.previewdata[:].transpose(1,0,2))

        fig2 = plt.figure(fig2)
        ax2 = fig2.add_subplot(111)
        xmax, ymax = self.radiance.shape[:2]
        wvlCenter = self.wavelength[self.wavelength.shape[0]/2]
        ax2.set_xlabel('wavelength [%s]'%self.wavelength.units)
        ax2.set_ylabel('radiance [%s]'%self.radiance.units)
        def onclick(event):
            if not event.dblclick:
                return
            try:
                x = int(event.xdata)
                y = int(event.ydata)
            except TypeError:
                return
            if x >= 0 and x < xmax and y >= 0 and y < ymax:
                print 'loading spectrum @%d,%d'%(x,y)
                ax2.plot(wvlCenter, self.radiance[x,y], label='@%d,%d'%(x,y))
                print 'drawing...'
                fig2.canvas.draw()
        fig1.canvas.mpl_connect('button_press_event', onclick)

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
                key = key[:i] + (slice(None),)*(len(self.shape)-len(key)+1) + key[i+1:]
                break
        return self._variable[key][tuple((0 if isinstance(k,int) else slice(None)) for k in key)]
    def __dir__(self):
        return self._variable.attributes.keys() + dir(self._variable)

class SearchResult(object):
    def __init__(self, baseRequest, macsdap):
        self._baseRequest = baseRequest
        self._macsdap = macsdap
        data = self._macsdap._getJSON(baseRequest)
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
            data = self._macsdap._getJSON(self._baseRequest+'/OFS:%d/LIMIT:%d'%(ofs, step))
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
            raise IndexError('index %d not found in search result'%_index)
        data = self._macsdap._getJSON(self._baseRequest+'/OFS:%d/LIMIT:%d'%(index, 1))
        return self._macsdap[data['result'][0]['_oid']]
