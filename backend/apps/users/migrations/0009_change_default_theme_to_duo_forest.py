from django.db import migrations, models


def migrate_default_theme_to_green(apps, schema_editor):
    UserSetting = apps.get_model("users", "UserSetting")
    UserSetting.objects.filter(theme_id="busuu_ocean").update(theme_id="duo_forest")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_usersetting_personalized_rag_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usersetting",
            name="theme_id",
            field=models.CharField(default="duo_forest", max_length=32, verbose_name="主题"),
        ),
        migrations.RunPython(migrate_default_theme_to_green, migrations.RunPython.noop),
    ]
