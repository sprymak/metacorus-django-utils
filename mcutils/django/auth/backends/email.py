from django.contrib.auth.backends import ModelBackend
try:
    from django.contrib.auth import get_user_model
except ImportError:
    import django.contrib.auth.models
    get_user_model = lambda: django.contrib.auth.models.User


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None, **kwargs):
        user_model = get_user_model()
        username_field = getattr(user_model, 'USERNAME_FIELD', 'username')
        if username is None:
            username = kwargs.get(username_field)
        if username is None:
            return
        try:
            user = user_model._default_manager.get(email__iexact=username)
            if user.check_password(password):
                return user
        except (user_model.DoesNotExist, user_model.MultipleObjectsReturned):
            return
