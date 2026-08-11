from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('workspaces', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeamManager',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='managers', to='workspaces.team')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='managed_teams', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='teammanager',
            constraint=models.UniqueConstraint(fields=('team', 'user'), name='uq_team_manager'),
        ),
        migrations.AddIndex(
            model_name='teammanager',
            index=models.Index(fields=['user', 'team'], name='team_manager_user_team_idx'),
        ),
    ]
