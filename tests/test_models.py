import pytest
from datetime import date
from django.contrib.auth import get_user_model
from reports.models import WeeklyReport, QuestionSection, QuestionItem, Answer, Q1ProjectField

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='u@test.com', password='pass', name='テスト')


@pytest.fixture
def section(db):
    s = QuestionSection.objects.create(
        title='Q2 状態について',
        section_type='radio_matrix',
        scale_labels=['非常に問題', '少し問題', '普通', '良い状態', '非常に良い状態'],
        order=2,
    )
    QuestionItem.objects.create(section=s, label='稼働時間', order=1)
    return s


@pytest.mark.django_db
def test_weekly_report_creation(user):
    report = WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
    assert str(report) == 'テスト - 2026-03-02週'


@pytest.mark.django_db
def test_weekly_report_is_submitted_false(user):
    report = WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
    assert report.is_submitted is False


@pytest.mark.django_db
def test_answer_for_radio_matrix(user, section):
    report = WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
    item = section.items.first()
    answer = Answer.objects.create(
        report=report,
        question_section=section,
        question_item=item,
        value='普通',
    )
    assert answer.value == '普通'


@pytest.mark.django_db
def test_q1_project_field(user):
    report = WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
    Q1ProjectField.objects.create(report=report, label='プロジェクト名', value='政府系システム', order=1)
    assert report.q1_fields.count() == 1


@pytest.mark.django_db
def test_weekly_report_unique_per_user_week(user):
    WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        WeeklyReport.objects.create(user=user, week_start=date(2026, 3, 2))
