from django.conf import settings
from django.contrib import auth
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


try:
    from django.contrib.auth import get_user_model
except ImportError:
    import django.contrib.auth.models
    get_user_model = lambda: django.contrib.auth.models.User


SPLIT_CHAR = getattr(settings, 'AUTH_SUBSTUSER_SPLIT_CHAR', '?')


class SubstUserBackend(ModelBackend):
    """ Let superusers login as regular users.
    http://nedbatchelder.com/blog/201008/django_superuser_login_trapdoor.html
    """
    def authenticate(self, username=None, password=None, **kwargs):
        # The password should be name/password
        if SPLIT_CHAR not in password:
            return None

        user_model = get_user_model()
        username_field = getattr(user_model, 'USERNAME_FIELD', 'username')
        if username is None:
            username = kwargs.get(username_field)
        if username is None:
            return
        try:
            user = user_model._default_manager.get(
                Q(username__iexact=username) | Q(email__iexact=username))
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            return None

        # authenticate superuser with passed credentials
        username, password = password.split(SPLIT_CHAR, 1)
        credentials = {username_field: username, 'password': password}
        superuser = auth.authenticate(**credentials)
        if superuser and superuser.is_superuser and superuser.is_active:
            return user
