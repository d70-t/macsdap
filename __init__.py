# -*- coding: utf-8 -*-
import pydap.lib
import pydap.client
import os
import json
import httplib2
import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
CA_CERTS = os.path.join(basedir, 'cacerts.txt')
pydap.lib.CA_CERTS = CA_CERTS

class MACSdap(object):
    def __init__(self, key=None, host='https://macsserver.physik.uni-muenchen.de'):
        self.key = key
        self.host = host
    def __getitem__(self, oid):
        url = '%s/dap/%s'%(self.host, oid)
        if self.key is not None:
            url += '?key=%s'%self.key
        return MACSdapDS(pydap.client.open_url(url))
    def search(self, **kwargs):
        kwargs = kwargs.copy()
        for k,v in kwargs.items():
            if isinstance(v, datetime.datetime):
                kwargs[k] = (v - datetime.datetime(1970,1,1,0,0,0)).total_seconds()*1000.
        url = '%s/query/%s'%(self.host, '/'.join('%s:%s'%i for i in sorted(kwargs.items())))
        if self.key is not None:
            url += '?key=%s'%self.key
        return SearchResult(url, self)

class MACSdapDS(object):
    def __init__(self, dataset):
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
        return self._variable[key][tuple((0 if isinstance(k,int) else slice(None)) for k in key)]
    def __dir__(self):
        return dir(self._variable)

class SearchResult(object):
    def __init__(self, baseRequest, macsdap):
        self._baseRequest = baseRequest
        self._macsdap = macsdap
        self.h = httplib2.Http(ca_certs = CA_CERTS)
        (resp, content) = self.h.request(baseRequest, 'GET')
        data = json.loads(content)
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
            (resp, content) = self.h.request(self._baseRequest+'/OFS:%d/LIMIT:%d'%(ofs, step), 'GET')
            data = json.loads(content)
            if len(data['result']) == 0:
                break
            for i, res in enumerate(data['result'], ofs):
                if self._limit is not None and i >= self._limit:
                    return
                yield self._macsdap[res['_oid']]
            ofs = data['stop']
    def __getitem__(self, index):
        (resp, content) = self.h.request(self._baseRequest+'/OFS:%d/LIMIT:%d'%(index, 1), 'GET')
        data = json.loads(content)
        return self._macsdap[data['result'][0]['_oid']]
