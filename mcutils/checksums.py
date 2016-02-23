__all__ = ['crc16', 'get_hexdigest', 'luhn']


def crc16(buff, crc=0, poly=0xa001):
    l = len(buff)
    i = 0
    while i < l:
        ch = ord(buff[i])
        uc = 0
        while uc < 8:
            if (crc & 1) ^ (ch & 1):
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
            ch >>= 1
            uc += 1
        i += 1
    return crc


def get_hexdigest(algorithm, salt, s):
    """ Returns a string of the hexdigest of the given string and salt
    using the given algorithm ('md5', 'sha1' or 'crypt').
    """
    import sys
    if sys.version_info >= (2, 5):
        import hashlib
        md5_constructor = hashlib.md5
        md5_hmac = md5_constructor
        sha_constructor = hashlib.sha1
        sha_hmac = sha_constructor
    else:
        import md5
        md5_constructor = md5.new
        md5_hmac = md5
        import sha
        sha_constructor = sha.new
        sha_hmac = sha

    if algorithm == 'crypt':
        try:
            import crypt
        except ImportError:
            raise ValueError('"crypt" algorithm not supported in this '
                'environment')
        return crypt.crypt(s, salt)

    if algorithm == 'md5':
        return md5_constructor(salt + s).hexdigest()
    elif algorithm == 'sha1':
        return sha_constructor(salt + s).hexdigest()
    raise ValueError("Got unknown algorithm type.")


LUHN_ODD_LOOKUP = (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)  # sum_of_digits(index * 2)


def luhn(candidate):
    """ Checks a candidate number for validity according to the Luhn
    algorithm (used in validation of, for example, credit cards).
    Both numeric and string candidates are accepted.
    """
    if not isinstance(candidate, basestring):
        candidate = str(candidate)
    try:
        evens = sum([int(c) for c in candidate[-1::-2]])
        odds = sum([LUHN_ODD_LOOKUP[int(c)] for c in candidate[-2::-2]])
        return ((evens + odds) % 10 == 0)
    except ValueError:  # Raised if an int conversion fails
        return False
