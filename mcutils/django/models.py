from django.db import models
from django.core.management import call_command


def load_fixture(file_name, orm):
    """ Proper fixtures loading in south data migrations (to be ensured that
    migration will use appropriate version of the models for fixture loading

    https://djangosnippets.org/snippets/2897/

    Usage::

        def forwards(self, orm):
             load_fixture('my_fixture.json', orm)
    """
    original_get_model = models.get_model

    def get_model_southern_style(*args):
        try:
            return orm['.'.join(args)]
        except IndexError:
            return original_get_model(*args)

    models.get_model = get_model_southern_style
    call_command('loaddata', file_name)
    models.get_model = original_get_model
