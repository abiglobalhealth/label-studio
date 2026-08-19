"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import json

import pytest
from organizations.models import OrganizationMember
from users.models import User
from workspaces.models import Workspace, WorkspaceUserAssignment


@pytest.mark.django_db
def test_signup_setting(business_client, client, settings):
    settings.DISABLE_SIGNUP_WITHOUT_LINK = True
    response = client.post('/user/signup', data={'email': 'test_user@example.com', 'password': 'test_password'})
    assert response.status_code == 403

    response = business_client.get('/api/invite')

    invite_url = response.json()['invite_url']

    response = client.post(invite_url, data={'email': 'test_user@example.com', 'password': 'test_password'})
    assert response.status_code == 302

    client.logout()
    response = client.post(invite_url, data={'email': 'second_user@example.com', 'password': 'test_password'})
    assert response.status_code == 403


@pytest.mark.django_db
def test_signup_requires_invite_token_even_when_setting_allows_it(business_client, client, settings):
    settings.DISABLE_SIGNUP_WITHOUT_LINK = False

    response = client.post('/user/signup', data={'email': 'test_user@example.com', 'password': 'test_password'})

    assert response.status_code == 403


@pytest.mark.django_db
def test_reset_token(business_client, client, settings):
    settings.DISABLE_SIGNUP_WITHOUT_LINK = True

    # get invite_url link and check it works
    response = business_client.get('/api/invite')
    invite_url = response.json()['invite_url']
    response = client.post(invite_url, data={'email': 'test_user@example.com', 'password': 'test_password'})
    assert response.status_code == 302

    response = business_client.post('/api/invite/reset-token')
    new_invite_url = response.json()['invite_url']

    # after reset old link returns permission denied
    client.logout()
    response = client.post(invite_url, data={'email': 'test_user1@example.com', 'password': 'test_password'})
    assert response.status_code == 403, response.content

    # but new one works fine
    response = client.post(new_invite_url, data={'email': 'test_user2@example.com', 'password': 'test_password'})
    assert response.status_code == 302


@pytest.mark.django_db
def test_reset_token_not_valid(business_client, client, settings):
    settings.DISABLE_SIGNUP_WITHOUT_LINK = False

    # disallow if token and does not match
    response = client.post(
        '/user/signup/?token=54321abce', data={'email': 'test_user1@example.com', 'password': 'test_password'}
    )
    assert response.status_code == 403, response.content


@pytest.mark.django_db
def test_token_get_not_post_shows_form(business_client, client, settings):
    settings.DISABLE_SIGNUP_WITHOUT_LINK = True

    # can't bypass post
    response = business_client.get('/api/invite')
    invite_url = response.json()['invite_url']
    response = client.get(f'{invite_url}&email=test_user@example.com&password=test_password')
    assert response.status_code == 200, response.content
    assert str(response.content).find('Create Account') != -1


@pytest.mark.django_db
def test_scoped_invite_applies_role_and_workspace(business_client, client):
    workspace = Workspace.objects.create(
        organization=business_client.organization,
        title='Restricted workspace',
        created_by=business_client.user,
    )

    response = business_client.post(
        '/api/invite/links',
        data=json.dumps(
            {
                'default_role': OrganizationMember.Roles.ADMIN,
                'workspace_ids': [workspace.id],
            }
        ),
        content_type='application/json',
    )

    assert response.status_code == 201, response.content
    invite_url = response.json()['invite_url']

    response = client.post(
        invite_url,
        data={'email': 'scoped-admin@example.com', 'password': 'test_password'},
    )

    assert response.status_code == 302, response.content
    invited_user = User.objects.get(email='scoped-admin@example.com')
    membership = OrganizationMember.objects.get(
        user=invited_user,
        organization=business_client.organization,
        deleted_at__isnull=True,
    )

    assert membership.role == OrganizationMember.Roles.ADMIN
    assert WorkspaceUserAssignment.objects.filter(workspace=workspace, user=invited_user).exists()

    client.logout()
    response = client.post(
        invite_url,
        data={'email': 'second-scoped-admin@example.com', 'password': 'test_password'},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_scoped_invite_cannot_assign_owner(business_client):
    response = business_client.post(
        '/api/invite/links',
        data=json.dumps({'default_role': OrganizationMember.Roles.OWNER}),
        content_type='application/json',
    )

    assert response.status_code == 400
