from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0006_agent_runtime_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="aimessage",
            name="runtime_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="conversation_messages",
                to="ai.aiasyncrun",
                verbose_name="关联运行",
            ),
        ),
    ]
