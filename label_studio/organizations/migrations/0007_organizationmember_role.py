from django.db import migrations, models


def backfill_owner_roles(apps, schema_editor):
    Organization = apps.get_model('organizations', 'Organization')
    OrganizationMember = apps.get_model('organizations', 'OrganizationMember')

    for organization in Organization.objects.exclude(created_by_id=None).iterator():
        OrganizationMember.objects.filter(
            organization_id=organization.id,
            user_id=organization.created_by_id,
            deleted_at__isnull=True,
        ).update(role='OWNER')


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0006_alter_organizationmember_deleted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationmember',
            name='role',
            field=models.CharField(
                choices=[
                    ('OWNER', 'Owner'),
                    ('ADMIN', 'Admin'),
                    ('MANAGER', 'Manager'),
                    ('ANNOTATOR', 'Annotator'),
                    ('VIEWER', 'Viewer'),
                ],
                db_index=True,
                default='ANNOTATOR',
                help_text='Organization membership role used for RBAC checks.',
                max_length=32,
                verbose_name='role',
            ),
        ),
        migrations.RunPython(backfill_owner_roles, migrations.RunPython.noop),
    ]
