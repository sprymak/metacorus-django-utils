import datetime

import django
from django import db
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import _get_queryset
from django.utils import six
from django.utils.text import slugify
try:
    from django.utils import timezone
except ImportError:
    timezone = None
from unidecode import unidecode

from .. import random_in_range


__all__ = [
    'create_slug',
    'get_object_or_none',
    'get_object_dto',
    'make_model_dto',
    'model_uid_generator',
    'reverse_lazy',
    'timestamp_with_timezone',
    'update_object_from_dto',
]


def create_slug(value, model_class=None, field_name=None, queryset=None,
        separator='-', max_length=None, exclude=None):
    """
    This function is mostly based on django snippet #690 (http://goo.gl/RYV5x3)
    """
    if isinstance(model_class, six.string_types):
        def __dummy():
            pass

        if "." in model_class:
            app_label, model_name = model_class.split(".")
        else:
            app_label = __dummy.__module__.split('.')[0]
            model_name = model_class
        from django.db import models
        model_class = models.get_model(app_label, model_name)

    slug = slugify(six.text_type(unidecode(value)))

    # calculate max length
    from django.db.models.base import ModelBase
    if max_length is None and isinstance(model_class, ModelBase):
        if field_name is None:
            field_name = "slug"
        slug_field = model_class._meta.get_field(field_name)
        max_length = slug_field.max_length

    if max_length:
        slug = slug[:max_length]
        slug = slug.strip(separator)

    # make unique slug
    if queryset is None and isinstance(model_class, ModelBase):
        queryset = model_class._default_manager.all()
        if isinstance(exclude, dict):
            queryset = queryset.exclude(**exclude)

    # Find a unique slug. If one matches, add '-2' to the end and try again
    # (then '-3', etc).
    # TODO(sprymak): pass index generator function as an argument.
    # create_slug(name, index_generator = lambda x: x + random.randint(1, 9))
    # index = index_generator(index)
    if queryset is not None:
        index = 2
        original_slug = slug
        while not slug or queryset.filter(**{field_name: slug}):
            slug = original_slug
            end = '%s%s' % (separator, index)
            if max_length and len(slug) + len(end) > max_length:
                slug = slug[:max_length - len(end)]
                slug = slug.strip(separator)
            slug = '%s%s' % (slug, end)
            index += 1

    return slug


def get_max_uid_value(model_class, field_name):
    max_value = None
    max_config_values = getattr(settings, 'MAX_UID_VALUE', {})
    if isinstance(max_config_values, six.integer_types):
        return max_config_values

    default_value = max_config_values.get('*')
    model_name = model_class
    if isinstance(model_name, db.models.base.ModelBase):
        model_name = '.'.join([
            model_name._meta.app_label,
            model_name._meta.object_name])
    if isinstance(field_name, six.string_types):
        max_value = max_config_values.get(
            '.'.join([model_name, field_name]), default_value)
    return max_value


class model_uid_generator(object):
    """
        Usage::

        class Entry(models.Model):
          uid = models.BigIntegerField(unique=True, editable=False,
              default=utils.model_uid_generator("blog.Entry", field_name="uid",
                  max_value=MAX_UID_VALUE))
    """
    def __init__(self, model_class, max_value=None, min_value=None, field_name="pk"):
        self.model_class = model_class
        self.min_value = min_value
        self.max_value = max_value
        self.field_name = field_name
        if self.min_value is None:
            self.min_value = 0
        if self.max_value is None:
            self.max_value = get_max_uid_value(self.model_class, self.field_name)
            if self.max_value is None:
                raise ImproperlyConfigured()

    def get_random_id(self):
        """ Get random integer. """
        return random_in_range(
            min_value=self.min_value, max_value=self.max_value)

    def is_unique(self, value):
        # Assume generated value is unique if it is not a Django model
        # or ID field name is empty.
        if not (self.field_name and self.model_class
                and issubclass(self.model_class, db.models.Model)):
            return True
        try:
            queryset = _get_queryset(self.model_class)
            queryset.get(**{self.field_name: value})
        except self.model_class.DoesNotExist:
            return True
        except db.DatabaseError:
            # catch "no such table" errors while south schema inspecting
            pass
        return False

    def __call__(self):
        if self.model_class is not None and not isinstance(
                self.model_class, (six.string_types, db.models.base.ModelBase)):
            raise TypeError("model_class must be either a string or "
                            "subclass of Model; received %r" % self.model_class)

        if isinstance(self.model_class, six.string_types):
            if "." in self.model_class:
                app_label, model_name = self.model_class.split(".")
            else:
                app_label = model_uid_generator.__module__.split('.')[0]
                model_name = self.model_class
            self.model_class = db.models.get_model(app_label, model_name)
            if self.model_class is None:
                raise ValueError("model_class refers to model '%r' "
                                 "that has not been installed" % self.model_class)

        if not isinstance(self.field_name, six.string_types):
            raise TypeError("field_name must be a string; "
                            "received %r" % self.field_name)

        # calculate max length
        if self.max_value is None and isinstance(self.model_class,
                db.models.base.ModelBase):
            field = self.model_class._meta.get_field(self.field_name)
            max_length = field.max_length
            # TODO: guess maximum allowed value based on field type

        val = self.get_random_id()
        while not self.is_unique(val):
            val = self.get_random_id()
        return val


def get_object_or_none(model_class, *args, **kwargs):
    """Utility function just list django.shortcuts.get_object_or_404

    Instead of raising a 404 error this function returns None.

    See: django.shortcuts.get_object_or_404
    """
    queryset = _get_queryset(model_class)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None


def make_model_dto(model, **data):
    """ Makes a data transfer object for Django ``db.Model`` class.

        dto = make_model_dto(models.Post, title="Lorem Ipsum")
        print dto.title
        dto.more = 11
        print dto.more
    """

    class final(type):
        """ Metaclass to prevent a class from being inherited """

        def __init__(cls, name, bases, namespace):
            super(final, cls).__init__(name, bases, namespace)
            for klass in bases:
                if isinstance(klass, final):
                    raise TypeError(str(klass.__name__) + " is final")

    class DataTransferObject(object):
        __metaclass__ = final

        def __init__(self, **kwargs):
            self.__dict__ = kwargs

        def __iter__(self):
            return self.__dict__

        def as_dict(self):
            return self.__dict__

    fields = {}
    for field in model._meta.get_all_field_names():
        fields[field] = data.get(field)

    return DataTransferObject(**fields)


def get_object_dto(instance):
    """ Constructs the composite transfer object from Django ``Model`` object.
        :param instance: source model object
    """
    data = {}
    if isinstance(instance, django.db.models.Model):
        from django.core import serializers
        serializer = serializers.get_serializer("python")()
        serializer.use_natural_keys = False

        serializer.start_serialization()
        serializer.start_object(instance)
        for field in instance._meta.local_fields:
            if field.serialize:
                if field.rel is None:
                    serializer.handle_field(instance, field)
                else:
                    try:
                        serializer.handle_fk_field(instance, field)
                    except field.rel.to.DoesNotExist:
                        # skip not found relatives
                        pass
        for field in instance._meta.many_to_many:
            if field.serialize:
                serializer.handle_m2m_field(instance, field)
        serializer.end_object(instance)
        serializer.end_serialization()
        value = serializer.getvalue()
        if value:
            data = value[0].get('fields', {})
    return make_model_dto(instance.__class__, **data)


def update_object_from_dto(instance, data, partial=False):
    model = instance.__class__
    for field in model._meta.get_all_field_names():
        value = getattr(data, field)
        if value or not partial:
            setattr(instance, field, value)


def render_to_json_response(data, **kwargs):
    """ Render data as JSON.

        :param encoder: custom `JSONEncoder` subclass to serialize additional
            types. This argument is an alias to `cls` argument for `json.dump`.
        :param kwargs: arguments suitable to pass to `json.dump` function.
        :returns: `HttpResponse` object with JSON mime type.

        Usage::

            render_to_json_response({'foo':'bar'})
            render_to_json_response({'foo':'bar'}, indent=4)
    """
    from django.http import HttpResponse
    from django.utils import simplejson
    from .decorators import _JSON_MIME_TYPE
    status_code = kwargs.pop('status', None)
    content_type = kwargs.pop('content_type', None)

    if isinstance(data, HttpResponse):
        data.mimetype = _JSON_MIME_TYPE
        if status_code:
            data.status_code = status_code
        if content_type:
            data['Content-Type'] = content_type
        return data

    retval = HttpResponse(mimetype=_JSON_MIME_TYPE, content_type=content_type)
    if status_code:
        retval.status_code = status_code
    encoder = kwargs.pop('encoder', None)
    retval.write(simplejson.dumps(data, cls=encoder, **kwargs))
    return retval


def timestamp_with_timezone(dt=None):
    """ Return a timestamp with a timezone for the configured locale.
    If all else fails, consider localtime to be UTC.
    """
    dt = dt or datetime.datetime.now()
    if timezone is None:
        return dt.strftime('%Y-%m-%d %H:%M%z')
    if not dt.tzinfo:
        tz = timezone.get_current_timezone()
        if not tz:
            tz = timezone.utc
        dt = dt.replace(tzinfo=timezone.get_current_timezone())
    return dt.strftime("%Y-%m-%d %H:%M%z")


# A lazily evaluated version of reverse().
# It is useful for when you need to use a URL reversal before your
# project's URLConf is loaded.
if django.VERSION < (1, 4, None):
    from django.core.urlresolvers import reverse
    from django.utils.functional import lazy
    reverse_lazy = lazy(reverse, str)
else:
    from django.core.urlresolvers import reverse_lazy


def url_name(request):
    """ Returns URL name for current request.
    Origin: https://code.djangoproject.com/ticket/18584

        Usage::

            if url_name(request) != 'auth_login':
                ...
    """
    from django.core.urlresolvers import resolve
    try:
        res = resolve(request.path)
        if res:
            return res.url_name
    except:
        return
