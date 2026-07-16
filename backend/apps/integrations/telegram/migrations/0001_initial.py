import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_chat_id', models.CharField(blank=True, max_length=64)),
                ('telegram_username', models.CharField(blank=True, max_length=255)),
                ('linking_code', models.CharField(blank=True, max_length=32, null=True, unique=True)),
                ('enabled', models.BooleanField(default=True)),
                ('last_contact_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='telegram_connection', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
