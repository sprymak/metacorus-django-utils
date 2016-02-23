import re
import collections

from django.http import QueryDict
from django.template import Library, Node, TemplateSyntaxError
from django.utils import six
from django.utils.datastructures import MultiValueDict
import django.utils.http

register = Library()


class UrlParamsNode(Node):
    def __init__(self, url, args, kwargs, asvar):
        self.url = url
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        url = self.url.resolve(context)
        parts = url.split('?')
        url = parts[0]
        original_query = QueryDict('&'.join(parts[1:])).copy()
        query = MultiValueDict(dict(
            (k, v.resolve(context)) for k, v in six.iteritems(self.kwargs)))

        args_to_set = []
        args_to_remove = []
        for arg in self.args:
            k = arg.resolve(context)
            if k.startswith('-'):
                args_to_remove.append(k[1:])
            else:
                args_to_set.append(k)

        kwargs_to_set = MultiValueDict()
        kwargs_to_add = MultiValueDict()
        kwargs_to_remove = MultiValueDict()
        for (k, v) in query.lists():
            # make sure val is a list of strings
            val = map(str, v if isinstance(v, list) else [v])
            if k.startswith('+'):
                kwargs_to_add.setlistdefault(k[1:]).extend(val)
            elif k.startswith('-'):
                kwargs_to_remove.setlistdefault(k[1:]).extend(val)
            else:
                kwargs_to_set.setlist(k, val)

        filter_excluded_kwargs = lambda values: [
            (k, list(set(v) - set(kwargs_to_remove.getlist(k))))
            for k, v in values.iterlists() if k not in args_to_remove]

        args = [arg for arg in args_to_set if arg not in args_to_remove]
        kwargs = MultiValueDict()
        for k, v in filter_excluded_kwargs(original_query):
            kwargs.setlistdefault(k).extend(v if isinstance(v, list) else [v])
        for k, v in filter_excluded_kwargs(kwargs_to_set):
            kwargs.setlist(k, v)
        for k, v in filter_excluded_kwargs(kwargs_to_add):
            kwargs.setlistdefault(k).extend(v)

        output = list(set(args))
        for k, l in kwargs.lists():
            output.extend(
                ['%s=%s' % (k, v) if v else six.text_type(k) for v in l])

        if output:
            url = '?'.join([url, '&'.join(set(output))])

        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url


kwarg_re = re.compile(r"(?:(^[+-]?\w+)=)?(.+)")


@register.filter('base36_to_int')
def do_base36_to_int(value):
    return django.utils.http.base36_to_int(value)


@register.filter('int_to_base36')
def do_int_to_base36(value):
    return django.utils.http.int_to_base36(int(value))


@register.assignment_tag(takes_context=True)
def url_name(context):
    """ Returns URL name of the current request.

    Example::

        {% url_name as current_url_name %}
        {% if current_url_name != 'auth_login' %}
        <li>
        <a href="{% url 'auth_login_next' request.get_full_path|urlencode %}">
            {% trans 'Signin' %}</a>
        </li>
        {% endif %}
    """
    request = context.get("request")
    if not request:
        return ""
    from .. import url_name as _url_name
    return _url_name(request)


@register.tag
def url_params(parser, token):
    """ Changes GET parameters of the URL.

        Set 'mode' parameter to 'list', remove value 9 of 'limit' parameter of
        the current URL::

            {% url_params request.get_full_path mode='list' -limit=9 as url %}

        Add 'list' value to 'mode' parameter, remove all 'limit' values of
        the current URL::

            {% url_params request.get_full_path +mode='list' '-limit' %}
    """
    bits = token.split_contents()
    url = parser.compile_filter(bits[1])
    args = []
    kwargs = {}
    asvar = None
    bits = bits[2:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]
    for bit in bits:
        match = kwarg_re.match(bit)
        if not match:
            raise TemplateSyntaxError("Malformed arguments to url_params tag")
        name, value = match.groups()
        if name:
            kwargs[name] = parser.compile_filter(value)
        else:
            args.append(parser.compile_filter(value))

    return UrlParamsNode(url, args, kwargs, asvar)
