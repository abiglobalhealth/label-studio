import pytest
from core.api_permissions import RoleBasedPermission
from core.permissions import ViewClassPermission, all_permissions
from django.contrib.auth.models import AnonymousUser
from organizations.models import OrganizationMember
from organizations.tests.factories import OrganizationFactory
from projects.tests.factories import ProjectFactory
from rest_framework.test import APIClient, APIRequestFactory
from users.tests.factories import UserFactory
from workspaces.models import Workspace


class _NoPermissionView:
    permission_required = None


class _ProjectsVCView:
    permission_required = ViewClassPermission(
        GET=all_permissions.projects_view,
        POST=all_permissions.projects_create,
        PATCH=all_permissions.projects_change,
        PUT=all_permissions.projects_change,
        DELETE=all_permissions.projects_delete,
    )


class _StringPermissionView:
    permission_required = all_permissions.projects_change


def _request(method='GET'):
    factory = APIRequestFactory()
    return factory.generic(method, '/')


def _user(org, role):
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=role)
    return user


@pytest.mark.django_db
@pytest.mark.parametrize(
    'role',
    [
        OrganizationMember.Roles.OWNER,
        OrganizationMember.Roles.ADMIN,
        OrganizationMember.Roles.MANAGER,
        OrganizationMember.Roles.ANNOTATOR,
        OrganizationMember.Roles.VIEWER,
    ],
)
def test_no_permission_declared_allows_every_role(role):
    org = OrganizationFactory()
    request = _request('GET')
    request.user = _user(org, role)
    assert RoleBasedPermission().has_permission(request, _NoPermissionView()) is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    'role,method,expected',
    [
        (OrganizationMember.Roles.OWNER, 'GET', True),
        (OrganizationMember.Roles.OWNER, 'POST', True),
        (OrganizationMember.Roles.OWNER, 'PATCH', True),
        (OrganizationMember.Roles.OWNER, 'DELETE', True),
        (OrganizationMember.Roles.MANAGER, 'GET', True),
        (OrganizationMember.Roles.MANAGER, 'POST', True),
        (OrganizationMember.Roles.MANAGER, 'PATCH', True),
        (OrganizationMember.Roles.MANAGER, 'DELETE', True),
        (OrganizationMember.Roles.ANNOTATOR, 'GET', True),
        (OrganizationMember.Roles.ANNOTATOR, 'POST', False),
        (OrganizationMember.Roles.ANNOTATOR, 'PATCH', False),
        (OrganizationMember.Roles.ANNOTATOR, 'DELETE', False),
        (OrganizationMember.Roles.VIEWER, 'GET', True),
        (OrganizationMember.Roles.VIEWER, 'POST', False),
        (OrganizationMember.Roles.VIEWER, 'PATCH', False),
    ],
)
def test_view_class_permission_resolves_per_method(role, method, expected):
    org = OrganizationFactory()
    request = _request(method)
    request.user = _user(org, role)
    assert RoleBasedPermission().has_permission(request, _ProjectsVCView()) is expected


@pytest.mark.django_db
def test_string_permission_applies_to_all_methods():
    org = OrganizationFactory()
    request = _request('PATCH')
    request.user = _user(org, OrganizationMember.Roles.MANAGER)
    assert RoleBasedPermission().has_permission(request, _StringPermissionView()) is True
    request.user = _user(org, OrganizationMember.Roles.ANNOTATOR)
    assert RoleBasedPermission().has_permission(request, _StringPermissionView()) is False


@pytest.mark.django_db
def test_anonymous_user_is_denied():
    request = _request('GET')
    request.user = AnonymousUser()
    assert RoleBasedPermission().has_permission(request, _ProjectsVCView()) is False


@pytest.mark.django_db
def test_unmapped_method_is_allowed():
    org = OrganizationFactory()
    request = _request('OPTIONS')
    request.user = _user(org, OrganizationMember.Roles.VIEWER)
    view = type('V', (), {'permission_required': ViewClassPermission(GET=all_permissions.projects_view)})()
    assert RoleBasedPermission().has_permission(request, view) is True


@pytest.mark.django_db
def test_annotator_cannot_create_project():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.post('/api/projects/', {'title': 'X'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_annotator_cannot_update_project():
    org = OrganizationFactory()
    project = ProjectFactory(organization=org)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.patch(f'/api/projects/{project.id}/', {'title': 'Hacked'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_viewer_cannot_update_project():
    org = OrganizationFactory()
    project = ProjectFactory(organization=org)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.VIEWER))
    response = client.patch(f'/api/projects/{project.id}/', {'title': 'Hacked'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_annotator_can_list_projects():
    org = OrganizationFactory()
    ProjectFactory(organization=org)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.get('/api/projects/')
    assert response.status_code == 200


@pytest.mark.django_db
def test_owner_can_update_project():
    org = OrganizationFactory()
    owner = org.created_by
    project = ProjectFactory(organization=org)
    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.patch(f'/api/projects/{project.id}/', {'title': 'Renamed'}, format='json')
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.title == 'Renamed'


@pytest.mark.django_db
def test_cannot_delete_workspace_with_projects():
    org = OrganizationFactory()
    owner = org.created_by
    workspace = Workspace.objects.create(organization=org, title='General', created_by=owner)
    ProjectFactory(organization=org, workspace=workspace)
    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.delete(f'/api/workspaces/{workspace.id}')
    assert response.status_code == 400
    assert Workspace.objects.filter(id=workspace.id).exists()


@pytest.mark.django_db
def test_can_delete_empty_workspace():
    org = OrganizationFactory()
    owner = org.created_by
    workspace = Workspace.objects.create(organization=org, title='Empty', created_by=owner)
    client = APIClient()
    client.force_authenticate(user=owner)
    response = client.delete(f'/api/workspaces/{workspace.id}')
    assert response.status_code == 204
    assert not Workspace.objects.filter(id=workspace.id).exists()


@pytest.mark.django_db
def test_project_rejects_workspace_from_another_organization():
    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    owner_b = org_b.created_by
    workspace_a = Workspace.objects.create(organization=org_a, title='A', created_by=org_a.created_by)
    client = APIClient()
    client.force_authenticate(user=owner_b)
    response = client.post('/api/projects/', {'title': 'X', 'workspace': workspace_a.id}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_project_rejects_topic_from_another_organization():
    from workspaces.models import Topic

    org_a = OrganizationFactory()
    org_b = OrganizationFactory()
    owner_b = org_b.created_by
    topic_a = Topic.objects.create(organization=org_a, title='Topic A')
    client = APIClient()
    client.force_authenticate(user=owner_b)
    response = client.post('/api/projects/', {'title': 'X', 'topic': topic_a.id}, format='json')
    assert response.status_code == 400
