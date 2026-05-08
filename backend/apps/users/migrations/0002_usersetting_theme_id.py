from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usersetting",
            name="theme_id",
            field=models.CharField(default="duo_forest", max_length=32, verbose_name="主题"),
        ),
    ]
