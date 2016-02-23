# number of bytes taken from /dev/urandom
RANDOM_ID_SOURCE_BYTES = 7

# from april fool's rfc 1924
BASE85 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' \
    '!#$%&()*+-;<=>?@^_`{|}~'

# rfc4648 alphabets
BASE16 = BASE85[:16]
BASE32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
BASE32HEX = BASE85[:32]
BASE64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
BASE64URL = BASE64[:62] + '-_'

# http://en.wikipedia.org/wiki/Base_62 useful for url shorteners
BASE62 = BASE85[:62]


class NumConv(object):
    """ Class to create converter objects.

        :param radix: The base that will be used in the conversions.
           The default value is 10 for decimal conversions.
        :param alphabet: A string that will be used as a encoding alphabet.
           The length of the alphabet can be longer than the radix. In this
           case the alphabet will be internally truncated.

           The default value is :data:`numconv.BASE85`

        :raise TypeError: when *radix* isn't an integer
        :raise ValueError: when *radix* is invalid
        :raise ValueError: when *alphabet* has duplicated characters
    """

    def __init__(self, radix=10, alphabet=BASE85):
        if int(radix) != radix:
            raise TypeError('radix must be an integer')
        if not 2 <= radix <= len(alphabet):
            raise ValueError('radix must be >= 2 and <= %d' % (
                len(alphabet), ))
        self.radix = radix
        self.alphabet = alphabet
        self.cached_map = dict(zip(self.alphabet, range(len(self.alphabet))))
        if len(self.cached_map) != len(self.alphabet):
            raise ValueError("duplicate characters found in '%s'" % (
                self.alphabet, ))

    def int2str(self, num):
        """ Converts an integer into a string.

            Example usage:

            .. code-block:: python

               # 3735928559 to hexadecimal
               >> NumConv(16).int2str(3735928559)
               'DEADBEEF'

               # 19284 to binary
               >> NumConv(2).int2str(19284)
               '100101101010100'

               # 37 to base 4 using a custom dictionary
               >> NumConv(4, 'rofl').int2str(37)
               'foo'

               # Very large number to :data:`~numconv.BASE85`
               >> NumConv(85).int2str(2693233728041137L)
               '~123AFz@'

            Arguments:

            :param num: A numeric value to be converted to another base as a
                string.
            :returns: string
            :raise TypeError: when *num* isn't an integer
            :raise ValueError: when *num* isn't positive
        """
        if int(num) != num:
            raise TypeError('number must be an integer')
        if num < 0:
            raise ValueError('number must be positive')
        radix, alphabet = self.radix, self.alphabet
        if (radix in (8, 10, 16) and
                alphabet[:radix].lower() == BASE85[:radix].lower()):
            return ({8: '%o', 10: '%d', 16: '%x'}[radix] % num).upper()
        ret = ''
        while True:
            ret = alphabet[num % radix] + ret
            if num < radix:
                break
            num //= radix
        return ret

    def str2int(self, num):
        """ Converts a string into an integer.

            If possible, the built-in python conversion will be used for speed
            purposes.

            Example usage:

            .. code-block:: python

               # Hexadecimal 'DEADBEEF' to integer
              >> NumConv(16).str2int('DEADBEEF')
              3735928559L

               # Binary '100101101010100' to integer
               >> NumConv(2).str2int('100101101010100')
               19284

               # Base 4 with custom encoding 'foo' to integer
               >> NumConv(4, 'rofl').str2int('foo')
               37

               # :data:`~numconv.BASE85` '~123AFz@' to integer
               >> NumConv(85).str2int('~123AFz@')
               2693233728041137L

            :param num: A string that will be converted to an integer.
            :rtype: integer
            :raise ValueError: when *num* is invalid
        """
        radix, alphabet = self.radix, self.alphabet
        if radix <= 36 and alphabet[:radix].lower() == BASE85[:radix].lower():
            return int(num, radix)
        ret = 0
        lalphabet = alphabet[:radix]
        for char in num:
            if char not in lalphabet:
                raise ValueError("invalid literal for radix2int() with radix "
                    "%d: '%s'" % (radix, num))
            ret = ret * radix + self.cached_map[char]
        return ret


class Final(type):
    """ Metaclass for 'sealed' classes. A sealed class cannot be extended.
        Origin: BruceEckel / Python 3 Patterns & Idioms: Metaclasses
    """

    def __new__(cls, name, bases, classdict):
        for b in bases:
            if isinstance(b, Final):
                raise TypeError("type '%s' is not an acceptable base type" %
                    b.__name__)
        return type.__new__(cls, name, bases, dict(classdict))


def datetime_as_iso(value):
    """Helper function to format datetime object to ISO8601 string."""
    import datetime
    if not isinstance(value, datetime.datetime):
        return ""
    retval = value.strftime("%Y-%m-%dT%H:%M:%S%z")
    if not value.utcoffset():
        return "".join([retval, "Z"])
    return retval


def int2str(num, radix=10, alphabet=BASE85):
    """ Helper for quick base conversions from integers to strings """
    return NumConv(radix, alphabet).int2str(num)


def str2int(num, radix=10, alphabet=BASE85):
    """ Helper for quick base conversions from strings to integers. """
    return NumConv(radix, alphabet).str2int(num)


def clean_int(value, default, min_value=None, max_value=None):
    """ Helper to cast value to int and to clip it to min or max_value.

        Arguments:

        :param value: any value (preferably something that can be casted
            to ``int``).
        :param default: default value to be used when type casting fails.
        :param min_value: minimum allowed value.
        :param max_value: maximum allowed value.

        :returns:
            An integer between min_value and max_value.
    """
    if not isinstance(value, (int, long)):
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default
    if min_value is not None:
        value = max(min_value, value)
    if max_value is not None:
        value = min(value, max_value)
    return value


def str_to_bool(v):
    return v.strip().lower() in ("yes", "true", "on", "1")


def ip4_to_int(ip):
    """ Convert string contained valid IP4 address to 32-bit integer.
        >>> ip4_to_int("192.168.0.1")
        3232235521L
    """
    ip = ip.rstrip().split('.')
    ipn = 0
    while ip:
        ipn = (ipn << 8) + int(ip.pop(0))
    return ipn


def ip4_to_str(ip):
    """ Convert integer contained valid IP4 address to string.
        >>> ip4_to_str(3232235521)
        '192.168.0.1'
    """
    ips = ''
    for i in range(4):
        ip, n = divmod(ip, 256)
        ips = str(n) + '.' + ips
    return ips[:-1]  # take out extra point


def multi_split(s, seps):
    """ Split string by multiple separators.
        >>> multi_split("a,b;c:d", ",;:")
        ['a', 'b', 'c', 'd']
    """
    if not s or not seps:
        return [s]
    sep = seps[0]
    v = ''.join([ch if ch not in seps else sep for ch in s])
    return v.split(sep)


def _random(bytes):
    """ Get random bytes and convert them to integer. """
    import os
    table = ''.join(chr(i) for i in range(256))
    return str2int(os.urandom(bytes), 256, table)


def random_in_range(max_value, min_value=0):
    """ See How to generate a random number from within a range - C
    http://goo.gl/aWiZX
    """
    def numbits(x):
        """ Python before 2.7 does not have Long.bit_length method. """
        try:
            return x.bit_length()
        except AttributeError:
            return len(bin(abs(x))) - 2

    if not max_value:
        max_value = 2L ** 64 - 1
    bit_length = numbits(max_value)
    rand_max = 2L ** bit_length - 1
    import random
    r = random.SystemRandom()
    base_random = r.getrandbits(bit_length)

    # base_random in [0, RAND_MAX]
    if rand_max == base_random:
        return random_in_range(max_value=max_value, min_value=min_value)

    # now guaranteed to be in [0, RAND_MAX)
    value_range = max_value - min_value
    remainder = rand_max % value_range
    bucket = rand_max / value_range

    if base_random < rand_max - remainder:
        return min_value + base_random / bucket
    return random_in_range(max_value=max_value, min_value=min_value)


def get_random_id():
    """ Get random integer suitable for database ID. """
    return _random(RANDOM_ID_SOURCE_BYTES)


def get_random_id_str(alphabet=None):
    """ Get random integer and encode it to URL-safe string. """
    if not alphabet:
        alphabet = BASE62
    n = _random(RANDOM_ID_SOURCE_BYTES)
    return int2str(n, len(alphabet), alphabet)


def get_unique_id(is_unique=None):
    """ Get unique integer value suitable for use as a database key.

        :param is_unique: used to generate a bit shorter IDs than those
            based on UUID.  If this parameter is not specified UUID will be
            used as random data.
    """
    if not callable(is_unique):
        import uuid
        return uuid.uuid4().int
    else:
        id = get_random_id()
        while not is_unique(id):
            id = get_random_id()
        return id


def get_unique_id_str(is_unique=None, alphabet=None):
    """ Get unique string suitable for use as database key.

        :param is_unique: used to generate a bit shorter IDs than those
            based on UUID.  If this parameter is not specified UUID will be
            used as random data.
        :param alphabet: aplphabet used for generated value. Defaults to BASE62
    """
    if not alphabet:
        alphabet = BASE62
    if not callable(is_unique):
        import uuid
        return int2str(uuid.uuid4().int, len(alphabet), alphabet)
    else:
        id = get_random_id_str()
        while not is_unique(id):
            id = get_random_id_str(alphabet)
        return id


#
# cached_property
#

class _Missing(object):
    def __repr__(self):
        return 'no value'

    def __reduce__(self):
        return '_missing'

_missing = _Missing()


class cached_property(object):
    """ A decorator that converts a function into a lazy property.  The
        function wrapped is called the first time to retrieve the result
        and then that calculated result is used the next time you access
        the value.

        Example usage:

        .. code-block:: python

            class Foo(object):
                @cached_property
                def foo(self):
                    # calculate something important here
                    return 42

        The class has to have a `__dict__` in order for this property to
        work.
    """

    # implementation detail: this property is implemented as non-data
    # descriptor.  non-data descriptors are only invoked if there is
    # no entry with the same name in the instance's __dict__.
    # this allows us to completely get rid of the access function call
    # overhead.  If one choses to invoke __get__ by hand the property
    # will still work as expected because the lookup logic is replicated
    # in __get__ for manual invocation.

    def __init__(self, func, name=None, doc=None, writeable=False):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = obj.__dict__.get(self.__name__, _missing)
        if value is _missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def monkeypatch_method(cls):
    """ Add the decorated method to the given class; replace as needed.

        If the named method already exists on the given class, it will
        be replaced, and a reference to the old method appended to a list
        at cls._old_<name>. If the "_old_<name>" attribute already exists
        and is not a list, KeyError is raised.

        Example usage::

            from <somewhere> import <someclass>

            @monkeypatch_method(<someclass>)
            def <newmethod>(self, args):
                return <whatever>

        This adds <newmethod> to <someclass>

        Origin: http://goo.gl/C1v0z
    """

    def decorator(func):
        fname = func.__name__

        old_func = getattr(cls, fname, None)
        if old_func is not None:
            # Add the old func to a list of old funcs.
            old_ref = "_old_%s" % fname
            old_funcs = getattr(cls, old_ref, None)
            if old_funcs is None:
                setattr(cls, old_ref, [])
            elif not isinstance(old_funcs, list):
                raise KeyError("%s.%s already exists." %
                    (cls.__name__, old_ref))
            getattr(cls, old_ref).append(old_func)

        setattr(cls, fname, func)
        return func

    return decorator


if __name__ == "__main__":
    import doctest
    doctest.testmod()
