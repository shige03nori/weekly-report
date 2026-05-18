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


class AdminOneOnOneQuestionsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin2@test.com', password='pass', name='Admin2', is_admin=True
        )
        self.client.login(email='admin2@test.com', password='pass')

    def test_questions_view_returns_200(self):
        response = self.client.get('/mgmt/oneone/questions/')
        self.assertEqual(response.status_code, 200)

    def test_questions_view_shows_initial_data(self):
        response = self.client.get('/mgmt/oneone/questions/')
        self.assertContains(response, '最近の業務はどう？')

    def test_add_question(self):
        count_before = OneOnOneQuestion.objects.count()
        self.client.post('/mgmt/oneone/questions/', {
            'action': 'add',
            'section_number': 1,
            'question_text': 'テスト質問',
            'hint_text': '',
        })
        self.assertEqual(OneOnOneQuestion.objects.count(), count_before + 1)
        new_q = OneOnOneQuestion.objects.get(question_text='テスト質問')
        self.assertTrue(new_q.is_active)

    def test_toggle_question(self):
        q = OneOnOneQuestion.objects.filter(section_number=1).first()
        self.client.post('/mgmt/oneone/questions/', {
            'action': 'toggle',
            'question_id': q.id,
        })
        q.refresh_from_db()
        self.assertFalse(q.is_active)


class AdminOneOnOneNewViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin3@test.com', password='pass', name='Admin3', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member3@test.com', password='pass', name='Member3'
        )
        self.client.login(email='admin3@test.com', password='pass')

    def test_new_view_get_returns_200(self):
        response = self.client.get('/mgmt/oneone/new/')
        self.assertEqual(response.status_code, 200)

    def test_new_view_post_creates_session(self):
        response = self.client.post('/mgmt/oneone/new/', {
            'member': self.member.id,
            'conducted_at': '2026-05-18',
        })
        self.assertEqual(OneOnOneSession.objects.count(), 1)
        session = OneOnOneSession.objects.first()
        self.assertEqual(session.interviewer, self.admin)
        self.assertEqual(str(session.conducted_at), '2026-05-18')

    def test_new_view_post_creates_answers_for_active_questions(self):
        active_count = OneOnOneQuestion.objects.filter(is_active=True).count()
        self.client.post('/mgmt/oneone/new/', {
            'member': self.member.id,
            'conducted_at': '2026-05-18',
        })
        session = OneOnOneSession.objects.first()
        self.assertEqual(OneOnOneAnswer.objects.filter(session=session).count(), active_count)

    def test_new_view_post_redirects_to_detail(self):
        response = self.client.post('/mgmt/oneone/new/', {
            'member': self.member.id,
            'conducted_at': '2026-05-18',
        })
        session = OneOnOneSession.objects.first()
        self.assertRedirects(response, f'/mgmt/oneone/{session.id}/')


class AdminOneOnOneDetailViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin4@test.com', password='pass', name='Admin4', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member4@test.com', password='pass', name='Member4'
        )
        self.question = OneOnOneQuestion.objects.filter(is_active=True).first()
        self.session = OneOnOneSession.objects.create(
            member=self.member, interviewer=self.admin,
            conducted_at=date(2026, 5, 18)
        )
        self.answer = OneOnOneAnswer.objects.create(
            session=self.session, question=self.question, text=''
        )
        self.client.login(email='admin4@test.com', password='pass')

    def test_detail_view_returns_200(self):
        response = self.client.get(f'/mgmt/oneone/{self.session.id}/')
        self.assertEqual(response.status_code, 200)

    def test_detail_view_shows_question(self):
        response = self.client.get(f'/mgmt/oneone/{self.session.id}/')
        self.assertContains(response, self.question.question_text)

    def test_detail_view_post_updates_answer(self):
        self.client.post(f'/mgmt/oneone/{self.session.id}/', {
            f'answer_{self.answer.id}': '更新されたテキスト',
        })
        self.answer.refresh_from_db()
        self.assertEqual(self.answer.text, '更新されたテキスト')

    def test_detail_view_post_redirects(self):
        response = self.client.post(f'/mgmt/oneone/{self.session.id}/', {
            f'answer_{self.answer.id}': 'テキスト',
        })
        self.assertRedirects(response, f'/mgmt/oneone/{self.session.id}/')


class MemberOneOnOneViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin5@test.com', password='pass', name='Admin5', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member5@test.com', password='pass', name='Member5'
        )
        self.other = User.objects.create_user(
            email='other5@test.com', password='pass', name='Other5'
        )
        question = OneOnOneQuestion.objects.filter(is_active=True).first()
        self.session = OneOnOneSession.objects.create(
            member=self.member, interviewer=self.admin,
            conducted_at=date(2026, 5, 18)
        )
        OneOnOneAnswer.objects.create(session=self.session, question=question, text='回答')

    def test_member_list_returns_200(self):
        self.client.login(email='member5@test.com', password='pass')
        response = self.client.get('/oneone/')
        self.assertEqual(response.status_code, 200)

    def test_member_list_shows_own_sessions(self):
        self.client.login(email='member5@test.com', password='pass')
        response = self.client.get('/oneone/')
        self.assertContains(response, '2026-05-18')

    def test_member_list_requires_login(self):
        response = self.client.get('/oneone/')
        self.assertRedirects(response, '/login/?next=/oneone/')

    def test_member_detail_returns_200_for_own(self):
        self.client.login(email='member5@test.com', password='pass')
        response = self.client.get(f'/oneone/{self.session.id}/')
        self.assertEqual(response.status_code, 200)

    def test_member_detail_returns_403_for_others(self):
        self.client.login(email='other5@test.com', password='pass')
        response = self.client.get(f'/oneone/{self.session.id}/')
        self.assertEqual(response.status_code, 403)

    def test_member_detail_shows_answers(self):
        self.client.login(email='member5@test.com', password='pass')
        response = self.client.get(f'/oneone/{self.session.id}/')
        self.assertContains(response, '回答')
