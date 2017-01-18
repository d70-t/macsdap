# macsDAP

macsDAP is a wrapper around pydap which simplifies access to the macsServer.

## usage

macsDAP can be used as follows:

    import macsdap
    D = macsdap.MACSdap(key=<your API key>)
    ds = D[<dataset id>]
    imshow(ds.previewdata)

Please note that the preferred way of configuring macsDAP ist by using the configuration file as described below.

Multiple datasets can be loaded into one lazy xarray (this requires xarray and dask libraries to be installed):

    data = D.open_xarray(<iterable of dataset ids>)

Searching for data is also possible like the following:

    import datetime
    res = D.search(productType='calibrated_image', date_min=datetime.datetime(2014,9,5))
    imshow(res[5].previewdata)

It is also possible to get an xarray from a search result:

    data = res.to_xarray()
    # or if duplicate times should be elliminated automatically:
    data_without_duplicates = res.remove_overlapping_datasets().to_xarray()

For quick spectral preview, results provide a show() methos:

    D[<dataset id>].show()

## config

It is possible to create a configuration file in the users home directory, namely as:

    ~/.macs/macsdap.json

which may contain the key and/or the host to connect to using MACSdap:

    {
        "key": <your API key>,
        "host": <host to connect to>
    }

This allows to create the MACSdap instance simply by:

    import macsdap
    D = macsdap.MACSdap()

## requirements

Due to a missing root certificate in httplib2, currently a patched version of pydap is needed for https access.
It can be installed by:

    pip install git+git://github.com/d70-t/pydap

If you do the setup using pip, you should provide --process-dependency-links and it will automatically be installed:

    pip install --process-dependency-links git+ssh://git@git.die70.de/mim/macsdap.git
