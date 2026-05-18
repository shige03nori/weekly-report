from datetime import date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from .models import OneOnOneQuestion, OneOnOneSession, OneOnOneAnswer

User = get_user_model()


class OneOnOneModelTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass', name='Admin', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member@test.com', password='pass', name='Member'
        )

    def test_question_creation(self):
        q = OneOnOneQuestion.objects.create(
            section_number=1,
            section_title='現場状況確認',
            question_text='最近の業務はどう？',
            hint_text='ふんわり聞く',
            order=1,
        )
        self.assertEqual(q.section_number, 1)
        self.assertTrue(q.is_active)
        self.assertIn('最近の業務はどう？', str(q))

    def test_session_creation(self):
        session = OneOnOneSession.objects.create(
            member=self.member,
            interviewer=self.admin,
            conducted_at=date(2026, 5, 18),
        )
        self.assertEqual(session.member, self.member)
        self.assertIn('Member', str(session))

    def test_answer_creation(self):
        q = OneOnOneQuestion.objects.create(
            section_number=1, section_title='現場状況確認',
            question_text='最近の業務はどう？', order=1
        )
        session = OneOnOneSession.objects.create(
            member=self.member, interviewer=self.admin,
            conducted_at=date(2026, 5, 18)
        )
        answer = OneOnOneAnswer.objects.create(session=session, question=q, text='問題ない')
        self.assertEqual(answer.text, '問題ない')

    def test_question_protect_on_answer_exists(self):
        q = OneOnOneQuestion.objects.create(
            section_number=1, section_title='現場状況確認',
            question_text='最近の業務はどう？', order=1
        )
        session = OneOnOneSession.objects.create(
            member=self.member, interviewer=self.admin,
            conducted_at=date(2026, 5, 18)
        )
        OneOnOneAnswer.objects.create(session=session, question=q, text='')
        with self.assertRaises(ProtectedError):
            q.delete()


class OneOnOneInitialDataTest(TestCase):
    def test_initial_questions_count(self):
        self.assertEqual(OneOnOneQuestion.objects.count(), 17)

    def test_all_sections_present(self):
        sections = set(OneOnOneQuestion.objects.values_list('section_number', flat=True).distinct())
        self.assertEqual(sections, {1, 2, 3, 4, 5, 6})

    def test_section1_has_5_questions(self):
        self.assertEqual(OneOnOneQuestion.objects.filter(section_number=1).count(), 5)

    def test_section6_has_3_questions(self):
        self.assertEqual(OneOnOneQuestion.objects.filter(section_number=6).count(), 3)


class AdminOneOnOneListViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass', name='Admin', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member@test.com', password='pass', name='Member'
        )
        self.client.login(email='admin@test.com', password='pass')

    def test_list_view_returns_200(self):
        response = self.client.get('/mgmt/oneone/')
        self.assertEqual(response.status_code, 200)

    def test_list_view_shows_all_active_users(self):
        response = self.client.get('/mgmt/oneone/')
        self.assertContains(response, 'Member')
        self.assertContains(response, 'Admin')

    def test_list_view_requires_admin(self):
        self.client.logout()
        self.client.login(email='member@test.com', password='pass')
        response = self.client.get('/mgmt/oneone/')
        self.assertEqual(response.status_code, 403)

    def test_member_history_view_returns_200(self):
        response = self.client.get(f'/mgmt/oneone/member/{self.member.id}/')
        self.assertEqual(response.status_code, 200)

    def test_member_history_shows_sessions(self):
        q = OneOnOneQuestion.objects.filter(is_active=True).first()
        session = OneOnOneSession.objects.create(
            member=self.member, interviewer=self.admin,
            conducted_at=date(2026, 5, 18)
        )
        response = self.client.get(f'/mgmt/oneone/member/{self.member.id}/')
        self.assertContains(response, '2026-05-18')
