"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license."""

import logging

from core.utils.common import create_hash, load_func
from django.conf import settings
from django.db import models, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

OrganizationMemberMixin = load_func(settings.ORGANIZATION_MEMBER_MIXIN)


class OrganizationMember(OrganizationMemberMixin, models.Model):
    class Roles(models.TextChoices):
        OWNER = 'OWNER', 'Owner'
        ADMIN = 'ADMIN', 'Admin'
        MANAGER = 'MANAGER', 'Manager'
        ANNOTATOR = 'ANNOTATOR', 'Annotator'
        VIEWER = 'VIEWER', 'Viewer'

    """ """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='om_through', help_text='User ID'
    )
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, help_text='Organization ID'
    )

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    deleted_at = models.DateTimeField(
        _('deleted at'),
        default=None,
        null=True,
        blank=True,
        db_index=True,
        help_text='Timestamp indicating when the organization member was marked as deleted.  '
        'If NULL, the member is not considered deleted.',
    )

    role = models.CharField(
        _('role'),
        max_length=32,
        choices=Roles.choices,
        default=Roles.ANNOTATOR,
        help_text='Organization membership role used for RBAC checks.',
        db_index=True,
    )

    # objects = OrganizationMemberQuerySet.as_manager()

    @classmethod
    def find_by_user(cls, user_or_user_pk, organization_pk):
        from users.models import User

        user_pk = user_or_user_pk.pk if isinstance(user_or_user_pk, User) else user_or_user_pk
        return OrganizationMember.objects.get(user=user_pk, organization=organization_pk)

    @cached_property
    def is_deleted(self):
        return bool(self.deleted_at)

    @cached_property
    def is_owner(self):
        return self.role == OrganizationMember.Roles.OWNER

    class Meta:
        ordering = ['pk']

    def soft_delete(self):
        with transaction.atomic():
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])
            self.user.active_organization = self.user.organizations.filter(
                organizationmember__deleted_at__isnull=True
            ).first()
            if self.user.avatar:
                self.user.avatar.delete(save=False)
                self.user.avatar = None
            self.user.save(update_fields=['active_organization', 'avatar'])

        self.user.task_locks.all().delete()


OrganizationMixin = load_func(settings.ORGANIZATION_MIXIN)


class Organization(OrganizationMixin, models.Model):
    class WorkspaceVisibility(models.TextChoices):
        AUTO = 'auto', 'Auto'
        OPEN = 'open', 'Open'
        RESTRICTED = 'restricted', 'Restricted'

    """ """

    title = models.CharField(_('organization title'), max_length=1000, null=False)

    token = models.CharField(_('token'), max_length=256, default=create_hash, unique=True, null=True, blank=True)

    workspace_visibility = models.CharField(
        _('workspace visibility'),
        max_length=16,
        choices=WorkspaceVisibility.choices,
        default=WorkspaceVisibility.AUTO,
        help_text='Controls how workspace visibility restrictions are applied: '
        "'auto' enables restrictions once any workspace assignment exists, "
        "'open' keeps all workspaces visible to all members, "
        "'restricted' only shows assigned workspaces.",
    )

    users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='organizations', through=OrganizationMember)

    created_by = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='organization',
        verbose_name=_('created_by'),
    )

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    contact_info = models.EmailField(_('contact info'), blank=True, null=True)

    def __str__(self):
        return self.title + ', id=' + str(self.pk)

    @classmethod
    def create_organization(cls, created_by=None, title='Your Organization', **kwargs):
        _create_organization = load_func(settings.CREATE_ORGANIZATION)
        return _create_organization(title=title, created_by=created_by, **kwargs)

    @classmethod
    def find_by_user(cls, user, check_deleted=False):
        memberships = (
            OrganizationMember.objects.filter(user=user, deleted_at__isnull=True)
            .prefetch_related('organization')
            .order_by('-created_at', '-pk')
        )
        if not memberships.exists():
            raise ValueError(f'No memberships found for user {user}')
        membership = memberships.first()
        if check_deleted:
            return membership.organization, False

        return membership.organization

    @classmethod
    def find_by_invite_url(cls, url):
        token = url.strip('/').split('/')[-1]
        if len(token):
            return Organization.objects.get(token=token)
        else:
            raise KeyError(f"Can't find Organization by welcome URL: {url}")

    def has_user(self, user):
        return self.users.filter(pk=user.pk).exists()

    def has_deleted(self, user):
        return OrganizationMember.objects.filter(user=user, organization=self, deleted_at__isnull=False).exists()

    def has_project_member(self, user):
        return self.projects.filter(members__user=user).exists()

    def has_permission(self, user):
        return OrganizationMember.objects.filter(user=user, organization=self, deleted_at__isnull=True).exists()

    def add_user(self, user):
        if self.users.filter(pk=user.pk).exists():
            logger.debug('User already exists in organization.')
            return

        with transaction.atomic():
            om = OrganizationMember(user=user, organization=self, role=OrganizationMember.Roles.ANNOTATOR)
            om.save()

            return om

    def remove_user(self, user):
        OrganizationMember.objects.filter(user=user, organization=self).delete()
        if user.active_organization_id == self.id:
            user.active_organization = user.organizations.filter(organizationmember__deleted_at__isnull=True).first()
            user.save(update_fields=['active_organization'])

    def reset_token(self):
        self.token = create_hash()
        self.save(update_fields=['token'])

    @classmethod
    def resolve_invite_token(cls, token: str):
        """Resolve invite token to organization and optional preset.

        Returns tuple: (organization | None, invite_preset | None)
        """
        if not token:
            return None, None

        preset = (
            InvitePreset.objects.select_related('organization')
            .filter(token=token)
            .first()
        )
        if preset:
            if preset.is_available_for_use():
                return preset.organization, preset
            return None, None

        organization = Organization.objects.filter(token=token).first()
        return organization, None

    def check_max_projects(self):
        """This check raise an exception if the projects limit is hit"""
        pass

    def projects_sorted_by_created_at(self):
        return (
            self.projects.all()
            .order_by('-created_at')
            .annotate(tasks_count=Count('tasks'), labeled_tasks_count=Count('tasks', filter=Q(tasks__is_labeled=True)))
            .prefetch_related('created_by')
        )

    def created_at_prettify(self):
        return self.created_at.strftime('%d %b %Y %H:%M:%S')

    def per_project_invited_users(self):
        from users.models import User

        invited_ids = self.projects.values_list('members__user__pk', flat=True).distinct()
        per_project_invited_users = User.objects.filter(pk__in=invited_ids)
        return per_project_invited_users

    def should_verify_ssl_certs(self) -> bool:
        if hasattr(self, 'billing') and (org_verify := self.billing.verify_ssl_certs()) is not None:
            return org_verify
        return settings.VERIFY_SSL_CERTS

    @cached_property
    def secure_mode(self):
        return False

    @cached_property
    def members(self):
        return OrganizationMember.objects.filter(organization=self)

    class Meta:
        db_table = 'organization'


class InvitePreset(models.Model):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='invite_presets')
    token = models.CharField(_('token'), max_length=256, default=create_hash, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invite_presets',
    )
    default_role = models.CharField(
        _('default role'),
        max_length=32,
        choices=OrganizationMember.Roles.choices,
        default=OrganizationMember.Roles.ANNOTATOR,
    )
    team_ids = models.JSONField(default=list, blank=True)
    workspace_ids = models.JSONField(default=list, blank=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    max_uses = models.PositiveIntegerField(_('max uses'), null=True, blank=True)
    uses_count = models.PositiveIntegerField(_('uses count'), default=0)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def is_available_for_use(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= now:
            return False
        # Invite links are intentionally single-use. Keep max_uses on the
        # model for compatibility with existing data and API responses, but
        # never allow it to expand the lifetime of a token.
        if self.uses_count >= 1:
            return False
        return True

    def consume(self):
        updated = InvitePreset.objects.filter(
            pk=self.pk,
            is_active=True,
            uses_count=0,
        ).update(uses_count=1, is_active=False)
        if updated:
            self.uses_count = 1
            self.is_active = False
        return bool(updated)
