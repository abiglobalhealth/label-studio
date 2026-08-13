from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizations', '0007_organizationmember_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topics', to='organizations.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('description', models.TextField(blank=True, default='', null=True, verbose_name='description')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teams', to='organizations.organization')),
            ],
        ),
        migrations.CreateModel(
            name='Workspace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('description', models.TextField(blank=True, default='', null=True, verbose_name='description')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='updated at')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_workspaces', to=settings.AUTH_USER_MODEL)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspaces', to='organizations.organization')),
            ],
        ),
        migrations.CreateModel(
            name='TeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='workspaces.team')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_memberships', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceUserAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspace_assignments', to=settings.AUTH_USER_MODEL)),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_assignments', to='workspaces.workspace')),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceTeamAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspace_assignments', to='workspaces.team')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='team_assignments', to='workspaces.workspace')),
            ],
        ),
        migrations.CreateModel(
            name='WorkspaceTopicAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('topic', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workspace_assignments', to='workspaces.topic')),
                ('workspace', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='topic_assignments', to='workspaces.workspace')),
            ],
        ),
        migrations.AddConstraint(
            model_name='topic',
            constraint=models.UniqueConstraint(fields=('organization', 'title'), name='uq_topic_org_title'),
        ),
        migrations.AddConstraint(
            model_name='team',
            constraint=models.UniqueConstraint(fields=('organization', 'title'), name='uq_team_org_title'),
        ),
        migrations.AddConstraint(
            model_name='workspace',
            constraint=models.UniqueConstraint(fields=('organization', 'title'), name='uq_workspace_org_title'),
        ),
        migrations.AddConstraint(
            model_name='teammember',
            constraint=models.UniqueConstraint(fields=('team', 'user'), name='uq_team_member'),
        ),
        migrations.AddConstraint(
            model_name='workspaceuserassignment',
            constraint=models.UniqueConstraint(fields=('workspace', 'user'), name='uq_workspace_user_assignment'),
        ),
        migrations.AddConstraint(
            model_name='workspaceteamassignment',
            constraint=models.UniqueConstraint(fields=('workspace', 'team'), name='uq_workspace_team_assignment'),
        ),
        migrations.AddConstraint(
            model_name='workspacetopicassignment',
            constraint=models.UniqueConstraint(fields=('workspace', 'topic'), name='uq_workspace_topic_assignment'),
        ),
    ]
