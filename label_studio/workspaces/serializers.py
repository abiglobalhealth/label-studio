from rest_framework import serializers

from workspaces.models import Team, TeamManager, TeamMember, Topic, Workspace, WorkspaceTeamAssignment, WorkspaceUserAssignment


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'organization', 'title', 'created_at', 'updated_at']
        read_only_fields = ['organization', 'created_at', 'updated_at']


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = ['id', 'team', 'user', 'created_at']
        read_only_fields = ['created_at']


class TeamManagerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamManager
        fields = ['id', 'team', 'user', 'created_at']
        read_only_fields = ['created_at']


class TeamSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'organization', 'title', 'description', 'members_count', 'created_at', 'updated_at']
        read_only_fields = ['organization', 'created_at', 'updated_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    user_assignments = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='user_assignments.all')
    team_assignments = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='team_assignments.all')

    class Meta:
        model = Workspace
        fields = [
            'id',
            'organization',
            'title',
            'description',
            'created_by',
            'created_at',
            'updated_at',
            'user_assignments',
            'team_assignments',
        ]
        read_only_fields = ['organization', 'created_by', 'created_at', 'updated_at']


class WorkspaceUserAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceUserAssignment
        fields = ['id', 'workspace', 'user', 'created_at']
        read_only_fields = ['created_at']


class WorkspaceTeamAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceTeamAssignment
        fields = ['id', 'workspace', 'team', 'created_at']
        read_only_fields = ['created_at']
