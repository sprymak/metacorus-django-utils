import collections
from django import template
from django.utils import six


register = template.Library()


def _get_item(value, key):
    """ Returns specified item of the collection by key or index.
    Example::

        {{ unread_messages|get_item:obj.pk|default_if_none:0 }}

        {% get_item field|get_item:'__class__' '__name__' as field_type %}
    """
    if isinstance(value, collections.Mapping):
        return value.get(key)
    if isinstance(value, collections.Sequence):
        try:
            return value[key]
        except IndexError:
            return None
    return getattr(value, key, None)

register.filter('get_item', _get_item)
register.assignment_tag(_get_item, name='get_item')


@register.filter
def in_list(value, container):
    """ Returns True if `value` is in the `arg` container or comma separated
    values list.
        Example::

            {% if value|in_list:"a,b,c,d" %}...{% endif %}
            {% if value|in_list:selection %}...{% endif %}
    """
    if container is None:
        return False
    if isinstance(container, six.text_type):
        container = container.split(',')
    if not isinstance(container, collections.Container):
        container = list(container)
    return value in container or six.text_type(value) in container


@register.filter
def split(value, size):
    size = int(size)
    length = len(value)
    for i in xrange(0, length, size):
        yield value[i:i + size]


@register.filter
def partition(value, n):
    """
    Break a list into ``n`` pieces. The last list may be larger than the rest if
    the list doesn't break cleanly. That is::

        >>> l = range(10)

        >>> partition(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> partition(l, 3)
        [[0, 1, 2], [3, 4, 5], [6, 7, 8, 9]]

        >>> partition(l, 4)
        [[0, 1], [2, 3], [4, 5], [6, 7, 8, 9]]

        >>> partition(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

    """
    try:
        n = int(n)
        value = list(value)
    except (ValueError, TypeError):
        return [value]
    p = len(value) / n
    return [value[p * i:p * (i + 1)] for i in range(n - 1)] + [value[p * (i + 1):]]


@register.filter
def partition_horizontal(value, n):
    """
    Break a list into ``n`` peices, but "horizontally." That is,
    ``partition_horizontal(range(10), 3)`` gives::

        [[1, 2, 3],
         [4, 5, 6],
         [7, 8, 9],
         [10]]

    Clear as mud?
    """
    try:
        n = int(n)
        value = list(value)
    except (ValueError, TypeError):
        return [value]
    newlists = [list() for i in range(n)]
    for i, val in enumerate(value):
        newlists[i % n].append(val)
    return newlists
