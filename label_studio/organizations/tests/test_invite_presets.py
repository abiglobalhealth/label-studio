import pytest

from organizations.models import InvitePreset, Organization
from organizations.tests.factories import OrganizationFactory


@pytest.mark.django_db
def test_resolve_invite_token_prefers_active_preset():
    org = OrganizationFactory()
    preset = InvitePreset.objects.create(organization=org)

    resolved_org, resolved_preset = Organization.resolve_invite_token(preset.token)

    assert resolved_org.id == org.id
    assert resolved_preset.id == preset.id


@pytest.mark.django_db
def test_resolve_invite_token_falls_back_to_org_token():
    org = OrganizationFactory()

    resolved_org, resolved_preset = Organization.resolve_invite_token(org.token)

    assert resolved_org.id == org.id
    assert resolved_preset is None


@pytest.mark.django_db
def test_invite_preset_respects_max_uses():
    org = OrganizationFactory()
    preset = InvitePreset.objects.create(organization=org, max_uses=1)

    assert preset.is_available_for_use() is True

    preset.consume()

    assert preset.is_available_for_use() is False
