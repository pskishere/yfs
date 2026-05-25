from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatmessage',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('streaming', 'Streaming'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('error', 'Error'),
                ],
                default='completed',
                max_length=20,
                verbose_name='状态',
            ),
        ),
    ]
