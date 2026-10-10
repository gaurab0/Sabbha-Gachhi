from django.core.management.base import BaseCommand, CommandError

from accounts.models import VerificationSendLog


class Command(BaseCommand):
    help = "Clear email verification resend daily-cap rows."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--user-id", help="Clear email send-log rows for one user id.")
        group.add_argument(
            "--all",
            action="store_true",
            help="Clear all email send-log rows for all users.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be deleted without deleting them.",
        )

    def handle(self, *args, **options):
        qs = VerificationSendLog.objects.filter(kind="email")
        if options["user_id"]:
            qs = qs.filter(user_id=options["user_id"])

        count = qs.count()
        scope = "all users" if options["all"] else f"user_id={options['user_id']}"
        if options["dry_run"]:
            self.stdout.write(
                f"Would delete {count} email VerificationSendLog row(s) for {scope}."
            )
            return
        if count == 0:
            self.stdout.write(f"No email VerificationSendLog rows found for {scope}.")
            return
        deleted, details = qs.delete()
        if deleted < count:
            raise CommandError(
                f"Expected to delete {count} rows for {scope}, deleted {deleted}: {details}"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {count} email VerificationSendLog row(s) for {scope}."
            )
        )
