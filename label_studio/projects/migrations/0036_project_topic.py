from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workspaces', '0001_initial'),
        ('projects', '0035_project_workspace_archive_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='topic',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='projects',
                to='workspaces.topic',
            ),
        ),
    ]
