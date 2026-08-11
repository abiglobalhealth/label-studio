import pytest
from core.permissions import all_permissions
from core.rbac import has_permission
from organizations.models import OrganizationMember
from organizations.tests.factories import OrganizationFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
@pytest.mark.parametrize(
    'role,allowed,denied',
    [
        (OrganizationMember.Roles.OWNER, all_permissions.projects_delete, None),
        (OrganizationMember.Roles.ADMIN, all_permissions.organizations_invite, None),
        (OrganizationMember.Roles.MANAGER, all_permissions.projects_create, None),
        (OrganizationMember.Roles.MANAGER, all_permissions.projects_delete, all_permissions.workspaces_create),
        (OrganizationMember.Roles.MANAGER, all_permissions.organizations_members_change, all_permissions.organizations_change),
        (OrganizationMember.Roles.MANAGER, all_permissions.organizations_members_invite, all_permissions.organizations_invite),
        (OrganizationMember.Roles.MANAGER, all_permissions.teams_view, all_permissions.teams_create),
        (OrganizationMember.Roles.ANNOTATOR, all_permissions.projects_view, all_permissions.organizations_view),
        (OrganizationMember.Roles.ANNOTATOR, all_permissions.workspaces_view, all_permissions.workspaces_create),
        (OrganizationMember.Roles.VIEWER, all_permissions.projects_view, all_permissions.organizations_view),
        (OrganizationMember.Roles.VIEWER, all_permissions.workspaces_view, all_permissions.teams_view),
        (OrganizationMember.Roles.ANNOTATOR, all_permissions.annotations_change, all_permissions.projects_delete),
        (OrganizationMember.Roles.VIEWER, all_permissions.projects_view, all_permissions.annotations_change),
    ],
)
def test_role_permission_matrix(role, allowed, denied):
    org = OrganizationFactory()
    user = UserFactory(active_organization=org)
    OrganizationMember.objects.filter(user=user, organization=org).update(role=role)

    assert has_permission(user, allowed)
    if denied:
        assert not has_permission(user, denied)
