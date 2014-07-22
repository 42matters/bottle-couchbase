import inspect
from bottle import PluginError
from couchbase.connection import Connection
from Queue import Queue, Empty
from threading import Lock


class _ClientUnavailableError(Exception):
    pass


class _Pool(object):
    def __init__(self, initial=4, max_clients=100, **connargs):
        """
        Create a new pool
        :param int initial: The initial number of client objects to create
        :param int max_clients: The maximum amount of clients to create. These
          clients will only be created on demand and will potentially be
          destroyed once they have been returned via a call to
          :meth:`release_client`
        :param connargs: Extra arguments to pass to the Connection object's
        constructor
        """

        if initial <= 0:
            initial = 1

        if max_clients <= initial:
            max_clients = initial + 1

        self._q = Queue()
        self._l = []
        self._connargs = connargs
        self._cur_clients = 0
        self._max_clients = max_clients
        self._lock = Lock()

        for x in range(initial):
            self._q.put(self._make_client())
            self._cur_clients += 1

    def _make_client(self):
        ret = Connection(**self._connargs)
        self._l.append(ret)
        return ret

    def get_client(self, initial_timeout=0.05, next_timeout=200):
        """
        Wait until a client instance is available
        :param float initial_timeout:
          how long to wait initially for an existing client to complete
        :param float next_timeout:
          if the pool could not obtain a client during the initial timeout,
          and we have allocated the maximum available number of clients, wait
          this long until we can retrieve another one

        :return: A connection object
        """
        try:
            return self._q.get(True, initial_timeout)
        except Empty:
            try:
                self._lock.acquire()
                if self._cur_clients == self._max_clients:
                    raise _ClientUnavailableError("Too many clients in use")
                cb = self._make_client()
                self._cur_clients += 1
                return cb
            except _ClientUnavailableError as ex:
                try:
                    return self._q.get(True, next_timeout)
                except Empty:
                    raise ex
            finally:
                self._lock.release()

    def release_client(self, cb):
        """
        Return a Connection object to the pool
        :param Connection cb: the client to release
        """
        self._q.put(cb, True)


class CouchbasePlugin(object):
    name = 'couchbase'
    api = 2

    def __init__(self, keyword='cb', host='localhost', bucket='default', **kwargs):
        self.keyword = keyword
        self.host = host
        self.bucket = bucket
        self.kwargs = kwargs
        self._pool = None

    def setup(self, app):
        for other in app.plugins:
            if not isinstance(other, CouchbasePlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another couchbase plugin with conflicting settings (non-unique keyword).")
        if self._pool is None:
            self._pool = _Pool(bucket=self.bucket,
                               host=self.host,
                               **self.kwargs)

    def apply(self, callback, route):
        conf = route.config.get('couchbase') or {}
        args = inspect.getargspec(route.callback)[0]
        keyword = conf.get('keyword', self.keyword)
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            cb = self._pool.get_client()
            kwargs[self.keyword] = cb
            try:
                rv = callback(*args, **kwargs)
            finally:
                self._pool.release_client(cb)
            return rv
        return wrapper

Plugin = CouchbasePlugin
