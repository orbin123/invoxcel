from django.db import migrations, models


def assign_user_batch_numbers(apps, schema_editor):
    AnalysisBatch = apps.get_model("processing", "AnalysisBatch")
    user_ids = AnalysisBatch.objects.order_by().values_list("user_id", flat=True).distinct()
    for user_id in user_ids:
        batches = AnalysisBatch.objects.filter(user_id=user_id).order_by("created_at", "pk")
        for number, batch in enumerate(batches, start=1):
            AnalysisBatch.objects.filter(pk=batch.pk).update(number=number)


class Migration(migrations.Migration):
    dependencies = [
        ("processing", "0008_remove_excel_layout"),
    ]

    operations = [
        migrations.AddField(
            model_name="analysisbatch",
            name="number",
            field=models.PositiveIntegerField(editable=False, null=True),
        ),
        migrations.RunPython(assign_user_batch_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="analysisbatch",
            name="number",
            field=models.PositiveIntegerField(editable=False),
        ),
        migrations.AddConstraint(
            model_name="analysisbatch",
            constraint=models.UniqueConstraint(
                fields=("user", "number"),
                name="unique_user_batch_number",
            ),
        ),
    ]
