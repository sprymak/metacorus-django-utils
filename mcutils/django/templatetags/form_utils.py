import copy

from django.template import Library
from django.utils import six
from django.utils.datastructures import SortedDict


register = Library()


@register.assignment_tag
def fieldset(form, field_names):
    fields = list(filter(lambda s: bool(s.strip()), field_names.split(',')))
    new_form = copy.copy(form)
    new_form.fields = SortedDict(
        [(k, v) for k, v in six.iteritems(form.fields) if k in fields])
    return new_form


@register.inclusion_tag('include/form.html')
def render_form(form, formsets=None):
    return {
        'form': form,
    }
