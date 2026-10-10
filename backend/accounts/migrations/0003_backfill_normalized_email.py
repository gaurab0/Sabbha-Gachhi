"""Backfill for email verification (non-breaking).

- Fills `normalized_email` for every existing user (lowercase/trim + Gmail
  dot/plus folding, mirroring accounts.email_normalize.normalize_email so
  the migration never depends on app code).
- Leaves `email_verified=False` (existing users must verify and will be
  prompted). To grandfather existing users instead, run after migrate:
      python manage.py shell -c "
      from django.utils import timezone
      from accounts.models import User
      User.objects.filter(email_verified=False).update(
          email_verified=True, email_verified_at=timezone.now())"
"""

from django.db import migrations


def _normalize(email):
    email = (email or "").strip().lower()
    if "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local = local.split("+", 1)[0].replace(".", "")
    return f"{local}@{domain}"


def backfill_normalized_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    updated = 0
    for user in User.objects.all().only("id", "email", "normalized_email").iterator():
        normalized = _normalize(user.email)
        # First-write-wins on collision (e.g. pre-existing Gmail aliases):
        # the duplicate keeps NULL and must resolve via support/re-register.
        if User.objects.filter(normalized_email=normalized).exclude(pk=user.pk).exists():
            continue
        user.normalized_email = normalized
        user.save(update_fields=["normalized_email"])
        updated += 1
    print(f"Backfilled normalized_email for {updated} user(s).")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_email_verified_user_email_verified_at_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_normalized_emails, noop),
    ]
