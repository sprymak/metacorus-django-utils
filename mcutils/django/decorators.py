from functools import wraps

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.utils import simplejson

__all__ = (
    'ajax_only', 'ajax_login_required', 'ajax_template', 'auth_user_only',
    'debug_only', 'render_to_json_response', 'super_user_only',
)


_JSON_MIME_TYPE = 'application/json'


def ajax_login_required(view_func):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            json = simplejson.dumps({'login_required': True})
            return HttpResponseForbidden(json, mimetype=_JSON_MIME_TYPE)
    return wrap


def ajax_only(view_func):
    """ Ensure that all requests made to a view are made as AJAX requests.
        Non-AJAX requests will recieve a 400 (Bad Request) response.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.is_ajax():
            from django.http import HttpResponseBadResponse
            return HttpResponseBadResponse()
        return view_func(request, *args, **kwargs)
    return wrapper


def ajax_template(template_name):
    def internal(view_func):
        def wrap(request, *args, **kwargs):
            if request.is_ajax() and template_name:
                kwargs.update({'template_name': template_name})
            return view_func(request, *args, **kwargs)
        return wrap
    return internal


def auth_user_only(view_func):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            raise Http404
    return wrap


def debug_only(handler):
    def wrap(request, *args, **kw):
        if not (settings.DEBUG or getattr(request.user, 'is_superuser', None)):
            raise Http404
        return handler(request, *args, **kw)
    wrap.__name__ = handler.__name__
    return wrap


def message_if(test_func, message):
    """ Drop a message before view_func run if test_func returns True. """
    def internal(view_func):
        def wrap(request, *args, **kwargs):
            if test_func(request):
                from django.contrib import messages
                if callable(message):
                    text = message(request)
                else:
                    text = message
                if text:
                    messages.warning(request, text)
            return view_func(request, *args, **kwargs)
        return wrap
    return internal


def render_to_json_response(*fn, **jsonargs):
    """ Render response as JSON.

        :param encoder: custom `JSONEncoder` subclass to serialize additional
            types. This argument is an alias to `cls` argument for `json.dump`.
        :param jsonargs: arguments suitable to pass to `json.dump` function.
        :returns: `HttpResponse` object with JSON mime type.

        Usage::

            @render_to_json_response
            def json_view(request):
                return { 'foo': 'bar' }

            @render_to_json_response(indent=4)
            def json_view(request):
                return { 'foo': 'bar' }
    """
    def internal(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs) or {}
            status_code = kwargs.pop('status', None)
            if isinstance(response, HttpResponse):
                response.mimetype = _JSON_MIME_TYPE
                if status_code:
                    response.status_code = status_code
                return response

            ret = HttpResponse(mimetype=_JSON_MIME_TYPE)
            if status_code:
                ret.status_code = status_code
            encoder = jsonargs.pop('encoder', None)
            ret.write(simplejson.dumps(response, cls=encoder, **jsonargs))
            return ret
        return wrapper
    if len(fn) > 0 and callable(fn[0]):
        return internal(fn[0])
    return internal


def super_user_only(view_func):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated() and request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        else:
            raise Http404
    return wrap
