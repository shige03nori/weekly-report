import pytest
from datetime import date, datetime
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from reports.models import (
    WeeklyReport, QuestionSection, QuestionItem,
    Q1FieldTemplate, Q1ProjectField
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='u@test.com', password='pass', name='テスト')


@pytest.fixture
def q1_templates(db):
    Q1FieldTemplate.objects.create(label='プロジェクト名', order=1)
    Q1FieldTemplate.objects.create(label='商流', order=2)


@pytest.fixture
def section(db):
    s = QuestionSection.objects.create(
        title='Q2 状態',
        section_type='radio_matrix',
        scale_labels=['普通', '良い'],
        order=2,
    )
    QuestionItem.objects.create(section=s, label='稼働時間', order=1)
    return s


@pytest.fixture
def select_section(db):
    return QuestionSection.objects.create(
        title='Q4 残業時間',
        section_type='select',
        scale_labels=['0h', '〜10h'],
        order=4,
    )


@pytest.fixture
def free_section(db):
    return QuestionSection.objects.create(
        title='Q5 来週の予定',
        section_type='free_text',
        placeholder='決まっていれば',
        order=5,
    )


@pytest.mark.django_db
def test_report_form_get(client, user, q1_templates, section):
    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('report_form', args=['2026-03-02']))
    assert response.status_code == 200
    assert 'weeks' not in response.context  # カレンダーでなくフォーム画面
    assert 'q1_templates' in response.context


@pytest.mark.django_db
def test_report_form_requires_login(client):
    response = client.get(reverse('report_form', args=['2026-03-02']))
    assert response.status_code == 302
    assert '/login/' in response.url


@pytest.mark.django_db
def test_report_submit(client, user, q1_templates, section):
    client.login(username='u@test.com', password='pass')
    item = section.items.first()
    data = {
        'q1_プロジェクト名': '政府系システム',
        'q1_商流': 'NTTデータ',
        f'answer_{section.id}_{item.id}': '普通',
        'action': 'submit',
    }
    response = client.post(reverse('report_form', args=['2026-03-02']), data)
    assert response.status_code == 302
    report = WeeklyReport.objects.get(user=user, week_start=date(2026, 3, 2))
    assert report.is_submitted
    assert report.q1_fields.filter(label='プロジェクト名', value='政府系システム').exists()


@pytest.mark.django_db
def test_report_draft_save(client, user, q1_templates, section):
    client.login(username='u@test.com', password='pass')
    data = {
        'q1_プロジェクト名': '下書きプロジェクト',
        'q1_商流': '',
        'action': 'draft',
    }
    response = client.post(reverse('report_form', args=['2026-03-02']), data)
    assert response.status_code == 302
    report = WeeklyReport.objects.get(user=user, week_start=date(2026, 3, 2))
    assert not report.is_submitted


@pytest.mark.django_db
def test_report_prefill_q1_from_previous(client, user, q1_templates):
    """Q1は直前の提出済み週報の値をデフォルト表示する"""
    prev_report = WeeklyReport.objects.create(
        user=user,
        week_start=date(2026, 2, 23),
        submitted_at=timezone.make_aware(datetime(2026, 2, 23, 12, 0)),
    )
    Q1ProjectField.objects.create(
        report=prev_report, label='プロジェクト名', value='前回のプロジェクト', order=1
    )

    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('report_form', args=['2026-03-02']))
    assert response.status_code == 200
    assert '前回のプロジェクト' in response.content.decode()


@pytest.mark.django_db
def test_report_readonly_view(client, user, q1_templates, section):
    """提出済み週報は読み取り専用で閲覧できる"""
    report = WeeklyReport.objects.create(
        user=user,
        week_start=date(2026, 2, 9),  # 4週前 = 編集不可
        submitted_at=timezone.make_aware(datetime(2026, 2, 9, 12, 0)),
    )
    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('report_readonly', args=['2026-02-09']))
    assert response.status_code == 200
