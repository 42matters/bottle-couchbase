bottle-couchbase
================

This plugin simplifies the use of [Couchbase](http://www.couchbase.com/)
in your [Bottle](http://bottlepy.org/) applications.
Once installed, all you have to do is to add a ``cb`` keyword argument
(configurable name) to route callbacks that need a database connection.
The plugin is backed by a connection pool, so the connections will be reused
over multiple threads.

Installation
===============

Install with one of the following commands:
```shell
$ pip install bottle-couchbase
```

or download the latest version from github:

```shell
$ git clone git://github.com/42matters/bottle-couchbase.git
$ cd bottle-couchbase
$ python setup.py install
```

Usage
===============

Once installed to an application, the plugin passes an open
[couchbase.connection.Connection](http://www.couchbase.com/autodocs/couchbase-python-client-1.2.0/html/api/couchbase.html#couchbase.connection.Connection)
instance to all routes that require a ``cb`` keyword argument:
```python
from bottle import route, default_app
from bottle_couchbase import CouchbasePlugin
import time

application = default_app()
application.install(CouchbasePlugin(host='localhost', bucket='default'))

@route('/')
def index(cb):
    cb.set('now', time.time())
    return str(cb.get('now').value)

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=True)
```
Routes that do not expect a ``cb`` keyword argument are not affected.

Configuration
=============

The following configuration options exist for the plugin class:

* **keyword**: The keyword argument name that triggers the plugin (default: ``cb``)
* **initial** : Initial number of connections to create (default: ``4``)
* **max_clients** : Maximum number of connections to create.
If more connections are needed, the callback will be blocked until some other callbacks
release their connections (default: ``100``)
* **host**: Host on which the Couchbase server is located (default: ``localhost``), can also be a list of hosts
* **bucket** : Select the database to use (default: ``default``)
* Other arguments [couchbase.Couchbase.connect](http://www.couchbase.com/autodocs/couchbase-python-client-1.2.0/html/api/couchbase.html#couchbase.Couchbase.connect) takes
