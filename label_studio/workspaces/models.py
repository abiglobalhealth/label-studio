from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Topic(models.Model):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(_('title'), max_length=255)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization', 'title'], name='uq_topic_org_title')]


class Team(models.Model):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='teams')
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True, null=True, default='')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization', 'title'], name='uq_team_org_title')]


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['team', 'user'], name='uq_team_member')]


class TeamManager(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='managers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='managed_teams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['team', 'user'], name='uq_team_manager')]
        indexes = [models.Index(fields=['user', 'team'], name='team_manager_user_team_idx')]


class Workspace(models.Model):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='workspaces')
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True, null=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_workspaces',
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization', 'title'], name='uq_workspace_org_title')]


class WorkspaceUserAssignment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='user_assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workspace_assignments')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'user'], name='uq_workspace_user_assignment')]


class WorkspaceTeamAssignment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='team_assignments')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='workspace_assignments')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'team'], name='uq_workspace_team_assignment')]


class WorkspaceTopicAssignment(models.Model):
    """Legacy relation retained for migration compatibility; topics are not access scopes."""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='topic_assignments')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='workspace_assignments')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['workspace', 'topic'], name='uq_workspace_topic_assignment')]
