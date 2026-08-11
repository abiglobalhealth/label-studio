from types import SimpleNamespace

import pytest

from core.current_request import CurrentContext
from organizations.tests.factories import OrganizationFactory
from projects.tests.factories import ProjectFactory
from users.tests.factories import UserFactory
from workspaces.models import Workspace


@pytest.mark.django_db
def test_archived_project_hidden_from_default_manager():
    org = OrganizationFactory()
    workspace = Workspace.objects.create(organization=org, title='General', created_by=org.created_by)

    visible = ProjectFactory(organization=org, workspace=workspace)
    archived = ProjectFactory(organization=org, workspace=workspace)
    archived.archived_at = visible.created_at
    archived.save(update_fields=['archived_at'])

    assert type(visible).objects.filter(id=visible.id).exists()
    assert not type(visible).objects.filter(id=archived.id).exists()
    assert type(visible).all_objects.filter(id=archived.id).exists()


@pytest.mark.django_db
def test_archived_project_is_read_only_for_mutations():
    org = OrganizationFactory()
    workspace = Workspace.objects.create(organization=org, title='General', created_by=org.created_by)
    user = UserFactory(active_organization=org)

    project = ProjectFactory(organization=org, workspace=workspace)
    project.archived_at = project.created_at
    project.save(update_fields=['archived_at'])

    CurrentContext.set_request(SimpleNamespace(method='PATCH', user=user))
    try:
        assert not project.has_permission(user)
    finally:
        CurrentContext.clear()
