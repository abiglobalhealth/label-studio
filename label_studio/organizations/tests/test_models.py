import pytest

from organizations.models import Organization
from organizations.tests.factories import OrganizationFactory
from users.tests.factories import UserFactory


@pytest.mark.django_db
def test_find_by_user_prefers_latest_active_membership():
    user = UserFactory(active_organization=None)

    old_org = OrganizationFactory()
    old_member = old_org.add_user(user)

    new_org = OrganizationFactory()
    new_member = new_org.add_user(user)

    assert old_member is not None
    assert new_member is not None

    found = Organization.find_by_user(user)
    assert found.id == new_org.id


@pytest.mark.django_db
def test_find_by_user_ignores_deleted_memberships():
    user = UserFactory(active_organization=None)

    deleted_org = OrganizationFactory()
    deleted_member = deleted_org.add_user(user)
    assert deleted_member is not None
    deleted_member.soft_delete()

    active_org = OrganizationFactory()
    active_member = active_org.add_user(user)
    assert active_member is not None

    found = Organization.find_by_user(user)
    assert found.id == active_org.id
