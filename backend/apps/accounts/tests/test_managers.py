import pytest

from apps.accounts.models import User


@pytest.mark.django_db
class TestCreateUser:
    def test_creates_user_with_normalized_email(self):
        user = User.objects.create_user(email="Maria@Example.com", password="strongpass123")

        assert user.email == "Maria@example.com"
        assert user.check_password("strongpass123")
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_raises_without_email(self):
        with pytest.raises(ValueError, match="e-mail"):
            User.objects.create_user(email="", password="strongpass123")


@pytest.mark.django_db
class TestCreateSuperuser:
    def test_creates_superuser_with_expected_flags(self):
        user = User.objects.create_superuser(email="admin@example.com", password="strongpass123")

        assert user.is_staff is True
        assert user.is_superuser is True

    def test_raises_when_is_staff_overridden_to_false(self):
        with pytest.raises(ValueError, match="is_staff"):
            User.objects.create_superuser(email="admin@example.com", password="strongpass123", is_staff=False)

    def test_raises_when_is_superuser_overridden_to_false(self):
        with pytest.raises(ValueError, match="is_superuser"):
            User.objects.create_superuser(email="admin@example.com", password="strongpass123", is_superuser=False)
