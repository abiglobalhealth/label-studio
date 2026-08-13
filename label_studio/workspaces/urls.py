from django.urls import path

from workspaces import api

app_name = 'workspaces'

urlpatterns = [
    path('api/workspaces', api.WorkspaceListCreateAPI.as_view(), name='workspace-list'),
    path('api/workspaces/<int:pk>', api.WorkspaceDetailAPI.as_view(), name='workspace-detail'),
    path('api/teams', api.TeamListCreateAPI.as_view(), name='team-list'),
    path('api/teams/<int:pk>', api.TeamDetailAPI.as_view(), name='team-detail'),
    path('api/teams/members', api.TeamMemberListCreateAPI.as_view(), name='team-member-list'),
    path('api/teams/members/<int:pk>', api.TeamMemberDetailAPI.as_view(), name='team-member-detail'),
    path('api/teams/managers', api.TeamManagerListCreateAPI.as_view(), name='team-manager-list'),
    path('api/teams/managers/<int:pk>', api.TeamManagerDetailAPI.as_view(), name='team-manager-detail'),
    path('api/topics', api.TopicListCreateAPI.as_view(), name='topic-list'),
    path('api/topics/<int:pk>', api.TopicDetailAPI.as_view(), name='topic-detail'),
    path('api/workspaces/users', api.WorkspaceUserAssignmentListCreateAPI.as_view(), name='workspace-user-assignment-list'),
    path('api/workspaces/users/<int:pk>', api.WorkspaceUserAssignmentDetailAPI.as_view(), name='workspace-user-assignment-detail'),
    path('api/workspaces/teams', api.WorkspaceTeamAssignmentListCreateAPI.as_view(), name='workspace-team-assignment-list'),
    path('api/workspaces/teams/<int:pk>', api.WorkspaceTeamAssignmentDetailAPI.as_view(), name='workspace-team-assignment-detail'),
]
