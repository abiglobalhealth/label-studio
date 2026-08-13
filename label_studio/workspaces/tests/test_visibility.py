import pytest

from core.rbac import workspace_visibility_q
from organizations.models import OrganizationMember
from organizations.tests.factories import OrganizationFactory
from projects.models import ProjectMember
from projects.tests.factories import ProjectFactory
from users.tests.factories import UserFactory
from workspaces.models import Team, TeamManager, TeamMember, Workspace, WorkspaceTeamAssignment, WorkspaceUserAssignment


@pytest.mark.django_db
def test_annotator_workspace_visibility_via_direct_assignment():
    org = OrganizationFactory()
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    workspace_visible = Workspace.objects.create(organization=org, title='Visible', created_by=org.created_by)
    workspace_hidden = Workspace.objects.create(organization=org, title='Hidden', created_by=org.created_by)
    WorkspaceUserAssignment.objects.create(workspace=workspace_visible, user=user)

    visible_ids = set(Workspace.objects.filter(organization=org).filter(workspace_visibility_q(user)).values_list('id', flat=True))
    assert workspace_visible.id in visible_ids
    assert workspace_hidden.id not in visible_ids


@pytest.mark.django_db
def test_annotator_workspace_visibility_via_team_assignment():
    org = OrganizationFactory()
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    workspace = Workspace.objects.create(organization=org, title='Team Workspace', created_by=org.created_by)
    team = Team.objects.create(organization=org, title='A Team')
    TeamMember.objects.create(team=team, user=user)
    WorkspaceTeamAssignment.objects.create(workspace=workspace, team=team)

    assert Workspace.objects.filter(id=workspace.id).filter(workspace_visibility_q(user)).exists()


@pytest.mark.django_db
def test_annotator_has_no_workspace_visibility_without_explicit_assignments():
    org = OrganizationFactory()
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    workspace_a = Workspace.objects.create(organization=org, title='General', created_by=org.created_by)
    workspace_b = Workspace.objects.create(organization=org, title='Backlog', created_by=org.created_by)

    visible_ids = set(Workspace.objects.filter(organization=org).filter(workspace_visibility_q(user)).values_list('id', flat=True))
    assert not visible_ids


@pytest.mark.django_db
def test_project_visibility_is_project_assignment_based_not_creator_based():
    org = OrganizationFactory()
    owner = org.created_by
    annotator = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=annotator, organization=org).update(role=OrganizationMember.Roles.ANNOTATOR)

    workspace_owner = Workspace.objects.create(organization=org, title='Owner Workspace', created_by=owner)
    workspace_team = Workspace.objects.create(organization=org, title='Team Workspace', created_by=owner)
    workspace_other = Workspace.objects.create(organization=org, title='Other Workspace', created_by=owner)

    team = Team.objects.create(organization=org, title='Annotators')
    TeamMember.objects.create(team=team, user=annotator)
    WorkspaceTeamAssignment.objects.create(workspace=workspace_team, team=team)

    own_project = ProjectFactory(organization=org, workspace=workspace_owner, created_by=annotator)
    team_project = ProjectFactory(organization=org, workspace=workspace_team, created_by=owner)
    other_project = ProjectFactory(organization=org, workspace=workspace_other, created_by=owner)
    ProjectMember.objects.create(project=own_project, user=annotator)

    visible_ids = set(type(own_project).objects.for_user(annotator).values_list('id', flat=True))

    assert team_project.id in visible_ids
    assert own_project.id in visible_ids
    assert other_project.id not in visible_ids


@pytest.mark.django_db
def test_manager_project_visibility_is_limited_to_assigned_team_workspaces():
    org = OrganizationFactory()
    manager = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=manager, organization=org).update(role=OrganizationMember.Roles.MANAGER)

    assigned_workspace = Workspace.objects.create(organization=org, title='Assigned', created_by=org.created_by)
    other_workspace = Workspace.objects.create(organization=org, title='Other', created_by=org.created_by)
    team = Team.objects.create(organization=org, title='Managed Team')
    TeamManager.objects.create(team=team, user=manager)
    WorkspaceTeamAssignment.objects.create(workspace=assigned_workspace, team=team)

    assigned_project = ProjectFactory(organization=org, workspace=assigned_workspace)
    other_project = ProjectFactory(organization=org, workspace=other_workspace)

    visible_ids = set(type(assigned_project).objects.for_user(manager).values_list('id', flat=True))

    assert assigned_project.id in visible_ids
    assert other_project.id not in visible_ids
