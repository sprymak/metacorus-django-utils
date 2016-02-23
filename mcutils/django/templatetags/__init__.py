# -*- coding: utf-8 -*-
import django
import django.template
import django.utils.safestring
from django.conf import settings
from django.utils import six
from .collections_utils import in_list
from .form_utils import fieldset
from .http_utils import url_name


def assignment_tag(self, func=None, takes_context=None):
    from inspect import getargspec
    from django.template import TemplateSyntaxError

    def dec(func):
        params, xx, xxx, defaults = getargspec(func)
        if takes_context:
            if params[0] == 'context':
                params = params[1:]
            else:
                raise TemplateSyntaxError("Any tag function decorated with "
                    "takes_context=True must have a first argument "
                    "of 'context'")

        class AssignmentNode(django.template.Node):
            def __init__(self, params_vars, target_var):
                self.params_vars = map(django.template.Variable, params_vars)
                self.target_var = target_var

            def render(self, context):
                resolved_vars = [var.resolve(context) for var in
                    self.params_vars]
                if takes_context:
                    func_args = [context] + resolved_vars
                else:
                    func_args = resolved_vars
                context[self.target_var] = func(*func_args)
                return ''

        def compile_func(parser, token):
            bits = token.split_contents()
            tag_name = bits[0]
            bits = bits[1:]
            params_max = len(params)
            defaults_length = defaults and len(defaults) or 0
            params_min = params_max - defaults_length
            if (len(bits) < 2 or bits[-2] != 'as'):
                raise TemplateSyntaxError(
                    "'%s' tag takes at least 2 arguments and the "
                    "second last argument must be 'as'" % tag_name)
            params_vars = bits[:-2]
            target_var = bits[-1]
            if (len(params_vars) < params_min or
                    len(params_vars) > params_max):
                if params_min == params_max:
                    raise TemplateSyntaxError(
                        "%s takes %s arguments" % (tag_name, params_min))
                else:
                    raise TemplateSyntaxError(
                        "%s takes between %s and %s arguments"
                        % (tag_name, params_min, params_max))
            return AssignmentNode(params_vars, target_var)

        compile_func.__doc__ = func.__doc__
        self.tag(getattr(func, "_decorated_function", func).__name__,
            compile_func)
        return func

    if func is None:
        # @register.assignment_tag(...)
        return dec
    elif callable(func):
        # @register.assignment_tag
        return dec(func)
    else:
        raise TemplateSyntaxError("Invalid arguments provided to "
            "assignment_tag")


if django.VERSION < (1, 4, None):
    import utils
    utils.monkeypatch_method(django.template.Library)(assignment_tag)

register = django.template.Library()


class VerbatimNode(django.template.Node):
    def __init__(self, text):
        self.text = text

    def render(self, context):
        return self.text


def do_verbatim(parser, token):
    text = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endverbatim':
            break
        if token.token_type == django.template.TOKEN_VAR:
            text.append('{{')
        elif token.token_type == django.template.TOKEN_BLOCK:
            text.append('{%')
        text.append(token.contents)
        if token.token_type == django.template.TOKEN_VAR:
            text.append('}}')
        elif token.token_type == django.template.TOKEN_BLOCK:
            text.append('%}')
    return VerbatimNode(''.join(text))


if django.VERSION < (1, 5, None):
    register.tag("verbatim")(do_verbatim)


@register.filter
def add_url_parameters(value, arg):
    """ Add GET parameters to URL string.
        Usage:
            {{ request.get_full_path|add_url_parameters:"mode=list&limit=9" }}
    """
    if not isinstance(arg, basestring):
        arg = unicode(arg)
    from django.http import QueryDict, parse_qsl
    parts = value.split('?')
    path = parts[0]
    q = '&'.join(parts[1:])
    args = QueryDict(q).copy()
    new_args = parse_qsl(arg or '')
    for (k, v) in new_args:
        args.update({k: v})
    s = lambda x, y: "%s=%s" % (x, y) if y else "%s" % x
    q = '&'.join([s(k, v) for (k, v) in args.items()])
    return '?'.join([path, q])


register.filter('in_list', in_list)


@register.filter
def escapejson(value, arg=None):
    import simplejson
    base = simplejson.dumps(value)
    return base.replace('/', r'\/')


register.assignment_tag(fieldset)


DEFAULT_WINDOW = getattr(settings, 'PAGINATION_DEFAULT_WINDOW', 4)


@register.inclusion_tag("paginator.html", takes_context=True)
def paginator(context, window=DEFAULT_WINDOW):
    """ Renders the ``pagination/pagination.html`` template, resulting in a
    Digg-like display of the available pages, given the current page.  If there
    are too many pages to be displayed before and after the current page, then
    elipses will be used to indicate the undisplayed gap between page numbers.

    Requires one argument, ``context``, which should be a dictionary-like data
    structure and must contain the following keys:

    ``paginator``
        A ``Paginator`` or ``QuerySetPaginator`` object.

    ``page_obj``
        This should be the result of calling the page method on the
        aforementioned ``Paginator`` or ``QuerySetPaginator`` object, given
        the current page.

    This same ``context`` dictionary-like data structure may also include:

    ``getvars``
        A dictionary of all of the **GET** parameters in the current request.
        This is useful to maintain certain types of state, even when requesting
        a different page.
        """
    try:
        paginator = context['paginator']
        page_obj = context['page_obj']
        page_range = paginator.page_range
        # First and last are simply the first *n* pages and the last *n* pages,
        # where *n* is the current window size.
        first = set(page_range[:window])
        last = set(page_range[-window:])
        # Now we look around our current page, making sure that we don't wrap
        # around.
        current_start = page_obj.number - 1 - window
        if current_start < 0:
            current_start = 0
        current_end = page_obj.number - 1 + window
        if current_end < 0:
            current_end = 0
        current = set(page_range[current_start:current_end])
        pages = []
        # If there's no overlap between the first set of pages and the current
        # set of pages, then there's a possible need for elusion.
        if len(first.intersection(current)) == 0:
            first_list = list(first)
            first_list.sort()
            second_list = list(current)
            second_list.sort()
            pages.extend(first_list)
            diff = second_list[0] - first_list[-1]
            # If there is a gap of two, between the last page of the first
            # set and the first page of the current set, then we're missing a
            # page.
            if diff == 2:
                pages.append(second_list[0] - 1)
            # If the difference is just one, then there's nothing to be done,
            # as the pages need no elusion and are correct.
            elif diff == 1:
                pass
            # Otherwise, there's a bigger gap which needs to be signaled for
            # elusion, by pushing a None value to the page list.
            else:
                pages.append(None)
            pages.extend(second_list)
        else:
            unioned = list(first.union(current))
            unioned.sort()
            pages.extend(unioned)
        # If there's no overlap between the current set of pages and the last
        # set of pages, then there's a possible need for elusion.
        if len(current.intersection(last)) == 0:
            second_list = list(last)
            second_list.sort()
            diff = second_list[0] - pages[-1]
            # If there is a gap of two, between the last page of the current
            # set and the first page of the last set, then we're missing a
            # page.
            if diff == 2:
                pages.append(second_list[0] - 1)
            # If the difference is just one, then there's nothing to be done,
            # as the pages need no elusion and are correct.
            elif diff == 1:
                pass
            # Otherwise, there's a bigger gap which needs to be signaled for
            # elusion, by pushing a None value to the page list.
            else:
                pages.append(None)
            pages.extend(second_list)
        else:
            differenced = list(last.difference(current))
            differenced.sort()
            pages.extend(differenced)
        to_return = {
            'pages': pages,
            'page_obj': page_obj,
            'paginator': paginator,
            'is_paginated': paginator.count > paginator.per_page,
        }
        if 'request' in context:
            getvars = context['request'].GET.copy()
            if 'page' in getvars:
                del getvars['page']
            if len(getvars.keys()) > 0:
                to_return['getvars'] = "&%s" % getvars.urlencode()
            else:
                to_return['getvars'] = ''
        return to_return
    except KeyError, AttributeError:
        return {}


class SiteNameNode(django.template.Node):

    def __init__(self, site=None, var_name=None):
        from django.contrib.sites.models import Site
        if isinstance(site, Site):
            self.site = site
        else:
            self.site = django.template.Variable(site)
        self.var_name = var_name

    def render(self, context):
        from django.contrib.sites.models import Site
        try:
            if isinstance(self.site, Site):
                site = self.site
            else:
                site = self.site.resolve(context)
            site_name = site.name or ''
            if self.var_name:
                context[self.var_name] = site_name
                return ''
            else:
                return site_name
        except django.template.VariableDoesNotExist:
            return ''


@register.tag()
def site_name(parser, token):
    """ site title.
        {% site_name %}
        {% site_name as title %}
        {% site_name request.site %}
        {% site_name request.site as title %}
    """
    from django.contrib.sites.models import Site
    current_site = Site.objects.get_current()
    try:
        args = token.split_contents()
        var_name = None
        if len(args) == 1:
            # {% site_name %} case
            arg = current_site
        elif len(args) == 2:
            # {% site_name site %} case
            tag_name, arg = args
        elif len(args) == 3:
            # {% site_name as var %} case
            arg = current_site
            tag_name, _as, var_name = args
        elif len(args) == 4:
            # {% site_name site as var %} case
            tag_name, arg, _as, var_name = args
    except ValueError:
        raise django.template.TemplateSyntaxError, \
            "%r tag requeres arguments" % token.contents.split()[0]
    return SiteNameNode(arg, var_name)


@register.assignment_tag(name='type_label')
def type_label_tag(val):
    return type(val).__name__.lower()


@register.filter(name='type_label')
def type_label_filter(val):
    return type(val).__name__.lower()


register.assignment_tag(url_name, takes_context=True)
