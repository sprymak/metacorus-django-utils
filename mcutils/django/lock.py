import functools
import logging
from django.core import cache
from django.utils import timezone


logger = logging.getLogger(__name__)


class MutexError(Exception):
    pass


class mutually_exclusive(object):
    def __init__(self, lock_id, timeout=None, cache_alias=None,
                 fail_silently=False):
        self.lock_id = lock_id
        self.fail_silently = fail_silently
        self.timeout = timeout
        self.cache = cache.get_cache(cache_alias or cache.DEFAULT_CACHE_ALIAS)

    def __call__(self, func):
        return self.decorate_callable(func)

    def __enter__(self):
        if self.cache.has_key(self.lock_id):
            raise MutexError('Could not acquire lock: {0}'.format(self.lock_id))
        self.cache.add(self.lock_id, timezone.now(), self.timeout)

    def __exit__(self, *args):
        self.cache.delete(self.lock_id)

    def decorate_callable(self, func):
        """ Decorates a function with the mutex decorator by using this class
        as a context manager around it.
        """
        def wrapper(*args, **kwargs):
            try:
                with self:
                    return func(*args, **kwargs)
            except MutexError as e:
                logger.warn(e.message)
                if not self.fail_silently:
                    raise e

        functools.update_wrapper(wrapper, func)
        return wrapper
