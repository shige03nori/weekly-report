import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        name='テストユーザー',
    )


@pytest.mark.django_db
def test_login_page_get(client):
    response = client.get(reverse('login'))
    assert response.status_code == 200


def test_login_success(client, user):
    response = client.post(reverse('login'), {
        'username': 'test@example.com',
        'password': 'testpass123',
    })
    assert response.status_code == 302
    assert response.url == '/'


def test_login_failure(client, user):
    response = client.post(reverse('login'), {
        'username': 'test@example.com',
        'password': 'wrongpassword',
    })
    assert response.status_code == 200
    assert 'メールアドレスまたはパスワードが正しくありません' in response.content.decode()


def test_logout(client, user):
    client.login(username='test@example.com', password='testpass123')
    response = client.post(reverse('logout'))
    assert response.status_code == 302


def test_password_change_requires_login(client):
    response = client.get(reverse('password_change'))
    assert response.status_code == 302
    assert '/login/' in response.url


def test_password_change_success(client, user):
    client.login(username='test@example.com', password='testpass123')
    response = client.post(reverse('password_change'), {
        'old_password': 'testpass123',
        'new_password1': 'newpass456!Aa',
        'new_password2': 'newpass456!Aa',
    })
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password('newpass456!Aa')
