import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model
from reports.utils import get_week_start, is_editable_week

User = get_user_model()


def test_get_week_start_monday():
    # 2026-03-04 (水曜) → 2026-03-02 (月曜)
    assert get_week_start(date(2026, 3, 4)) == date(2026, 3, 2)


def test_get_week_start_monday_itself():
    assert get_week_start(date(2026, 3, 2)) == date(2026, 3, 2)


def test_is_editable_week_current(monkeypatch):
    import reports.utils as utils
    monkeypatch.setattr(utils, 'today', lambda: date(2026, 3, 6))
    assert is_editable_week(date(2026, 3, 2)) is True


def test_is_editable_week_one_week_ago(monkeypatch):
    import reports.utils as utils
    monkeypatch.setattr(utils, 'today', lambda: date(2026, 3, 6))
    assert is_editable_week(date(2026, 2, 23)) is True


def test_is_editable_week_two_weeks_ago(monkeypatch):
    import reports.utils as utils
    monkeypatch.setattr(utils, 'today', lambda: date(2026, 3, 6))
    assert is_editable_week(date(2026, 2, 16)) is True


def test_is_editable_week_three_weeks_ago(monkeypatch):
    import reports.utils as utils
    monkeypatch.setattr(utils, 'today', lambda: date(2026, 3, 6))
    assert is_editable_week(date(2026, 2, 9)) is False


def test_is_editable_week_future(monkeypatch):
    import reports.utils as utils
    monkeypatch.setattr(utils, 'today', lambda: date(2026, 3, 6))
    assert is_editable_week(date(2026, 3, 9)) is False


@pytest.mark.django_db
def test_home_requires_login(client):
    response = client.get(reverse('home'))
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_home_shows_calendar(client):
    user = User.objects.create_user(email='u@test.com', password='pass', name='テスト')
    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('home'))
    assert response.status_code == 200
    assert 'weeks' in response.context
