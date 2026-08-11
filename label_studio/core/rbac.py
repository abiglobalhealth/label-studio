"""RBAC helpers for organization-scoped permissions and visibility."""

from __future__ import annotations

from typing import Optional

from django.db.models import Q
from organizations.models import Organization, OrganizationMember
from rest_framework.permissions import SAFE_METHODS


def _organization_has_workspace_restrictions(organization: Optional[Organization]) -> bool:
    if organization is None:
        return False

    if organization.workspace_visibility == Organization.WorkspaceVisibility.OPEN:
        return False
    if organization.workspace_visibility == Organization.WorkspaceVisibility.RESTRICTED:
        return True

    return _organization_has_workspace_assignments(organization)


def _organization_has_workspace_assignments(organization: Optional[Organization]) -> bool:
    if organization is None:
        return False

    from workspaces.models import WorkspaceTeamAssignment, WorkspaceUserAssignment

    return WorkspaceUserAssignment.objects.filter(workspace__organization=organization).exists() or WorkspaceTeamAssignment.objects.filter(
        workspace__organization=organization
    ).exists()


def _assigned_workspace_ids(user, organization: Optional[Organization] = None):
    target_organization = organization or getattr(user, 'active_organization', None)
    if target_organization is None:
        return []

    cache_key = f'_assigned_workspace_ids_{target_organization.pk}'
    cached = getattr(user, cache_key, None)
    if cached is not None:
        return cached

    from workspaces.models import WorkspaceTeamAssignment, WorkspaceUserAssignment

    user_workspace_ids = WorkspaceUserAssignment.objects.filter(
        workspace__organization=target_organization,
        user=user,
    ).values_list('workspace_id', flat=True)
    team_workspace_ids = WorkspaceTeamAssignment.objects.filter(
        workspace__organization=target_organization,
        team__members__user=user,
    ).values_list('workspace_id', flat=True)

    ids = list(set(user_workspace_ids).union(set(team_workspace_ids)))
    try:
        setattr(user, cache_key, ids)
    except Exception:
        pass
    return ids


def _assigned_team_ids(user, organization: Optional[Organization] = None):
    target_organization = organization or getattr(user, 'active_organization', None)
    if target_organization is None:
        return []

    from workspaces.models import TeamManager

    return list(
        TeamManager.objects.filter(team__organization=target_organization, user=user)
        .values_list('team_id', flat=True)
        .distinct()
    )


def _manager_workspace_ids(user, organization: Optional[Organization] = None):
    target_organization = organization or getattr(user, 'active_organization', None)
    if target_organization is None:
        return []

    from workspaces.models import WorkspaceTeamAssignment

    return list(
        WorkspaceTeamAssignment.objects.filter(
            workspace__organization=target_organization,
            team__managers__user=user,
        )
        .values_list('workspace_id', flat=True)
        .distinct()
    )


def can_manage_member(user, member) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    role = get_user_role(user, organization=member.organization)
    if role in {OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN}:
        if member.role == OrganizationMember.Roles.OWNER and role != OrganizationMember.Roles.OWNER:
            return False
        return True
    if role != OrganizationMember.Roles.MANAGER:
        return False

    if member.role not in {OrganizationMember.Roles.ANNOTATOR, OrganizationMember.Roles.VIEWER}:
        return False

    return member.user_id in _managed_team_user_ids(user, member.organization)


def _managed_team_user_ids(user, organization: Optional[Organization] = None):
    target_organization = organization or getattr(user, 'active_organization', None)
    if target_organization is None:
        return []

    from workspaces.models import TeamManager

    return list(
        TeamManager.objects.filter(team__organization=target_organization, user=user)
        .values_list('team__members__user_id', flat=True)
        .distinct()
    )

ROLE_PERMISSION_MATRIX = {
    OrganizationMember.Roles.OWNER: {'*'},
    OrganizationMember.Roles.ADMIN: {'*'},
    OrganizationMember.Roles.MANAGER: {
        'organizations.view',
        'organizations.members.change',
        'organizations.members.invite',
        'organizations.members.role',
        'projects.create',
        'projects.view',
        'projects.change',
        'projects.delete',
        'tasks.create',
        'tasks.view',
        'tasks.change',
        'tasks.delete',
        'views.reset',
        'annotations.create',
        'annotations.view',
        'annotations.change',
        'annotations.delete',
        'actions.perform',
        'predictions.any',
        'avatar.any',
        'labels.create',
        'labels.view',
        'labels.change',
        'labels.delete',
        'models.create',
        'models.view',
        'models.change',
        'models.delete',
        'model_provider_connection.create',
        'model_provider_connection.view',
        'model_provider_connection.change',
        'model_provider_connection.delete',
        'webhooks.view',
        'webhooks.change',
        'storages.view',
        'storages.change',
        'storages.sync',
        'views.view',
        'views.create',
        'views.change',
        'views.delete',
        'users.token.any',
        'workspaces.view',
        'teams.view',
        'topics.view',
    },
    OrganizationMember.Roles.ANNOTATOR: {
        'projects.view',
        'tasks.view',
        'annotations.create',
        'annotations.view',
        'annotations.change',
        'annotations.delete',
        'workspaces.view',
        'topics.view',
    },
    OrganizationMember.Roles.VIEWER: {
        'projects.view',
        'tasks.view',
        'annotations.view',
        'workspaces.view',
        'topics.view',
    },
}


def get_active_membership(user, organization: Optional[Organization] = None) -> Optional[OrganizationMember]:
    if not getattr(user, 'is_authenticated', False):
        return None

    target_org = organization or getattr(user, 'active_organization', None)
    if target_org is None:
        return None

    return (
        OrganizationMember.objects.filter(user=user, organization=target_org, deleted_at__isnull=True)
        .only('id', 'role', 'organization_id', 'user_id')
        .first()
    )


def get_user_role(user, organization: Optional[Organization] = None) -> Optional[str]:
    membership = get_active_membership(user, organization=organization)
    return membership.role if membership else None


def has_permission(user, permission_name: str, organization: Optional[Organization] = None) -> bool:
    if not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True

    role = get_user_role(user, organization=organization)
    if role is None:
        return False

    allowed = ROLE_PERMISSION_MATRIX.get(role, set())
    return '*' in allowed or permission_name in allowed


def is_workspace_visible_for_user(user, workspace) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    role = get_user_role(user, organization=workspace.organization)
    if role in {OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN}:
        return True

    if role == OrganizationMember.Roles.MANAGER:
        return workspace.id in _manager_workspace_ids(user, organization=workspace.organization)

    return workspace.id in _assigned_workspace_ids(user, organization=workspace.organization)


def can_manage_workspace(user, workspace) -> bool:
    if getattr(user, 'is_superuser', False):
        return True

    role = get_user_role(user, organization=workspace.organization)
    if role in {OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN}:
        return True
    return role == OrganizationMember.Roles.MANAGER and workspace.id in _manager_workspace_ids(
        user, organization=workspace.organization
    )


def project_visibility_q(user):
    if getattr(user, 'is_superuser', False):
        return Q()

    role = get_user_role(user)
    if role in {OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN}:
        return Q()

    if role == OrganizationMember.Roles.MANAGER:
        return Q(workspace_id__in=_manager_workspace_ids(user, organization=getattr(user, 'active_organization', None))) | Q(
            members__user=user, members__enabled=True
        )

    return Q(workspace_id__in=_assigned_workspace_ids(user, organization=getattr(user, 'active_organization', None))) | Q(
        members__user=user, members__enabled=True
    )


def workspace_visibility_q(user):
    if getattr(user, 'is_superuser', False):
        return Q()

    role = get_user_role(user)
    if role in {OrganizationMember.Roles.OWNER, OrganizationMember.Roles.ADMIN}:
        return Q()
    if role == OrganizationMember.Roles.MANAGER:
        return Q(pk__in=_manager_workspace_ids(user, organization=getattr(user, 'active_organization', None)))
    return Q(pk__in=_assigned_workspace_ids(user, organization=getattr(user, 'active_organization', None)))


def can_mutate_project(user, project, request_method: str) -> bool:
    if request_method in SAFE_METHODS:
        return True
    if project.archived_at is not None:
        return False

    return can_manage_workspace(user, project.workspace)
