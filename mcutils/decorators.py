import functools
import inspect


class cached_property(object):
    """ Decorator for read-only properties evaluated only once within TTL
    period.

    It can be used to created a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):

            # create property whose value is cached for ten minutes
            @cached_property(ttl=600)
            def randint(self):
                # will only be evaluated every 10 min. at maximum.
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object instance that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    The default time-to-live (TTL) is 300 seconds (5 minutes). Set the TTL to
    zero for the cached value to never expire.

    To expire a cached property value manually just do::

        del instance._cache[<property name>]

    (c) 2011 Christopher Arndt, MIT License
    """
    def __init__(self, ttl=300):
        self.ttl = ttl

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        import time
        now = time.time()
        try:
            value, last_update = inst._cache[self.__name__]
            if self.ttl > 0 and now - last_update > self.ttl:
                raise AttributeError
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = (value, now)
        return value


def naive_memoize(function):
    "Standard memoization decorator."
    name = function.__name__
    _name = '_' + name

    def method(self):
        if not hasattr(self, _name):
            value = function(self)
            setattr(self, _name, value)
        return getattr(self, _name)

    def invalidate():
        if hasattr(method, _name):
            delattr(method, _name)

    method.__name__ = function.__name__
    method.__doc__ = function.__doc__
    method._invalidate = invalidate
    return method


def decorator(func):
    """ This decorator can be used to turn simple functions or callable objects
    into well-behaved decorators, so long as the decorators are fairly simple.
    Allows to use decorator either with arguments or not.

    Usage::

        @decorator
        def apply(func, *args, **kw):
            return func(*args, **kw)

        @decorator
        class apply:
            def __init__(self, *args, **kw):
                self.args = args
                self.kw   = kw

            def __call__(self, func):
                return func(*self.args, **self.kw)

        @apply
        def test():
            return 'test'

        @apply(2, 3)
        def test(a, b):
            return a + b

        assert test == 5

    Note. There is only one drawback: wrapper checks its arguments for single
    function or class. To avoid wrong behavior you can use keyword arguments
    instead of positional

    Links
        * http://wiki.python.org/moin/PythonDecoratorLibrary
    """

    def _is_func_arg(*args, **kw):
        return len(args) == 1 and len(kw) == 0 and (
            inspect.isfunction(args[0]) or isinstance(args[0], type))

    if isinstance(func, type):
        def class_wrapper(*args, **kw):
            if _is_func_arg(*args, **kw):
                return func()(*args, **kw)  # create class before usage
            return func(*args, **kw)
        class_wrapper.__name__ = func.__name__
        class_wrapper.__module__ = func.__module__
        return class_wrapper

    @functools.wraps(func)
    def func_wrapper(*args, **kw):
        if _is_func_arg(*args, **kw):
            return func(*args, **kw)

        def functor(userFunc):
            return func(userFunc, *args, **kw)

        return functor

    return func_wrapper


def deprecated(func):
    """ Decorator to be used to mark functions as deprecated.
    It will result in a warning being emitted when the function is used.

    Usage::

        @other_decorators_must_be_upper
        @deprecated
        def some_old_function(x,y):
            return x + y

        class SomeClass:

            @deprecated
            def some_old_method(self, x,y):
                return x + y
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        import warnings
        warnings.warn_explicit("Call to deprecated function %(funcname)s." % {
                'funcname': func.__name__,
            },
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)

    return new_func


class memoize(object):
    """ Decorator to cache a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.

    Usage::

         @memoize
         def fibonacci(n):
            if n in (0, 1):
               return n
            return fibonacci(n-1) + fibonacci(n-2)
    """

    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)

    def __repr__(self):
        """ Return the function's docstring. """
        return self.func.__doc__

    def __get__(self, obj, objtype):
        """ Support instance methods. """
        return functools.partial(self.__call__, obj)
