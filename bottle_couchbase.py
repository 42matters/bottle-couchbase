import inspect
from Queue import Queue, Empty
from threading import Lock
import time

from bottle import PluginError
from couchbase.connection import Connection
from couchbase.exceptions import NetworkError, TimeoutError, CouchbaseError


class _ClientUnavailableError(Exception):
    pass


class _Pool(object):
    def __init__(self, initial=4, max_clients=100, tolerate_error=False, timeout_retries=2, **connargs):
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
        self._connargs = connargs
        self._clients_in_use = 0
        self._max_clients = max_clients
        self._tolerate_error = tolerate_error
        self._timeout_retries = max(0, timeout_retries)
        self._lock = Lock()

        try:
            for x in range(initial):
                self._q.put(self._make_client())
        except NetworkError:
            if not tolerate_error:
                raise

    def _make_client(self):
        for i in range(1 + self._timeout_retries):
            try:
                return Connection(**self._connargs)
            except TimeoutError:
                if i >= self._timeout_retries:
                    raise
                time.sleep(1)

    def _test_client(self, cb):
        try:
            cb.get('\u0fff', quiet=True)
            self._clients_in_use += 1
            return cb
        except CouchbaseError:
            if self._tolerate_error:
                return None
            else:
                raise

    def get_client(self, initial_timeout=0.1, next_timeout=30):
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
            return self._test_client(self._q.get(True, initial_timeout))
        except Empty:
            try:
                self._lock.acquire()
                if self._clients_in_use >= self._max_clients:
                    raise _ClientUnavailableError("Too many clients in use")
                return self._test_client(self._make_client())
            except NetworkError:
                if not self._tolerate_error:
                    raise
            except _ClientUnavailableError as e:
                try:
                    return self._test_client(self._q.get(True, next_timeout))
                except Empty:
                    raise e
            finally:
                self._lock.release()

    def release_client(self, cb):
        """
        Return a Connection object to the pool
        :param Connection cb: the client to release
        """
        if cb:
            self._q.put(cb, True)
            self._clients_in_use -= 1


class CouchbasePlugin(object):
    api = 2

    def __init__(self,
                 keyword='cb',
                 host='localhost',
                 bucket='default',
                 tolerate_error=False,
                 timeout_retries=2,
                 pooling=True, **kwargs):
        self.name = '/'.join(['couchbase', keyword, str(host), bucket])
        self.keyword = keyword
        self.host = host
        self.bucket = bucket
        self.kwargs = kwargs
        self.tolerate_error = tolerate_error
        self.timeout_retries = timeout_retries
        self.pooling = pooling
        self._pool = None

    def setup(self, app):
        for other in app.plugins:
            if not isinstance(other, CouchbasePlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another couchbase plugin with conflicting settings (non-unique keyword).")
        if self.pooling and self._pool is None:
            self._pool = _Pool(bucket=self.bucket,
                               host=self.host,
                               timeout_retries=self.timeout_retries,
                               tolerate_error=self.tolerate_error,
                               **self.kwargs)

    def apply(self, callback, route):
        args = inspect.getargspec(route.callback)[0]
        if self.keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            cb = None
            if self._pool:
                cb = self._pool.get_client()
            else:
                for _ in range(1 + self.timeout_retries):
                    try:
                        cb = Connection(bucket=self.bucket, host=self.host, **self.kwargs)
                        break
                    except TimeoutError:
                        time.sleep(1)
                    except NetworkError:
                        if self.tolerate_error:
                            break
                        else:
                            raise
            kwargs[self.keyword] = cb
            try:
                rv = callback(*args, **kwargs)
            finally:
                if self._pool and cb:
                    self._pool.release_client(cb)
            return rv

        return wrapper


Plugin = CouchbasePlugin
