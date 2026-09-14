from django.apps import AppConfig


class RegistrationsConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'registrations'

    def ready(self):
        from . import signals  # noqa: F401