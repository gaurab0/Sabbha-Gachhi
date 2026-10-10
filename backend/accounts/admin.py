from django.contrib import admin

from .models import EmailVerificationToken, User, VerificationSendLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """Moderator view: verification state + fraud signals at a glance.

    risk_flags are moderator-only — no end-user API ever serializes them.
    """

    list_display = (
        "email",
        "email_verified",
        "phone_verified",
        "phone_country",
        "is_staff",
        "date_joined",
    )
    list_filter = ("email_verified", "phone_verified", "phone_country", "is_staff")
    search_fields = ("email", "normalized_email", "phone", "pending_phone")
    readonly_fields = (
        "email_verified_at",
        "phone_verified_at",
        "risk_flags",
        "phone_changes_count",
        "date_joined",
        "last_login",
    )
    fieldsets = (
        (None, {"fields": ("email", "normalized_email", "is_active", "is_staff")}),
        (
            "Email verification",
            {"fields": ("email_verified", "email_verified_at", "pending_email")},
        ),
        (
            "Phone verification",
            {
                "fields": (
                    "phone",
                    "phone_verified",
                    "phone_verified_at",
                    "phone_country",
                    "phone_line_type",
                    "pending_phone",
                    "phone_changes_count",
                )
            },
        ),
        ("Moderation", {"fields": ("risk_flags",)}),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )


@admin.register(EmailVerificationToken)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "target", "channel", "used_at", "expires_at", "attempts")
    list_filter = ("type", "channel")
    readonly_fields = ("token_hash",)  # hashes only; raw secrets never stored
    search_fields = ("target",)


@admin.register(VerificationSendLog)
class SendLogAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "country", "provider", "ip_address", "created_at")
    list_filter = ("kind", "country", "provider")
