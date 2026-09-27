"""
Celery tasks for the Sabha Gachhi backend.
"""

from celery import shared_task

from .models import Registration
from .matching_engine import run_matching_engine, create_automated_proposal
from .notifications import send_match_notification


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_matching_engine_task(self, registration_id: int):
    """
    Celery task that runs the automated matchmaking engine for a
    registration, persists Match records, and creates automated
    MatchProposal records for the top candidate. Idempotent —
    re-running upserts Match records rather than duplicating them.

    Usage:
        run_matching_engine_task.delay(registration_id)
    """
    from .models import Registration, Match

    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        # retry() re-queues the task and raises celery.exceptions.Retry
        # (throw=True by default), so execution never falls through here.
        raise self.retry(countdown=30)

    # Run the full pipeline and create proposals.
    # create_automated_proposal calls run_matching_engine internally,
    # so the engine runs once and Match rows are created idempotently.
    proposal = create_automated_proposal(registration)

    # Notify both users about new matches. Dereference the FK so we
    # pass Registration instances (values_list would hand back raw ids).
    # Materialize once to avoid re-querying for the final count.
    final_matches = list(
        Match.objects.filter(
            registration=registration,
            status=Match.Status.PENDING,
        )
    )
    for match in final_matches:
        candidate = match.candidate
        send_match_notification(registration, candidate)
        send_match_notification(candidate, registration)

    return {
        "registration_reference": registration.reference,
        "final_match_count": len(final_matches),
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def create_automated_proposal_task(self, registration_id: int):
    """
    Celery task that creates a MatchProposal for a registration
    after matching. Separate task so the engine and proposal creation
    can be monitored independently.
    """
    from .models import Registration

    try:
        registration = Registration.objects.get(pk=registration_id)
    except Registration.DoesNotExist:
        # retry() re-queues the task and raises celery.exceptions.Retry
        # (throw=True by default), so execution never falls through here.
        raise self.retry(countdown=30)

    proposal = create_automated_proposal(registration)

    if proposal:
        return {"proposal_id": proposal.id, "reference": registration.reference}
    return {"proposal_id": None, "reference": registration.reference}
