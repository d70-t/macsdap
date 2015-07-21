# macsDAP

macsDAP is a wrapper around pydap which simplifies access to the macsServer.

## usage

    import macsdap
    D = macsdap.MACSdap(key=<your API key>)
    ds = D[<dataset id>]
    imshow(ds.previewdata)

Searching for data is also possible like the following:

    import datetime
    res = D.search(productType='calibrated_image', date_min=datetime.datetime(2014,9,5))
    imshow(res[5].previewdata)

For quick spectral preview, results provide a show() methos:

    D[<dataset id>].show()

## requirements

Due to a missing root certificate in httplib2, currently a patched version of pydap is needed for https access.
It can be installed by:

    pip install git+git://github.com/d70-t/pydap

If you do the setup using pip, you should provide --process-dependency-links and it will automatically be installed:

    pip install --process-dependency-links git+ssh://git@git.die70.de:mim/macsdap.git
