"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import os
import uuid
from time import time

from core.utils.common import load_func
from django import forms
from django.conf import settings
from django.contrib import auth
from django.core.files.images import get_image_dimensions
from django.shortcuts import redirect
from django.urls import reverse
from organizations.models import Organization
from organizations.models import OrganizationMember


def hash_upload(instance, filename):
    filename = str(uuid.uuid4())[0:8] + '-' + filename
    return settings.AVATAR_PATH + '/' + filename


def check_avatar(files):
    images = list(files.items())
    if not images:
        return None

    _, avatar = list(files.items())[0]  # get first file
    w, h = get_image_dimensions(avatar)
    if not w or not h:
        raise forms.ValidationError("Can't read image, try another one")

    # validate dimensions
    max_width = max_height = 1200
    if w > max_width or h > max_height:
        raise forms.ValidationError('Please use an image that is %s x %s pixels or smaller.' % (max_width, max_height))

    valid_extensions = ['jpeg', 'jpg', 'gif', 'png']

    filename = avatar.name
    # check file extension
    ext = os.path.splitext(filename)[1].lstrip('.').lower()
    if ext not in valid_extensions:
        raise forms.ValidationError('Please upload a valid image file with extensions: JPEG, JPG, GIF, or PNG.')

    # validate content type
    main, sub = avatar.content_type.split('/')
    if not (main == 'image' and sub.lower() in valid_extensions):
        raise forms.ValidationError('Please use a JPEG, GIF or PNG image.')

    # validate file size
    max_size = 1024 * 1024
    if len(avatar) > max_size:
        raise forms.ValidationError('Avatar file size may not exceed ' + str(max_size / 1024) + ' kb')

    return avatar


def save_user(request, next_page, user_form):
    """Save user instance to DB"""
    user = user_form.save()
    user.username = user.email.split('@')[0]
    user.save()

    invite_organization = getattr(request, 'invite_organization', None)
    invite_preset = getattr(request, 'invite_preset', None)

    if invite_organization is not None:
        org = invite_organization
        org.add_user(user)
    elif Organization.objects.exists():
        org = Organization.objects.first()
        org.add_user(user)
    else:
        org = Organization.create_organization(created_by=user, title='Label Studio')

    membership = OrganizationMember.objects.filter(
        user=user,
        organization=org,
        deleted_at__isnull=True,
    ).first()

    if membership is not None and invite_preset is not None:
        membership.role = invite_preset.default_role
        membership.save(update_fields=['role'])

        from workspaces.models import TeamMember, WorkspaceUserAssignment

        if invite_preset.team_ids:
            valid_team_ids = set(org.teams.filter(id__in=invite_preset.team_ids).values_list('id', flat=True))
            for team_id in valid_team_ids:
                TeamMember.objects.get_or_create(team_id=team_id, user=user)

        if invite_preset.workspace_ids:
            valid_workspace_ids = set(org.workspaces.filter(id__in=invite_preset.workspace_ids).values_list('id', flat=True))
            for workspace_id in valid_workspace_ids:
                WorkspaceUserAssignment.objects.get_or_create(workspace_id=workspace_id, user=user)

        invite_preset.consume()

    user.active_organization = org
    user.save(update_fields=['active_organization'])

    request.advanced_json = {
        'email': user.email,
        'allow_newsletters': user.allow_newsletters,
        'update-notifications': 1,
        'new-user': 1,
        'how_find_us': user_form.cleaned_data.get('how_find_us', ''),
    }
    if user_form.cleaned_data.get('how_find_us', '') == 'Other':
        request.advanced_json['elaborate'] = user_form.cleaned_data.get('elaborate', '')

    redirect_url = next_page if next_page else reverse('projects:project-index')
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect(redirect_url)


def proceed_registration(request, user_form, organization_form, next_page):
    """Register a new user for POST user_signup"""
    # save user to db
    save_user = load_func(settings.SAVE_USER)
    response = save_user(request, next_page, user_form)

    return response


def login(request, *args, **kwargs):
    request.session['last_login'] = time()
    return auth.login(request, *args, **kwargs)
