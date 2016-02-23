from __future__ import unicode_literals
from django.db import models
from django.utils import six
from mcutils.django import model_uid_generator


class UidIntegerField(models.BigIntegerField):
    def __init__(self, model_class, **kwargs):
        self.model_class = model_class
        self.min_value = kwargs.pop('min_value')
        self.max_value = kwargs.pop('max_value', self.MAX_BIGINT)
        self.field_name = kwargs.pop('field_name', 'pk')
        kwargs.setdefault('unique', True)
        kwargs.setdefault('editable', False)
        kwargs.setdefault('default', model_uid_generator(
            self.model_class, max_value=self.max_value,
            min_value=self.min_value, field_name=self.field_name))
        super(UidIntegerField, self).__init__(**kwargs)

    def value_to_string(self, obj):
        return six.text_type(self._get_val_from_obj(obj)).zfill(
            len(six.text_type(self.max_value)))

    def deconstruct(self):
        name, path, args, kwargs = super(UidIntegerField, self).deconstruct()
        model_class = self.model_class
        if isinstance(model_class, models.base.ModelBase):
            model_class = '.'.join([
                model_class._meta.app_label, model_class.__class__.__name__])
        args = [six.text_type(model_class)]
        kwargs['min_value'] = self.min_value
        if self.max_value != self.MAX_BIGINT:
            kwargs['max_value'] = self.max_value
        if self.field_name != 'pk':
            kwargs['field_name'] = six.text_type(self.field_name)
        default = kwargs.get('default')
        if callable(default):
            kwargs['default'] = default()
        return name, path, args, kwargs

try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([
        ([UidIntegerField], [], {
            'model_class': ['model_class', {}],
            'field_name': ['field_name', {'default': 'pk'}],
            'min_value': ['min_value', {'default': 0}],
        })
    ], ['^mcutils\.django\.fields\.UidIntegerField'])
except ImportError:
    add_introspection_rules = lambda x: None
