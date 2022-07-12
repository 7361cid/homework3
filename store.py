import redis
import time


class RetrieException(Exception):
    pass


class Store:
    """
    Use Redis-x64-3.0.504
    """
    def __init__(self, retries=3, timeout=3):
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0, connection_pool=None)
        self.retries = retries
        self.timeout = timeout

    def set(self, key, value):
        return self.redis.set(key, value)

    def _get(self, key):
        return self.redis.get(key)

    def get(self, key):
        retries = self.retries
        while retries:
            try:
                return self._get(key)
            except redis.exceptions.ConnectionError:
                time.sleep(self.timeout)
                retries -= 1
        raise RetrieException

    def cache_get(self, key):
        """
        Отрабатывает в любом случае
        """
        try:
            self.get(key)
        except RetrieException:
            return 0

    def cache_set(self, key, value, time):
        self.set(key, value)
