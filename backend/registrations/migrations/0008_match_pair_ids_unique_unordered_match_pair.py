# Generated manually to enforce unordered pair uniqueness on Match

from django.db import migrations, models


def detect_duplicates_and_backfill_pairs(apps, schema_editor):
    Match = apps.get_model("registrations", "Match")
    seen_pairs = {}
    duplicates = []

    for match in Match.objects.all():
        reg_id = str(match.registration_id)
        cand_id = str(match.candidate_id)
        low, high = sorted([reg_id, cand_id])

        pair_key = (low, high)
        if pair_key in seen_pairs:
            duplicates.append(
                f"Duplicate unordered pair: Match #{match.pk} ({reg_id}, {cand_id}) "
                f"conflicts with Match #{seen_pairs[pair_key]}"
            )
        else:
            seen_pairs[pair_key] = match.pk

        match.pair_low_id = low
        match.pair_high_id = high
        match.save(update_fields=["pair_low_id", "pair_high_id"])

    if duplicates:
        raise RuntimeError(
            "Cannot apply unique constraint to Match: existing duplicate unordered pairs detected:\n"
            + "\n".join(duplicates)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0007_registration_candidate_photo_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="pair_low_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="match",
            name="pair_high_id",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.RunPython(
            detect_duplicates_and_backfill_pairs,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="match",
            name="pair_low_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AlterField(
            model_name="match",
            name="pair_high_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="match",
            constraint=models.UniqueConstraint(
                fields=["pair_low_id", "pair_high_id"],
                name="unique_unordered_match_pair",
            ),
        ),
    ]
