"""
Management command that pings the Celery worker and fails loudly if none
responds, so the silent-no-op failure mode of the async matching engine is
visible in dev/staging instead of swallowing tasks.

The matching engine (registrations.signals) dispatches
``run_matching_engine_task.delay(...)`` on verification, but if no worker is
consuming from the broker the tasks sit in the queue forever and
MatchAttemptLog/MatchProposal rows are never created — with no error surfaced
anywhere. Run this in a startup/health check to catch that condition early.

Usage:
    python manage.py check_celery_worker [--timeout SECONDS]

Exits with code 0 if at least one worker responds to a ping, 1 otherwise.
"""

import logging

from celery import current_app
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

NO_WORKER_MESSAGE = (
    "No Celery worker responded to the ping. The async matching engine is NOT "
    "running: registrations will be verified but never matched, and tasks sit "
    "unconsumed in the broker. Start the worker with "
    "`scripts/run_worker.ps1` (Windows) or `scripts/run_worker.sh` "
    "(Linux/WSL/prod), see README 'Running the async worker'."
)


class Command(BaseCommand):
    help = "Ping Celery workers and fail loudly if none is consuming tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=float,
            default=5.0,
            help="Seconds to wait for a worker ping reply (default: 5).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]

        try:
            pings = current_app.control.ping(timeout=timeout)
        except Exception as exc:
            broker = current_app.conf.broker_url
            message = (
                f"Could not reach the Celery broker ({broker}): {exc}. "
                "Is Redis running? Without a broker no tasks can be dispatched."
            )
            logger.error(message)
            raise CommandError(message) from exc

        if not pings:
            logger.error(NO_WORKER_MESSAGE)
            raise CommandError(NO_WORKER_MESSAGE)

        workers = sorted(ping_key for ping in pings for ping_key in ping)
        message = (
            f"Celery worker(s) responding to ping: {', '.join(workers)}. "
            "Async matching engine is online."
        )
        logger.info(message)
        self.stdout.write(self.style.SUCCESS(message))