from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_workspace_for_existing_projects(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    Workspace = apps.get_model('workspaces', 'Workspace')
    Project = apps.get_model('projects', 'Project')

    for organization in Organization.objects.all().iterator():
        workspace, _ = Workspace.objects.get_or_create(
            organization_id=organization.id,
            title='General',
            defaults={'created_by_id': organization.created_by_id},
        )
        Project.objects.filter(organization_id=organization.id, workspace_id__isnull=True).update(workspace_id=workspace.id)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workspaces', '0001_initial'),
        ('projects', '0034_project_annotator_evaluation_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='archived at'),
        ),
        migrations.AddField(
            model_name='project',
            name='archived_by',
            field=models.ForeignKey(
                blank=True,
                db_index=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='archived_projects',
                to=settings.AUTH_USER_MODEL,
                verbose_name='archived by',
            ),
        ),
        migrations.AddField(
            model_name='project',
            name='workspace',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='workspaces.workspace',
            ),
        ),
        migrations.RunPython(backfill_workspace_for_existing_projects, migrations.RunPython.noop),
    ]
