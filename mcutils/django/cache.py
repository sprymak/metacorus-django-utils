CACHE_KEY = getattr('settings', 'CACHE_MIDDLEWARE_KEY_PREFIX', '')
CACHE_GENERATION_KEY = CACHE_KEY + '/cache_gen'


def make_cache_key(key, user=None):
    from hashlib import md5
    gen = memcache.get(CACHE_GENERATION_KEY)
    if not gen:
        gen = 1
        memcache.set(CACHE_GENERATION_KEY, gen)
    from logging import info
    info("generation in model cache: %s", memcache.get(CACHE_GENERATION_KEY))
    return md5('%s/%d/%s' % (CACHE_KEY, gen, str(key))).hexdigest()


def invalidate_cache():
    gen = memcache.get(CACHE_GENERATION_KEY)
    if not gen:
        gen = 1
        memcache.set(CACHE_GENERATION_KEY, gen)
    else:
        memcache.incr(CACHE_GENERATION_KEY)
    from logging import info
    info("generation in model cache: %s", memcache.get(CACHE_GENERATION_KEY))


def invalidate_user_cache(user):
    pass
