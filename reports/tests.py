from datetime import date
from django.test import TestCase
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
