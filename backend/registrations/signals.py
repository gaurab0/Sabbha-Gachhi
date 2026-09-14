from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Registration


@receiver(pre_save, sender=Registration)
def _flag_verification_transition(sender, instance, **kwargs):
    """
    Runs just before save. Compares against the DB's current state to
    detect the exact moment a registration flips from pending -> verified.
    We stash the result on the instance so post_save (below) can act on it
    after the save actually completes.
    """
    if not instance.pk:
        # Brand new registration being created for the first time —
        # nothing to compare against yet.
        instance._just_became_verified = False
        return

    try:
        previous = Registration.objects.get(pk=instance.pk)
    except Registration.DoesNotExist:
        instance._just_became_verified = False
        return

    instance._just_became_verified = (
        previous.verification_status != Registration.VerificationStatus.VERIFIED
        and instance.verification_status == Registration.VerificationStatus.VERIFIED
    )


@receiver(post_save, sender=Registration)
def _run_matching_after_verification(sender, instance, created, **kwargs):
    """
    Runs right after save. If this save just verified the registration,
    kick off the automated matching pipeline for it.
    """
    if created:
        return  # a brand new registration can't already be "verified" on arrival

    if getattr(instance, "_just_became_verified", False):
        from .matching import create_automated_proposal
        create_automated_proposal(instance)