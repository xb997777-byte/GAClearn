from django.db import migrations, models


def migrate_default_theme_to_blue(apps, schema_editor):
    UserSetting = apps.get_model("users", "UserSetting")
    UserSetting.objects.filter(theme_id="duo_forest").update(theme_id="busuu_ocean")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_usersetting_custom_theme"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usersetting",
            name="theme_id",
            field=models.CharField(default="busuu_ocean", max_length=32, verbose_name="主题"),
        ),
        migrations.RunPython(migrate_default_theme_to_blue, migrations.RunPython.noop),
    ]
