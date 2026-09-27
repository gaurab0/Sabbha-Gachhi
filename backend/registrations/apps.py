from django.apps import AppConfig


class RegistrationsConfig(AppConfig):
    default_auto_field = 'django_mongodb_backend.fields.ObjectIdAutoField'
    name = 'registrations'

    def ready(self):
        from . import signals  # noqa: F401
        from . import tasks  # noqa: F401 — ensure Celery tasks are registered
