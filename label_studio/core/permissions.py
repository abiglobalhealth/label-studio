"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import logging  # noqa: I001
from typing import Optional

from pydantic import BaseModel, ConfigDict

import rules
from core.rbac import has_permission as has_rbac_permission

logger = logging.getLogger(__name__)


class AllPermissions(BaseModel):
    model_config = ConfigDict(protected_namespaces=('__.*__', '_.*'))

    organizations_create: str = 'organizations.create'
    organizations_view: str = 'organizations.view'
    organizations_change: str = 'organizations.change'
    organizations_delete: str = 'organizations.delete'
    organizations_invite: str = 'organizations.invite'
    organizations_members_change: str = 'organizations.members.change'
    organizations_members_invite: str = 'organizations.members.invite'
    organizations_members_role: str = 'organizations.members.role'
    projects_create: str = 'projects.create'
    projects_view: str = 'projects.view'
    projects_change: str = 'projects.change'
    projects_delete: str = 'projects.delete'
    projects_reset_cache: str = 'projects.reset_cache'
    tasks_create: str = 'tasks.create'
    tasks_view: str = 'tasks.view'
    tasks_change: str = 'tasks.change'
    tasks_delete: str = 'tasks.delete'
    views_reset: str = 'views.reset'
    annotations_create: str = 'annotations.create'
    annotations_view: str = 'annotations.view'
    annotations_change: str = 'annotations.change'
    annotations_delete: str = 'annotations.delete'
    actions_perform: str = 'actions.perform'
    predictions_any: str = 'predictions.any'
    avatar_any: str = 'avatar.any'
    labels_create: str = 'labels.create'
    labels_view: str = 'labels.view'
    labels_change: str = 'labels.change'
    labels_delete: str = 'labels.delete'
    models_create: str = 'models.create'
    models_view: str = 'models.view'
    models_change: str = 'models.change'
    models_delete: str = 'models.delete'
    model_provider_connection_create: str = 'model_provider_connection.create'
    model_provider_connection_view: str = 'model_provider_connection.view'
    model_provider_connection_change: str = 'model_provider_connection.change'
    model_provider_connection_delete: str = 'model_provider_connection.delete'
    webhooks_view: str = 'webhooks.view'
    webhooks_change: str = 'webhooks.change'
    users_token_any: str = 'users.token.any'

    storages_view: str = 'storages.view'
    storages_change: str = 'storages.change'
    storages_sync: str = 'storages.sync'

    views_view: str = 'views.view'
    views_create: str = 'views.create'
    views_change: str = 'views.change'
    views_delete: str = 'views.delete'

    workspaces_view: str = 'workspaces.view'
    workspaces_create: str = 'workspaces.create'
    workspaces_change: str = 'workspaces.change'
    workspaces_delete: str = 'workspaces.delete'
    teams_view: str = 'teams.view'
    teams_create: str = 'teams.create'
    teams_change: str = 'teams.change'
    teams_delete: str = 'teams.delete'
    topics_view: str = 'topics.view'
    topics_create: str = 'topics.create'
    topics_change: str = 'topics.change'
    topics_delete: str = 'topics.delete'


all_permissions = AllPermissions()


class ViewClassPermission(BaseModel):
    GET: Optional[str] = None
    PATCH: Optional[str] = None
    PUT: Optional[str] = None
    DELETE: Optional[str] = None
    POST: Optional[str] = None


def make_perm(name, pred, overwrite=False):
    if rules.perm_exists(name):
        if overwrite:
            rules.remove_perm(name)
        else:
            return
    rules.add_perm(name, pred)


def make_rbac_predicate(permission_name):
    @rules.predicate
    def _predicate(user, obj=None):
        organization = None
        if hasattr(obj, 'organization'):
            organization = obj.organization
        elif hasattr(obj, 'organization_id'):
            organization = getattr(user, 'active_organization', None)

        if not has_rbac_permission(user, permission_name, organization=organization):
            return False

        if obj is not None and hasattr(obj, 'has_permission'):
            return obj.has_permission(user)

        return True

    return _predicate


for _, permission_name in all_permissions:
    make_perm(permission_name, make_rbac_predicate(permission_name), overwrite=True)
