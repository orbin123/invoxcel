import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("templates", "0001_initial"),
        ("uploads", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="uploadeddocument",
            name="template",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="uploaded_documents",
                to="templates.template",
            ),
        ),
    ]
