from django.apps import AppConfig
from django.conf import settings

import logging


class AccountsConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "accounts"

    def ready(self):
        backend = settings.MAILERS["default"]["BACKEND"]
        options = settings.MAILERS["default"].get("OPTIONS", {})
        logging.getLogger("accounts.mailer").info(
            "email_backend_active backend=%s host=%s port=%s use_tls=%s use_ssl=%s",
            backend,
            options.get("host", ""),
            options.get("port", ""),
            options.get("use_tls", False),
            options.get("use_ssl", False),
        )
