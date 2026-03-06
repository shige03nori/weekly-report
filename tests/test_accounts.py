import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_user_with_email():
    user = User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        name='テストユーザー',
    )
    assert user.email == 'test@example.com'
    assert user.name == 'テストユーザー'
    assert user.is_admin is False
    assert user.check_password('testpass123')


@pytest.mark.django_db
def test_create_admin_user():
    user = User.objects.create_superuser(
        email='admin@example.com',
        password='adminpass123',
        name='管理者',
    )
    assert user.is_admin is True
    assert user.is_staff is True


@pytest.mark.django_db
def test_user_str():
    user = User.objects.create_user(
        email='test@example.com',
        password='pass',
        name='テスト',
    )
    assert str(user) == 'テスト (test@example.com)'
