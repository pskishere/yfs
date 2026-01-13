# Generated migration file for AI chat models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ystock', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(max_length=100, unique=True, verbose_name='会话ID')),
                ('summary', models.TextField(blank=True, null=True, verbose_name='会话摘要')),
                ('context_symbols', models.JSONField(blank=True, default=list, verbose_name='会话关注的股票代码列表')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'AI聊天会话',
                'verbose_name_plural': 'AI聊天会话',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', '用户'), ('assistant', 'AI助手'), ('system', '系统')], max_length=20, verbose_name='角色')),
                ('content', models.TextField(verbose_name='消息内容')),
                ('status', models.CharField(choices=[('pending', '等待中'), ('streaming', '生成中'), ('completed', '已完成'), ('error', '错误'), ('cancelled', '已取消')], default='completed', max_length=20, verbose_name='状态')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='错误信息')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='元数据（如引用的股票代码、指标数据等）')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='ystock.chatsession', verbose_name='会话')),
            ],
            options={
                'verbose_name': 'AI聊天消息',
                'verbose_name_plural': 'AI聊天消息',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='chatsession',
            index=models.Index(fields=['-updated_at'], name='ystock_chat_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['session', 'created_at'], name='ystock_chat_session_created_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['session', 'status'], name='ystock_chat_session_status_idx'),
        ),
    ]
