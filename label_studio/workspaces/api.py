from core.rbac import _manager_workspace_ids, has_permission, project_visibility_q, workspace_visibility_q
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Q
from organizations.models import OrganizationMember
from projects.models import Project
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from workspaces.models import (
    Team,
    TeamManager,
    TeamMember,
    Topic,
    Workspace,
    WorkspaceTeamAssignment,
    WorkspaceUserAssignment,
)
from workspaces.serializers import (
    TeamMemberSerializer,
    TeamManagerSerializer,
    TeamSerializer,
    TopicSerializer,
    WorkspaceSerializer,
    WorkspaceTeamAssignmentSerializer,
    WorkspaceUserAssignmentSerializer,
)


class RBACPermissionMixin:
    required_permission = None

    def _require(self):
        if self.required_permission and not has_permission(self.request.user, self.required_permission):
            self.permission_denied(self.request, message='Permission denied')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._require()


@extend_schema_view(
    get=extend_schema(tags=['Workspaces'], summary='List workspaces'),
    post=extend_schema(tags=['Workspaces'], summary='Create workspace'),
)
class WorkspaceListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def get_required_permission(self):
        return 'workspaces.create' if self.request.method == 'POST' else 'workspaces.view'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Workspace.objects.filter(organization=self.request.user.active_organization)
        if has_permission(self.request.user, 'workspaces.change'):
            return queryset
        return queryset.filter(workspace_visibility_q(self.request.user)).distinct()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.active_organization, created_by=self.request.user)


@extend_schema_view(
    get=extend_schema(tags=['Workspaces'], summary='Get workspace'),
    put=extend_schema(tags=['Workspaces'], summary='Update workspace'),
    patch=extend_schema(tags=['Workspaces'], summary='Partially update workspace'),
    delete=extend_schema(tags=['Workspaces'], summary='Delete workspace'),
)
class WorkspaceDetailAPI(RBACPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceSerializer

    def get_required_permission(self):
        if self.request.method == 'GET':
            return 'workspaces.view'
        if self.request.method == 'DELETE':
            return 'workspaces.delete'
        return 'workspaces.change'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Workspace.objects.filter(organization=self.request.user.active_organization)
        if has_permission(self.request.user, 'workspaces.change'):
            return queryset
        return queryset.filter(workspace_visibility_q(self.request.user)).distinct()

    def perform_destroy(self, instance):
        if Project.all_objects.filter(workspace_id=instance.id).exists():
            raise ValidationError(
                {'detail': 'Cannot delete a workspace that still has projects. Move or delete its projects first.'}
            )
        instance.delete()


@extend_schema_view(
    get=extend_schema(tags=['Teams'], summary='List teams'),
    post=extend_schema(tags=['Teams'], summary='Create team'),
)
class TeamListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamSerializer

    def get_required_permission(self):
        return 'teams.create' if self.request.method == 'POST' else 'teams.view'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Team.objects.filter(organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'teams.change'):
            queryset = queryset.filter(Q(members__user=self.request.user) | Q(managers__user=self.request.user))
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.active_organization)


@extend_schema_view(
    get=extend_schema(tags=['Teams'], summary='Get team'),
    put=extend_schema(tags=['Teams'], summary='Update team'),
    patch=extend_schema(tags=['Teams'], summary='Partially update team'),
    delete=extend_schema(tags=['Teams'], summary='Delete team'),
)
class TeamDetailAPI(RBACPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamSerializer

    def get_required_permission(self):
        if self.request.method == 'GET':
            return 'teams.view'
        if self.request.method == 'DELETE':
            return 'teams.delete'
        return 'teams.change'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Team.objects.filter(organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'teams.change'):
            queryset = queryset.filter(Q(members__user=self.request.user) | Q(managers__user=self.request.user))
        return queryset.distinct()


@extend_schema_view(
    get=extend_schema(tags=['Teams'], summary='List team members'),
    post=extend_schema(tags=['Teams'], summary='Add team member'),
)
class TeamMemberListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer
    required_permission = 'teams.change'

    def get_queryset(self):
        queryset = TeamMember.objects.filter(team__organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'teams.change'):
            queryset = queryset.filter(
                Q(team__members__user=self.request.user) | Q(team__managers__user=self.request.user)
            )
        return queryset.distinct()

    def perform_create(self, serializer):
        team = serializer.validated_data['team']
        user = serializer.validated_data['user']
        if team.organization_id != self.request.user.active_organization_id:
            raise ValidationError('Team does not belong to the active organization.')
        if not OrganizationMember.objects.filter(
            organization=team.organization, user=user, deleted_at__isnull=True
        ).exists():
            raise ValidationError('User does not belong to the team organization.')
        serializer.save()


@extend_schema_view(
    delete=extend_schema(tags=['Teams'], summary='Remove team member'),
)
class TeamMemberDetailAPI(RBACPermissionMixin, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamMemberSerializer
    required_permission = 'teams.change'

    def get_queryset(self):
        queryset = TeamMember.objects.filter(team__organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'teams.change'):
            queryset = queryset.filter(
                Q(team__members__user=self.request.user) | Q(team__managers__user=self.request.user)
            )
        return queryset.distinct()


@extend_schema_view(
    get=extend_schema(tags=['Teams'], summary='List team managers'),
    post=extend_schema(tags=['Teams'], summary='Assign team manager'),
)
class TeamManagerListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamManagerSerializer
    required_permission = 'teams.change'

    def get_queryset(self):
        return TeamManager.objects.filter(team__organization=self.request.user.active_organization).select_related('team', 'user')

    def perform_create(self, serializer):
        team = serializer.validated_data['team']
        user = serializer.validated_data['user']
        if team.organization_id != self.request.user.active_organization_id:
            raise ValidationError('Team does not belong to the active organization.')
        membership = OrganizationMember.objects.filter(
            organization=team.organization,
            user=user,
            deleted_at__isnull=True,
        ).first()
        if membership is None or membership.role not in {
            OrganizationMember.Roles.OWNER,
            OrganizationMember.Roles.ADMIN,
            OrganizationMember.Roles.MANAGER,
        }:
            raise ValidationError('Only organization Owners, Admins, and Managers can be assigned to a team.')
        serializer.save()


@extend_schema_view(
    delete=extend_schema(tags=['Teams'], summary='Remove team manager'),
)
class TeamManagerDetailAPI(RBACPermissionMixin, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TeamManagerSerializer
    required_permission = 'teams.change'

    def get_queryset(self):
        return TeamManager.objects.filter(team__organization=self.request.user.active_organization)


@extend_schema_view(
    get=extend_schema(tags=['Topics'], summary='List topics'),
    post=extend_schema(tags=['Topics'], summary='Create topic'),
)
class TopicListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def get_required_permission(self):
        return 'topics.create' if self.request.method == 'POST' else 'topics.view'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Topic.objects.filter(organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'topics.change'):
            visible_projects = Project.objects.filter(organization=self.request.user.active_organization).filter(
                project_visibility_q(self.request.user)
            )
            queryset = queryset.filter(projects__in=visible_projects)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.active_organization)


@extend_schema_view(
    get=extend_schema(tags=['Topics'], summary='Get topic'),
    put=extend_schema(tags=['Topics'], summary='Update topic'),
    patch=extend_schema(tags=['Topics'], summary='Partially update topic'),
    delete=extend_schema(tags=['Topics'], summary='Delete topic'),
)
class TopicDetailAPI(RBACPermissionMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializer

    def get_required_permission(self):
        if self.request.method == 'GET':
            return 'topics.view'
        if self.request.method == 'DELETE':
            return 'topics.delete'
        return 'topics.change'

    def _require(self):
        if not has_permission(self.request.user, self.get_required_permission()):
            self.permission_denied(self.request, message='Permission denied')

    def get_queryset(self):
        queryset = Topic.objects.filter(organization=self.request.user.active_organization)
        if not has_permission(self.request.user, 'topics.change'):
            visible_projects = Project.objects.filter(organization=self.request.user.active_organization).filter(
                project_visibility_q(self.request.user)
            )
            queryset = queryset.filter(projects__in=visible_projects)
        return queryset.distinct()


@extend_schema_view(
    get=extend_schema(tags=['Workspaces'], summary='List user assignments'),
    post=extend_schema(tags=['Workspaces'], summary='Assign user to workspace'),
)
class WorkspaceUserAssignmentListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceUserAssignmentSerializer
    required_permission = 'workspaces.change'

    def get_queryset(self):
        return WorkspaceUserAssignment.objects.filter(workspace__organization=self.request.user.active_organization)

    def perform_create(self, serializer):
        workspace = serializer.validated_data['workspace']
        user = serializer.validated_data['user']
        if workspace.organization_id != self.request.user.active_organization_id:
            raise ValidationError('Workspace does not belong to the active organization.')
        if not OrganizationMember.objects.filter(
            organization=workspace.organization, user=user, deleted_at__isnull=True
        ).exists():
            raise ValidationError('User does not belong to the workspace organization.')
        serializer.save()


@extend_schema_view(
    delete=extend_schema(tags=['Workspaces'], summary='Remove user from workspace'),
)
class WorkspaceUserAssignmentDetailAPI(RBACPermissionMixin, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceUserAssignmentSerializer
    required_permission = 'workspaces.change'

    def get_queryset(self):
        return WorkspaceUserAssignment.objects.filter(workspace__organization=self.request.user.active_organization)


@extend_schema_view(
    get=extend_schema(tags=['Workspaces'], summary='List team assignments'),
    post=extend_schema(tags=['Workspaces'], summary='Assign team to workspace'),
)
class WorkspaceTeamAssignmentListCreateAPI(RBACPermissionMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceTeamAssignmentSerializer
    required_permission = 'workspaces.change'

    def get_queryset(self):
        return WorkspaceTeamAssignment.objects.filter(workspace__organization=self.request.user.active_organization)

    def perform_create(self, serializer):
        workspace = serializer.validated_data['workspace']
        team = serializer.validated_data['team']
        if workspace.organization_id != self.request.user.active_organization_id:
            raise ValidationError('Workspace does not belong to the active organization.')
        if team.organization_id != workspace.organization_id:
            raise ValidationError('Team does not belong to the workspace organization.')
        serializer.save()


@extend_schema_view(
    delete=extend_schema(tags=['Workspaces'], summary='Remove team from workspace'),
)
class WorkspaceTeamAssignmentDetailAPI(RBACPermissionMixin, generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WorkspaceTeamAssignmentSerializer
    required_permission = 'workspaces.change'

    def get_queryset(self):
        return WorkspaceTeamAssignment.objects.filter(workspace__organization=self.request.user.active_organization)
