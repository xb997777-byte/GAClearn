from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("review", "0002_reviewrecord_answer_feedback"),
    ]

    operations = [
        migrations.AddField(
            model_name="reviewsession",
            name="extra_payload",
            field=models.JSONField(blank=True, default=dict, verbose_name="会话快照"),
        ),
    ]
