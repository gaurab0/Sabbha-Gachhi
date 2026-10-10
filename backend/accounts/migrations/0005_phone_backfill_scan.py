"""Phone verification backfill (non-breaking).

- Defaults (phone_verified=False, risk_flags=[]) apply automatically to
  existing rows — no update needed.
- Duplicate scan: reports any E.164 already claimed twice so ops can resolve
  BEFORE the unique index on User.phone bites. (Current data has none —
  verified safe on 2026-09-30; the scan stays as a guard for other envs.)

Grace-period choice (no code change needed for either):
(a) Force on next login: gate the remaining email-only routes with
    RequireFullyVerified in registrations/views.py (create/status/withdraw/
    concern currently stay email-only).
(b) Banner + deadline (default): frontend shows "verify your phone" banner
    until PHONE_GRACE_DEADLINE, then flip the gates above.
"""

from django.db import migrations


def scan_duplicate_phones(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    seen = {}
    dupes = 0
    for user in User.objects.all().only("id", "email", "phone").iterator():
        phone = (user.phone or "").strip()
        if not phone:
            continue
        if phone in seen:
            dupes += 1
            print(f"DUPLICATE phone {phone!r}: user {seen[phone]} and {user.pk} ({user.email})")
        else:
            seen[phone] = user.pk
    print(f"Phone duplicate scan: {len(seen)} distinct numbers, {dupes} collision(s).")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_emailverificationtoken_channel_user_pending_phone_and_more"),
    ]

    operations = [
        migrations.RunPython(scan_duplicate_phones, noop),
    ]
