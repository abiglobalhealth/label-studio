import pytest
from core.rbac import _assigned_workspace_ids, _organization_has_workspace_restrictions, workspace_visibility_q
from organizations.models import Organization, OrganizationMember
from organizations.tests.factories import OrganizationFactory
from users.tests.factories import UserFactory
from workspaces.models import Team, TeamMember, Workspace, WorkspaceTeamAssignment, WorkspaceUserAssignment


@pytest.mark.django_db
def test_auto_mode_restricts_once_an_assignment_exists():
    org = OrganizationFactory()
    assert org.workspace_visibility == Organization.WorkspaceVisibility.AUTO

    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    assert not _organization_has_workspace_restrictions(org)
    WorkspaceUserAssignment.objects.create(workspace=workspace, user=user)
    assert _organization_has_workspace_restrictions(org)


@pytest.mark.django_db
def test_open_mode_never_restricts_even_with_assignments():
    org = OrganizationFactory(workspace_visibility=Organization.WorkspaceVisibility.OPEN)
    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)
    WorkspaceUserAssignment.objects.create(workspace=workspace, user=user)

    assert not _organization_has_workspace_restrictions(org)
    visible_ids = set(Workspace.objects.filter(organization=org).filter(workspace_visibility_q(user)).values_list('id', flat=True))
    assert workspace.id in visible_ids


@pytest.mark.django_db
def test_restricted_mode_restricts_even_without_assignments():
    org = OrganizationFactory(workspace_visibility=Organization.WorkspaceVisibility.RESTRICTED)
    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    assert _organization_has_workspace_restrictions(org)
    visible_ids = set(Workspace.objects.filter(organization=org).filter(workspace_visibility_q(user)).values_list('id', flat=True))
    assert workspace.id not in visible_ids


@pytest.mark.django_db
def test_assigned_workspace_ids_cached_on_user_instance():
    org = OrganizationFactory()
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    workspace = Workspace.objects.create(organization=org, title='W', created_by=org.created_by)
    WorkspaceUserAssignment.objects.create(workspace=workspace, user=user)

    first = _assigned_workspace_ids(user, organization=org)
    assert first == [workspace.id]

    team = Team.objects.create(organization=org, title='T')
    TeamMember.objects.create(team=team, user=user)
    WorkspaceTeamAssignment.objects.create(workspace=workspace, team=team)

    cache_key = f'_assigned_workspace_ids_{org.pk}'
    assert getattr(user, cache_key, None) == first
    second = _assigned_workspace_ids(user, organization=org)
    assert second == first
