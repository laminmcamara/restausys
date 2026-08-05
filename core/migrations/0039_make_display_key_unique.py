import core.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0038_auto_20260804_1028"),
    ]

    operations = [
        migrations.AlterField(
            model_name="restaurant",
            name="display_key",
            field=models.CharField(
                max_length=64,
                unique=True,
                default=core.models.generate_display_key,
            ),
        ),
    ]