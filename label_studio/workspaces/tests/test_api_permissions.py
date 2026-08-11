import pytest
from organizations.models import Organization, OrganizationMember
from organizations.tests.factories import OrganizationFactory
from rest_framework.test import APIClient
from users.tests.factories import UserFactory
from workspaces.models import Team, TeamManager, Topic, Workspace, WorkspaceUserAssignment


def _user(org, role):
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=role)
    return user


@pytest.mark.django_db
def test_annotator_can_list_scoped_workspaces():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.get('/api/workspaces')
    assert response.status_code == 200


@pytest.mark.django_db
def test_annotator_cannot_create_workspace():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.post('/api/workspaces', {'title': 'Nope'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_annotator_cannot_change_workspace():
    org = OrganizationFactory()
    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.patch(f'/api/workspaces/{workspace.id}', {'title': 'Hacked'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_cannot_create_workspace():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    response = client.post('/api/workspaces', {'title': 'New'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_cannot_delete_workspace():
    org = OrganizationFactory()
    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    response = client.delete(f'/api/workspaces/{workspace.id}')
    assert response.status_code == 403
    assert Workspace.objects.filter(id=workspace.id).exists()


@pytest.mark.django_db
def test_manager_cannot_delete_team():
    org = OrganizationFactory()
    team = Team.objects.create(organization=org, title='Team')
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    response = client.delete(f'/api/teams/{team.id}')
    assert response.status_code == 403
    assert Team.objects.filter(id=team.id).exists()


@pytest.mark.django_db
def test_manager_cannot_delete_topic():
    org = OrganizationFactory()
    topic = Topic.objects.create(organization=org, title='Topic')
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    response = client.delete(f'/api/topics/{topic.id}')
    assert response.status_code == 403
    assert Topic.objects.filter(id=topic.id).exists()


@pytest.mark.django_db
def test_manager_cannot_create_team_and_topic():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    team_response = client.post('/api/teams', {'title': 'Team'}, format='json')
    topic_response = client.post('/api/topics', {'title': 'Topic'}, format='json')
    assert team_response.status_code == 403
    assert topic_response.status_code == 403


@pytest.mark.django_db
def test_annotator_cannot_manage_team_members():
    org = OrganizationFactory()
    team = Team.objects.create(organization=org, title='Team')
    target = UserFactory(active_organization=org)
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.post(
        '/api/teams/members',
        {'team': team.id, 'user': target.id},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_annotator_can_list_assigned_workspaces_only():
    org = OrganizationFactory(workspace_visibility=Organization.WorkspaceVisibility.RESTRICTED)
    visible = Workspace.objects.create(organization=org, title='Visible', created_by=org.created_by)
    hidden = Workspace.objects.create(organization=org, title='Hidden', created_by=org.created_by)
    user = _user(org, OrganizationMember.Roles.ANNOTATOR)
    WorkspaceUserAssignment.objects.create(workspace=visible, user=user)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get('/api/workspaces')
    assert response.status_code == 200
    titles = {item['title'] for item in response.json()}
    assert titles == {'Visible'}


@pytest.mark.django_db
def test_manager_cannot_change_organization_visibility():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.MANAGER))
    response = client.patch(
        f'/api/organizations/{org.id}',
        {'workspace_visibility': Organization.WorkspaceVisibility.RESTRICTED},
        format='json',
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_owner_can_assign_multiple_team_managers():
    org = OrganizationFactory()
    manager_a = _user(org, OrganizationMember.Roles.MANAGER)
    manager_b = _user(org, OrganizationMember.Roles.MANAGER)
    team = Team.objects.create(organization=org, title='Team')
    client = APIClient()
    client.force_authenticate(user=org.created_by)

    first = client.post('/api/teams/managers', {'team': team.id, 'user': manager_a.id}, format='json')
    second = client.post('/api/teams/managers', {'team': team.id, 'user': manager_b.id}, format='json')

    assert first.status_code == 201
    assert second.status_code == 201
    assert TeamManager.objects.filter(team=team).count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize('role', [OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN])
def test_owner_and_admin_can_be_assigned_as_team_managers(role):
    org = OrganizationFactory()
    team_manager = _user(org, role)
    team = Team.objects.create(organization=org, title='Team')
    client = APIClient()
    client.force_authenticate(user=org.created_by)

    response = client.post('/api/teams/managers', {'team': team.id, 'user': team_manager.id}, format='json')

    assert response.status_code == 201
    assert TeamManager.objects.filter(team=team, user=team_manager).exists()


@pytest.mark.django_db
def test_team_manager_assignment_requires_manager_role():
    org = OrganizationFactory()
    viewer = _user(org, OrganizationMember.Roles.VIEWER)
    team = Team.objects.create(organization=org, title='Team')
    client = APIClient()
    client.force_authenticate(user=org.created_by)

    response = client.post('/api/teams/managers', {'team': team.id, 'user': viewer.id}, format='json')

    assert response.status_code == 400
    assert not TeamManager.objects.filter(team=team, user=viewer).exists()


@pytest.mark.django_db
def test_annotator_cannot_change_organization_visibility():
    org = OrganizationFactory()
    client = APIClient()
    client.force_authenticate(user=_user(org, OrganizationMember.Roles.ANNOTATOR))
    response = client.patch(
        f'/api/organizations/{org.id}',
        {'workspace_visibility': Organization.WorkspaceVisibility.RESTRICTED},
        format='json',
    )
    assert response.status_code == 403
