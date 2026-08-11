from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizations', '0008_organization_workspace_visibility'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvitePreset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=256, unique=True, verbose_name='token')),
                (
                    'default_role',
                    models.CharField(
                        choices=[
                            ('OWNER', 'Owner'),
                            ('ADMIN', 'Admin'),
                            ('MANAGER', 'Manager'),
                            ('ANNOTATOR', 'Annotator'),
                            ('VIEWER', 'Viewer'),
                        ],
                        default='ANNOTATOR',
                        max_length=32,
                        verbose_name='default role',
                    ),
                ),
                ('team_ids', models.JSONField(blank=True, default=list)),
                ('workspace_ids', models.JSONField(blank=True, default=list)),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='expires at')),
                ('max_uses', models.PositiveIntegerField(blank=True, null=True, verbose_name='max uses')),
                ('uses_count', models.PositiveIntegerField(default=0, verbose_name='uses count')),
                ('is_active', models.BooleanField(default=True, verbose_name='active')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                (
                    'created_by',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='created_invite_presets',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'organization',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='invite_presets',
                        to='organizations.organization',
                    ),
                ),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
