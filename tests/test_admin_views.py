import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model
from reports.models import WeeklyReport

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email='admin@test.com', password='pass', name='管理者', is_admin=True
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email='user@test.com', password='pass', name='一般ユーザー'
    )


def test_admin_status_requires_admin(client, regular_user):
    client.login(username='user@test.com', password='pass')
    response = client.get(reverse('admin_status'))
    assert response.status_code == 403


def test_admin_status_shows_users(client, admin_user, regular_user):
    client.login(username='admin@test.com', password='pass')
    from django.utils import timezone
    WeeklyReport.objects.create(
        user=regular_user, week_start=date(2026, 3, 2),
        submitted_at=timezone.now()
    )
    response = client.get(reverse('admin_status') + '?week=2026-03-02')
    assert response.status_code == 200
    assert '一般ユーザー' in response.content.decode()


def test_admin_summary(client, admin_user, regular_user):
    client.login(username='admin@test.com', password='pass')
    response = client.get(reverse('admin_summary'))
    assert response.status_code == 200
