from django.contrib import admin

from .models import MatchAttemptLog


@admin.register(MatchAttemptLog)
class MatchAttemptLogAdmin(admin.ModelAdmin):
    list_display = ["registration", "outcome", "matched_registration", "ran_at"]
    list_filter = ["outcome"]
    readonly_fields = [
        "registration", "ran_at", "outcome", "matched_registration",
        "candidates_considered", "sapinda_rules_version",
    ]

# Register your models here.
