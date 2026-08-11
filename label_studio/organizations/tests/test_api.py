from urllib.parse import urlencode

from organizations.models import OrganizationMember
from organizations.tests.factories import OrganizationFactory
from projects.tests.factories import ProjectFactory
from rest_framework.test import APITestCase
from tasks.tests.factories import AnnotationFactory
from users.tests.factories import UserFactory
from workspaces.models import Team, TeamManager, TeamMember


class TestOrganizationMemberListAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory(created_by__username='owner')
        cls.owner = cls.organization.created_by
        cls.user_1 = UserFactory(username='user_1', active_organization=cls.organization)
        cls.user_2 = UserFactory(username='user_2', active_organization=cls.organization)

    def get_url(self, params=None):
        params = params or {}
        return f'/api/organizations/{self.organization.id}/memberships?{urlencode(params)}'

    def test_list_organization_members(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.get_url())
        assert response.status_code == 200
        assert len(response.json()['results']) == 3

        owner = response.json()['results'][0]
        assert owner['user']['id'] == self.owner.id
        assert owner['user']['created_projects'] is None
        assert owner['user']['contributed_to_projects'] is None
        assert owner['contributed_to_projects'] is None

        user_1 = response.json()['results'][1]
        assert user_1['user']['id'] == self.user_1.id
        assert user_1['user']['created_projects'] is None
        assert user_1['user']['contributed_to_projects'] is None
        assert user_1['contributed_to_projects'] is None

        user_2 = response.json()['results'][2]
        assert user_2['user']['id'] == self.user_2.id
        assert user_2['user']['created_projects'] is None
        assert user_2['user']['contributed_to_projects'] is None
        assert user_2['contributed_to_projects'] is None

    def test_list_with_contributed_to_projects(self):
        project_1 = ProjectFactory(created_by=self.user_1, organization=self.organization)
        project_2 = ProjectFactory(created_by=self.user_2, organization=self.organization)

        AnnotationFactory(task__project=project_1, completed_by=self.user_1)
        AnnotationFactory(task__project=project_2, completed_by=self.user_2)
        AnnotationFactory(task__project=project_2, completed_by=self.owner)

        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.get_url(params={'contributed_to_projects': 1}))
        assert response.status_code == 200
        assert len(response.json()['results']) == 3

        owner = response.json()['results'][0]
        assert owner['user']['created_projects'] == []
        assert owner['created_projects'] == []
        assert owner['user']['contributed_to_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
        ]
        assert owner['contributed_to_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
        ]

        user_1 = response.json()['results'][1]
        assert user_1['user']['contributed_to_projects'] == [
            {
                'id': project_1.id,
                'title': project_1.title,
            }
        ]
        assert user_1['contributed_to_projects'] == [
            {
                'id': project_1.id,
                'title': project_1.title,
            }
        ]
        assert user_1['user']['created_projects'] == [
            {
                'id': project_1.id,
                'title': project_1.title,
            }
        ]
        assert user_1['created_projects'] == [
            {
                'id': project_1.id,
                'title': project_1.title,
            }
        ]

        user_2 = response.json()['results'][2]
        assert user_2['user']['contributed_to_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
        ]
        assert user_2['contributed_to_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
        ]
        assert user_2['user']['created_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
        ]
        assert user_2['created_projects'] == [
            {
                'id': project_2.id,
                'title': project_2.title,
            }
            ]

    def test_manager_lists_all_members_of_assigned_teams_only(self):
        manager = UserFactory(username='manager', active_organization=self.organization)
        OrganizationMember.objects.filter(user=manager, organization=self.organization).update(
            role=OrganizationMember.Roles.MANAGER
        )
        team = Team.objects.create(organization=self.organization, title='Managed team')
        TeamManager.objects.create(team=team, user=manager)
        TeamMember.objects.create(team=team, user=self.user_1)

        self.client.force_authenticate(user=manager)
        response = self.client.get(self.get_url())

        assert response.status_code == 200
        assert {item['user']['id'] for item in response.json()['results']} == {manager.id, self.user_1.id}


class TestOrganizationMemberRoleUpdateAPI(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory(created_by__username='owner')
        cls.owner = cls.organization.created_by
        cls.admin = UserFactory(username='admin', active_organization=cls.organization)
        OrganizationMember.objects.filter(user=cls.admin, organization=cls.organization).update(
            role=OrganizationMember.Roles.ADMIN
        )
        cls.annotator = UserFactory(username='annotator', active_organization=cls.organization)
        OrganizationMember.objects.filter(user=cls.annotator, organization=cls.organization).update(
            role=OrganizationMember.Roles.ANNOTATOR
        )

    def get_url(self, user):
        return f'/api/organizations/{self.organization.id}/memberships/{user.id}/role'

    def get_role(self, user):
        return OrganizationMember.objects.get(user=user, organization=self.organization).role

    def test_owner_can_change_member_role(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.get_url(self.annotator), {'role': OrganizationMember.Roles.VIEWER}, format='json'
        )
        assert response.status_code == 200
        assert self.get_role(self.annotator) == OrganizationMember.Roles.VIEWER

    def test_admin_can_change_member_role(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            self.get_url(self.annotator), {'role': OrganizationMember.Roles.VIEWER}, format='json'
        )
        assert response.status_code == 200
        assert self.get_role(self.annotator) == OrganizationMember.Roles.VIEWER

    def test_owner_cannot_change_owner_role(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.get_url(self.owner), {'role': OrganizationMember.Roles.VIEWER}, format='json'
        )
        assert response.status_code == 403

    def test_manager_can_only_assign_annotator_or_viewer_within_team(self):
        manager = UserFactory(username='role_manager', active_organization=self.organization)
        OrganizationMember.objects.filter(user=manager, organization=self.organization).update(
            role=OrganizationMember.Roles.MANAGER
        )
        team = Team.objects.create(organization=self.organization, title='Role team')
        TeamManager.objects.create(team=team, user=manager)
        TeamMember.objects.create(team=team, user=self.annotator)

        self.client.force_authenticate(user=manager)
        response = self.client.patch(
            self.get_url(self.annotator), {'role': OrganizationMember.Roles.VIEWER}, format='json'
        )
        assert response.status_code == 200
        assert self.get_role(self.annotator) == OrganizationMember.Roles.VIEWER

        response = self.client.patch(
            self.get_url(self.annotator), {'role': OrganizationMember.Roles.ADMIN}, format='json'
        )
        assert response.status_code == 403
