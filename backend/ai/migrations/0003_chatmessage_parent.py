from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0002_fix_message_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='children',
                to='ai.chatmessage',
                verbose_name='父消息',
            ),
        ),
    ]
