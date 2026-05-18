# 1on1ミーティング機能 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 月1回の1on1ミーティングの記録・閲覧機能を既存の `reports` アプリに追加する

**Architecture:** `reports/models.py` に3モデル追加、`views_admin.py` に管理者ビュー5本・`views.py` にメンバービュー2本追加。質問はDBで管理しデータマイグレーションで初期投入。

**Tech Stack:** Django 4.x、Bootstrap 5（ダークテーマ）、Django TestCase

---

## ファイル構成

**新規作成:**
- `reports/migrations/000X_add_oneone_models.py` (makemigrations で自動生成)
- `reports/migrations/000Y_oneone_initial_data.py` (手動作成)
- `templates/reports/admin_oneone_list.html`
- `templates/reports/admin_oneone_member.html`
- `templates/reports/admin_oneone_questions.html`
- `templates/reports/admin_oneone_new.html`
- `templates/reports/admin_oneone_detail.html`
- `templates/reports/oneone_member_list.html`
- `templates/reports/oneone_member_detail.html`

**既存ファイル変更:**
- `reports/models.py` — 3モデル追加
- `reports/forms_admin.py` — 2フォーム追加
- `reports/views_admin.py` — 5ビュー追加
- `reports/views.py` — 2ビュー追加
- `reports/urls.py` — 7 URL追加
- `reports/tests.py` — テスト追加
- `templates/reports/admin_base.html` — 1on1タブ追加
- `templates/reports/home.html` — 1on1リンク追加

---

## Task 1: モデルとスキーママイグレーション

**Files:**
- Modify: `reports/models.py`
- Modify: `reports/tests.py`
- Create: `reports/migrations/000X_add_oneone_models.py` (auto-generated)

- [ ] **Step 1: テストを書く（失敗するはず）**

`reports/tests.py` を以下に置き換え:

```python
from datetime import date
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
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
        from django.db.models import ProtectedError
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.OneOnOneModelTest
```

Expected: `ImportError: cannot import name 'OneOnOneQuestion' from 'reports.models'`

- [ ] **Step 3: モデルを実装**

`reports/models.py` の末尾（`Answer` クラスの後）に追加:

```python
class OneOnOneQuestion(models.Model):
    section_number = models.IntegerField(verbose_name='セクション番号')
    section_title = models.CharField(max_length=100, verbose_name='セクション名')
    question_text = models.CharField(max_length=200, verbose_name='質問文')
    hint_text = models.CharField(max_length=200, blank=True, default='', verbose_name='補足テキスト')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['section_number', 'order']
        verbose_name = '1on1質問'
        verbose_name_plural = '1on1質問'

    def __str__(self):
        return f'{self.section_number}. {self.question_text}'


class OneOnOneSession(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oneone_sessions',
        verbose_name='メンバー',
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oneone_interviews',
        verbose_name='担当管理者',
    )
    conducted_at = models.DateField(verbose_name='実施日')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-conducted_at']
        verbose_name = '1on1セッション'
        verbose_name_plural = '1on1セッション'

    def __str__(self):
        return f'{self.member.name} - {self.conducted_at}'


class OneOnOneAnswer(models.Model):
    session = models.ForeignKey(
        OneOnOneSession,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='セッション',
    )
    question = models.ForeignKey(
        OneOnOneQuestion,
        on_delete=models.PROTECT,
        verbose_name='質問',
    )
    text = models.TextField(blank=True, verbose_name='回答')

    class Meta:
        verbose_name = '1on1回答'
        verbose_name_plural = '1on1回答'

    def __str__(self):
        return f'{self.session} - {self.question.question_text[:20]}'
```

- [ ] **Step 4: マイグレーションを生成・適用**

```
python manage.py makemigrations reports
python manage.py migrate
```

Expected: `Migrations for 'reports': reports/migrations/0003_oneoneoneanswer_...py` (番号はプロジェクトの状態に依存)

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.OneOnOneModelTest
```

Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 6: コミット**

```bash
git add reports/models.py reports/tests.py reports/migrations/
git commit -m "feat: add OneOnOneQuestion, OneOnOneSession, OneOnOneAnswer models"
```

---

## Task 2: データマイグレーション（初期質問17件投入）

**Files:**
- Create: `reports/migrations/000Y_oneone_initial_data.py`
- Modify: `reports/tests.py`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に `OneOnOneModelTest` クラスの後に追加:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.OneOnOneInitialDataTest
```

Expected: `AssertionError: 0 != 17`

- [ ] **Step 3: データマイグレーションを作成**

```
python manage.py makemigrations --empty reports --name oneone_initial_data
```

生成されたファイル（`reports/migrations/000Y_oneone_initial_data.py`）を以下の内容に編集:

```python
from django.db import migrations


def create_initial_questions(apps, schema_editor):
    OneOnOneQuestion = apps.get_model('reports', 'OneOnOneQuestion')
    questions = [
        (1, '現場状況確認', '最近の業務はどう？', 'ふんわり聞く　狙い：自分の意志が出やすくなる', 1),
        (1, '現場状況確認', '人間関係はどうか？', '', 2),
        (1, '現場状況確認', '作業量は多すぎない？', '', 3),
        (1, '現場状況確認', 'その他、困っていることある？', '', 4),
        (1, '現場状況確認', '今後の見通し', '', 5),
        (2, '技術・業務の成長確認', '今勉強していることある？', 'AIとか・・・', 1),
        (2, '技術・業務の成長確認', '気になっている事ある？', '', 2),
        (2, '技術・業務の成長確認', '最近出来るようになったこと', 'IT以外の些細な所も', 3),
        (3, 'メンタル・コンディション確認', '疲れてない？', '', 1),
        (3, 'メンタル・コンディション確認', '休日リフレッシュできてる？', '', 2),
        (3, 'メンタル・コンディション確認', '会社に対して不安ある？', '', 3),
        (4, 'キャリア確認', '今後どういうエンジニアになりたい？', '', 1),
        (4, 'キャリア確認', '将来的にリーダーやってみたい？', '', 2),
        (5, '会社への要望・改善', 'やってみたい企画やイベント', '', 1),
        (6, '次回までのアクション', '個人目標どう？', '', 1),
        (6, '次回までのアクション', '来月の1on1までになにをするか？', '', 2),
        (6, '次回までのアクション', '次回予定日', '', 3),
    ]
    for section_number, section_title, question_text, hint_text, order in questions:
        OneOnOneQuestion.objects.create(
            section_number=section_number,
            section_title=section_title,
            question_text=question_text,
            hint_text=hint_text,
            order=order,
        )


def reverse_initial_questions(apps, schema_editor):
    OneOnOneQuestion = apps.get_model('reports', 'OneOnOneQuestion')
    OneOnOneQuestion.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        # 直前のマイグレーションファイル名に変更すること
        # 例: ('reports', '0003_oneoneoneanswer_oneoneonesession_...')
        ('reports', '0003_oneoneoneanswer_oneoneonesession_oneoneonequestion'),
    ]

    operations = [
        migrations.RunPython(create_initial_questions, reverse_initial_questions),
    ]
```

**注意:** `dependencies` の値は Step 1 で生成されたスキーママイグレーションの実際のファイル名に合わせること。`reports/migrations/` フォルダの中の最新ファイル名を確認する。

- [ ] **Step 4: マイグレーションを適用**

```
python manage.py migrate
```

Expected: `Running migrations: Applying reports.000Y_oneone_initial_data... OK`

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.OneOnOneInitialDataTest
```

Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 6: コミット**

```bash
git add reports/migrations/ reports/tests.py
git commit -m "feat: add data migration for initial 1on1 questions"
```

---

## Task 3: フォームと URL パターン

**Files:**
- Modify: `reports/forms_admin.py`
- Modify: `reports/urls.py`

- [ ] **Step 1: フォームを追加**

`reports/forms_admin.py` の末尾に追加:

```python
from .models import OneOnOneSession, OneOnOneQuestion


class OneOnOneSessionForm(forms.ModelForm):
    class Meta:
        model = OneOnOneSession
        fields = ['member', 'conducted_at']
        widgets = {
            'conducted_at': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = User.objects.filter(is_active=True).order_by('name')
        self.fields['member'].label = 'メンバー'
        self.fields['conducted_at'].label = '実施日'


class OneOnOneQuestionForm(forms.ModelForm):
    class Meta:
        model = OneOnOneQuestion
        fields = ['section_number', 'question_text', 'hint_text']
        widgets = {
            'section_number': forms.Select(
                choices=[(i, f'{i}') for i in range(1, 7)],
                attrs={'class': 'form-select'},
            ),
            'question_text': forms.TextInput(attrs={'class': 'form-control'}),
            'hint_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '任意'}),
        }
        labels = {
            'section_number': 'セクション番号',
            'question_text': '質問文',
            'hint_text': '補足テキスト',
        }
```

- [ ] **Step 2: URL パターンを追加**

`reports/urls.py` の `urlpatterns` に追加:

```python
# 管理者向け 1on1
path('mgmt/oneone/', views_admin.admin_oneone_list_view, name='admin_oneone_list'),
path('mgmt/oneone/new/', views_admin.admin_oneone_new_view, name='admin_oneone_new'),
path('mgmt/oneone/questions/', views_admin.admin_oneone_questions_view, name='admin_oneone_questions'),
path('mgmt/oneone/member/<int:user_id>/', views_admin.admin_oneone_member_view, name='admin_oneone_member'),
path('mgmt/oneone/<int:session_id>/', views_admin.admin_oneone_detail_view, name='admin_oneone_detail'),
# メンバー向け 1on1
path('oneone/', views.oneone_member_list_view, name='oneone_member_list'),
path('oneone/<int:session_id>/', views.oneone_member_detail_view, name='oneone_member_detail'),
```

**注意:** `mgmt/oneone/questions/` と `mgmt/oneone/member/<int:user_id>/` は `mgmt/oneone/<int:session_id>/` より前に定義すること（URLパターンの優先順位のため）。

- [ ] **Step 3: コミット**

```bash
git add reports/forms_admin.py reports/urls.py
git commit -m "feat: add 1on1 forms and URL patterns"
```

---

## Task 4: 管理者 — 一覧・メンバー履歴ビューとテンプレート

**Files:**
- Modify: `reports/views_admin.py`
- Modify: `reports/tests.py`
- Create: `templates/reports/admin_oneone_list.html`
- Create: `templates/reports/admin_oneone_member.html`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.AdminOneOnOneListViewTest
```

Expected: `AttributeError: module 'reports.views_admin' has no attribute 'admin_oneone_list_view'`

- [ ] **Step 3: ビューを実装**

`reports/views_admin.py` の末尾に追加:

```python
@admin_required
def admin_oneone_list_view(request):
    from .models import OneOnOneSession
    selected_dept = request.GET.get('department', '')
    all_users = User.objects.filter(is_active=True).order_by('name')
    departments = sorted(set(all_users.values_list('department', flat=True)))
    if selected_dept:
        all_users = all_users.filter(department=selected_dept)

    users_data = []
    for user in all_users:
        last_session = (
            OneOnOneSession.objects.filter(member=user)
            .order_by('-conducted_at')
            .first()
        )
        count = OneOnOneSession.objects.filter(member=user).count()
        users_data.append({
            'user': user,
            'last_session': last_session,
            'count': count,
        })

    return render(request, 'reports/admin_oneone_list.html', {
        'users_data': users_data,
        'departments': departments,
        'selected_dept': selected_dept,
    })


@admin_required
def admin_oneone_member_view(request, user_id):
    from .models import OneOnOneSession
    from django.shortcuts import get_object_or_404
    target_user = get_object_or_404(User, id=user_id)
    sessions = OneOnOneSession.objects.filter(member=target_user).order_by('-conducted_at')
    return render(request, 'reports/admin_oneone_member.html', {
        'target_user': target_user,
        'sessions': sessions,
    })
```

- [ ] **Step 4: `admin_oneone_list.html` を作成**

```html
{% extends 'reports/admin_base.html' %}
{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4 class="mb-0">1on1 管理</h4>
  <div class="d-flex gap-2">
    <a href="{% url 'admin_oneone_questions' %}" class="btn btn-sm btn-outline-secondary">質問管理</a>
    <a href="{% url 'admin_oneone_new' %}" class="btn btn-sm btn-primary">＋ 新規 1on1 記録</a>
  </div>
</div>

<form method="get" class="mb-3">
  {% include 'reports/_dept_filter.html' %}
  <button type="submit" class="btn btn-sm btn-outline-secondary ms-2">絞り込み</button>
</form>

<table class="table table-hover">
  <thead>
    <tr>
      <th>メンバー</th>
      <th>部署</th>
      <th>最終実施日</th>
      <th>実施回数</th>
      <th>担当管理者</th>
    </tr>
  </thead>
  <tbody>
    {% for item in users_data %}
    <tr>
      <td>
        {% if item.count %}
          <a href="{% url 'admin_oneone_member' user_id=item.user.id %}">{{ item.user.name }}</a>
        {% else %}
          {{ item.user.name }}
        {% endif %}
      </td>
      <td class="text-secondary">{{ item.user.department|default:"—" }}</td>
      <td>
        {% if item.last_session %}
          {{ item.last_session.conducted_at }}
        {% else %}
          <span class="text-danger">—（未実施）</span>
        {% endif %}
      </td>
      <td>{{ item.count }}回</td>
      <td class="text-secondary">
        {% if item.last_session %}{{ item.last_session.interviewer.name }}{% else %}—{% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 5: `admin_oneone_member.html` を作成**

```html
{% extends 'reports/admin_base.html' %}
{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4 class="mb-0">{{ target_user.name }} の1on1履歴</h4>
  <a href="{% url 'admin_oneone_list' %}" class="btn btn-sm btn-outline-secondary">← 一覧に戻る</a>
</div>

{% if sessions %}
<table class="table table-hover">
  <thead>
    <tr>
      <th>実施日</th>
      <th>担当管理者</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for session in sessions %}
    <tr>
      <td>{{ session.conducted_at }}</td>
      <td class="text-secondary">{{ session.interviewer.name }}</td>
      <td class="text-end">
        <a href="{% url 'admin_oneone_detail' session_id=session.id %}" class="btn btn-sm btn-outline-primary">詳細</a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
<p class="text-secondary">まだ1on1の記録がありません。</p>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: テストを実行してパスを確認**

```
python manage.py test reports.tests.AdminOneOnOneListViewTest
```

Expected: `Ran 5 tests in ...s OK`

- [ ] **Step 7: コミット**

```bash
git add reports/views_admin.py reports/tests.py templates/reports/admin_oneone_list.html templates/reports/admin_oneone_member.html
git commit -m "feat: add admin 1on1 list and member history views"
```

---

## Task 5: 管理者 — 質問管理ビューとテンプレート

**Files:**
- Modify: `reports/views_admin.py`
- Modify: `reports/tests.py`
- Create: `templates/reports/admin_oneone_questions.html`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.AdminOneOnOneQuestionsViewTest
```

Expected: `AttributeError: module 'reports.views_admin' has no attribute 'admin_oneone_questions_view'`

- [ ] **Step 3: ビューを実装**

`reports/views_admin.py` の末尾に追加:

```python
@admin_required
def admin_oneone_questions_view(request):
    from .models import OneOnOneQuestion
    from .forms_admin import OneOnOneQuestionForm
    from django.shortcuts import get_object_or_404
    from django.db.models import Max

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = OneOnOneQuestionForm(request.POST)
            if form.is_valid():
                q = form.save(commit=False)
                max_order = OneOnOneQuestion.objects.filter(
                    section_number=q.section_number
                ).aggregate(Max('order'))['order__max'] or 0
                q.order = max_order + 1
                q.save()
        elif action == 'toggle':
            question_id = request.POST.get('question_id')
            q = get_object_or_404(OneOnOneQuestion, id=question_id)
            q.is_active = not q.is_active
            q.save()
        return redirect('admin_oneone_questions')

    form = OneOnOneQuestionForm()
    questions = OneOnOneQuestion.objects.order_by('section_number', 'order')
    sections = {}
    for q in questions:
        key = (q.section_number, q.section_title)
        sections.setdefault(key, []).append(q)

    return render(request, 'reports/admin_oneone_questions.html', {
        'sections': sections,
        'form': form,
    })
```

- [ ] **Step 4: `admin_oneone_questions.html` を作成**

```html
{% extends 'reports/admin_base.html' %}
{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-3">
  <h4 class="mb-0">1on1 質問管理</h4>
  <a href="{% url 'admin_oneone_list' %}" class="btn btn-sm btn-outline-secondary">← 1on1一覧</a>
</div>

{% for section_key, items in sections.items %}
<div class="mb-4">
  <h6 class="text-warning">■ {{ section_key.0 }}. {{ section_key.1 }}</h6>
  <table class="table table-sm">
    <tbody>
      {% for q in items %}
      <tr class="{% if not q.is_active %}opacity-50{% endif %}">
        <td>{{ q.question_text }}</td>
        <td class="text-secondary small">{{ q.hint_text }}</td>
        <td class="text-end">
          <form method="post" class="d-inline">
            {% csrf_token %}
            <input type="hidden" name="action" value="toggle">
            <input type="hidden" name="question_id" value="{{ q.id }}">
            {% if q.is_active %}
              <button type="submit" class="btn btn-sm btn-outline-secondary">無効化</button>
            {% else %}
              <button type="submit" class="btn btn-sm btn-outline-success">有効化</button>
            {% endif %}
          </form>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endfor %}

<hr>
<h5>＋ 質問を追加</h5>
<form method="post" class="row g-2 align-items-end">
  {% csrf_token %}
  <input type="hidden" name="action" value="add">
  <div class="col-auto">
    <label class="form-label small">セクション番号</label>
    {{ form.section_number }}
  </div>
  <div class="col-4">
    <label class="form-label small">質問文</label>
    {{ form.question_text }}
  </div>
  <div class="col-4">
    <label class="form-label small">補足テキスト（任意）</label>
    {{ form.hint_text }}
  </div>
  <div class="col-auto">
    <button type="submit" class="btn btn-primary">追加</button>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.AdminOneOnOneQuestionsViewTest
```

Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 6: コミット**

```bash
git add reports/views_admin.py reports/tests.py templates/reports/admin_oneone_questions.html
git commit -m "feat: add admin 1on1 questions management view"
```

---

## Task 6: 管理者 — 新規セッション作成ビューとテンプレート

**Files:**
- Modify: `reports/views_admin.py`
- Modify: `reports/tests.py`
- Create: `templates/reports/admin_oneone_new.html`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.AdminOneOnOneNewViewTest
```

Expected: `AttributeError: module 'reports.views_admin' has no attribute 'admin_oneone_new_view'`

- [ ] **Step 3: ビューを実装**

`reports/views_admin.py` の末尾に追加:

```python
@admin_required
def admin_oneone_new_view(request):
    from .models import OneOnOneQuestion, OneOnOneSession, OneOnOneAnswer
    from .forms_admin import OneOnOneSessionForm

    if request.method == 'POST':
        form = OneOnOneSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.interviewer = request.user
            session.save()
            active_questions = OneOnOneQuestion.objects.filter(is_active=True)
            OneOnOneAnswer.objects.bulk_create([
                OneOnOneAnswer(session=session, question=q, text='')
                for q in active_questions
            ])
            return redirect('admin_oneone_detail', session_id=session.id)
    else:
        form = OneOnOneSessionForm()

    return render(request, 'reports/admin_oneone_new.html', {'form': form})
```

- [ ] **Step 4: `admin_oneone_new.html` を作成**

```html
{% extends 'reports/admin_base.html' %}
{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h4 class="mb-0">新規 1on1 記録</h4>
  <a href="{% url 'admin_oneone_list' %}" class="btn btn-sm btn-outline-secondary">← 一覧に戻る</a>
</div>

<form method="post" class="row g-3" style="max-width:600px">
  {% csrf_token %}
  <div class="col-md-6">
    <label class="form-label">メンバー</label>
    {{ form.member }}
    {% if form.member.errors %}<div class="text-danger small">{{ form.member.errors }}</div>{% endif %}
  </div>
  <div class="col-md-6">
    <label class="form-label">実施日</label>
    {{ form.conducted_at }}
    {% if form.conducted_at.errors %}<div class="text-danger small">{{ form.conducted_at.errors }}</div>{% endif %}
  </div>
  <div class="col-12">
    <p class="text-secondary small mb-1">担当管理者: {{ request.user.name }}（ログイン中）</p>
    <button type="submit" class="btn btn-primary">記録を開始する</button>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.AdminOneOnOneNewViewTest
```

Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 6: コミット**

```bash
git add reports/views_admin.py reports/tests.py templates/reports/admin_oneone_new.html
git commit -m "feat: add admin 1on1 new session view"
```

---

## Task 7: 管理者 — セッション詳細ビューとテンプレート

**Files:**
- Modify: `reports/views_admin.py`
- Modify: `reports/tests.py`
- Create: `templates/reports/admin_oneone_detail.html`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.AdminOneOnOneDetailViewTest
```

Expected: `AttributeError: module 'reports.views_admin' has no attribute 'admin_oneone_detail_view'`

- [ ] **Step 3: ビューを実装**

`reports/views_admin.py` の末尾に追加:

```python
@admin_required
def admin_oneone_detail_view(request, session_id):
    from .models import OneOnOneSession
    from django.shortcuts import get_object_or_404

    session = get_object_or_404(OneOnOneSession, id=session_id)

    if request.method == 'POST':
        for answer in session.answers.select_related('question').all():
            key = f'answer_{answer.id}'
            if key in request.POST:
                answer.text = request.POST[key]
                answer.save()
        messages.success(request, '記録を更新しました')
        return redirect('admin_oneone_detail', session_id=session_id)

    answers = session.answers.select_related('question').order_by(
        'question__section_number', 'question__order'
    )
    sections = {}
    for answer in answers:
        q = answer.question
        key = (q.section_number, q.section_title)
        sections.setdefault(key, []).append(answer)

    return render(request, 'reports/admin_oneone_detail.html', {
        'session': session,
        'sections': sections,
    })
```

- [ ] **Step 4: `admin_oneone_detail.html` を作成**

```html
{% extends 'reports/admin_base.html' %}
{% block admin_content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h4 class="mb-1">{{ session.member.name }} の1on1</h4>
    <small class="text-secondary">{{ session.conducted_at }} ／ 担当: {{ session.interviewer.name }}</small>
  </div>
  <a href="{% url 'admin_oneone_member' user_id=session.member.id %}" class="btn btn-sm btn-outline-secondary">← 履歴一覧</a>
</div>

{% if messages %}
  {% for message in messages %}
    <div class="alert alert-success alert-dismissible py-2">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>
  {% endfor %}
{% endif %}

<form method="post">
  {% csrf_token %}
  {% for section_key, answers in sections.items %}
  <div class="mb-4">
    <h6 class="text-warning">■ {{ section_key.0 }}. {{ section_key.1 }}</h6>
    {% for answer in answers %}
    <div class="mb-3">
      <label class="form-label text-light">
        {{ answer.question.question_text }}
        {% if answer.question.hint_text %}
          <span class="text-secondary small ms-2">（{{ answer.question.hint_text }}）</span>
        {% endif %}
      </label>
      <textarea
        name="answer_{{ answer.id }}"
        class="form-control bg-dark text-light border-secondary"
        rows="3"
      >{{ answer.text }}</textarea>
    </div>
    {% endfor %}
  </div>
  {% endfor %}
  <button type="submit" class="btn btn-primary">保存</button>
</form>
{% endblock %}
```

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.AdminOneOnOneDetailViewTest
```

Expected: `Ran 4 tests in ...s OK`

- [ ] **Step 6: コミット**

```bash
git add reports/views_admin.py reports/tests.py templates/reports/admin_oneone_detail.html
git commit -m "feat: add admin 1on1 session detail view"
```

---

## Task 8: メンバービューとテンプレート

**Files:**
- Modify: `reports/views.py`
- Modify: `reports/tests.py`
- Create: `templates/reports/oneone_member_list.html`
- Create: `templates/reports/oneone_member_detail.html`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
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
        self.assertRedirects(response, '/accounts/login/?next=/oneone/')

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
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.MemberOneOnOneViewTest
```

Expected: `AttributeError: module 'reports.views' has no attribute 'oneone_member_list_view'`

- [ ] **Step 3: ビューを実装**

`reports/views.py` の末尾に追加:

```python
@login_required
def oneone_member_list_view(request):
    from .models import OneOnOneSession
    sessions = OneOnOneSession.objects.filter(
        member=request.user
    ).select_related('interviewer').order_by('-conducted_at')
    return render(request, 'reports/oneone_member_list.html', {'sessions': sessions})


@login_required
def oneone_member_detail_view(request, session_id):
    from .models import OneOnOneSession
    session = get_object_or_404(OneOnOneSession, id=session_id)
    if session.member != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden('アクセス権限がありません')

    answers = session.answers.select_related('question').order_by(
        'question__section_number', 'question__order'
    )
    sections = {}
    for answer in answers:
        q = answer.question
        key = (q.section_number, q.section_title)
        sections.setdefault(key, []).append(answer)

    return render(request, 'reports/oneone_member_detail.html', {
        'session': session,
        'sections': sections,
    })
```

- [ ] **Step 4: `oneone_member_list.html` を作成**

```html
{% extends 'base.html' %}
{% block title %}1on1 履歴 - 週報システム{% endblock %}
{% block content %}
<h4 class="mb-4">あなたの1on1 履歴</h4>

{% if sessions %}
<table class="table table-hover">
  <thead>
    <tr>
      <th>実施日</th>
      <th>担当管理者</th>
    </tr>
  </thead>
  <tbody>
    {% for session in sessions %}
    <tr>
      <td><a href="{% url 'oneone_member_detail' session_id=session.id %}">{{ session.conducted_at }}</a></td>
      <td class="text-secondary">{{ session.interviewer.name }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
<p class="text-secondary">まだ1on1の記録がありません。</p>
{% endif %}

<div class="mt-3">
  <a href="{% url 'home' %}" class="text-secondary small">← ホームに戻る</a>
</div>
{% endblock %}
```

- [ ] **Step 5: `oneone_member_detail.html` を作成**

```html
{% extends 'base.html' %}
{% block title %}1on1 詳細 - 週報システム{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <div>
    <h4 class="mb-1">1on1 記録</h4>
    <small class="text-secondary">{{ session.conducted_at }} ／ 担当: {{ session.interviewer.name }}</small>
  </div>
  <a href="{% url 'oneone_member_list' %}" class="btn btn-sm btn-outline-secondary">← 一覧に戻る</a>
</div>

{% for section_key, answers in sections.items %}
<div class="mb-4">
  <h6 class="text-warning">■ {{ section_key.0 }}. {{ section_key.1 }}</h6>
  {% for answer in answers %}
  <div class="mb-3">
    <div class="text-secondary small mb-1">
      {{ answer.question.question_text }}
      {% if answer.question.hint_text %}
        <span class="ms-2 opacity-50">（{{ answer.question.hint_text }}）</span>
      {% endif %}
    </div>
    <div class="border border-secondary rounded p-2 text-light" style="background:#1a1a2e;min-height:2.5rem">
      {{ answer.text|default:"—" }}
    </div>
  </div>
  {% endfor %}
</div>
{% endfor %}
{% endblock %}
```

- [ ] **Step 6: テストを実行してパスを確認**

```
python manage.py test reports.tests.MemberOneOnOneViewTest
```

Expected: `Ran 6 tests in ...s OK`

- [ ] **Step 7: コミット**

```bash
git add reports/views.py reports/tests.py templates/reports/oneone_member_list.html templates/reports/oneone_member_detail.html
git commit -m "feat: add member 1on1 list and detail views"
```

---

## Task 9: ナビゲーション変更

**Files:**
- Modify: `templates/reports/admin_base.html`
- Modify: `templates/reports/home.html`
- Modify: `reports/tests.py`

- [ ] **Step 1: テストを書く**

`reports/tests.py` に追加:

```python
class NavigationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='admin6@test.com', password='pass', name='Admin6', is_admin=True
        )
        self.member = User.objects.create_user(
            email='member6@test.com', password='pass', name='Member6'
        )

    def test_admin_nav_has_oneone_link(self):
        self.client.login(email='admin6@test.com', password='pass')
        response = self.client.get('/mgmt/status/')
        self.assertContains(response, 'admin_oneone_list')

    def test_home_has_oneone_link_for_member(self):
        self.client.login(email='member6@test.com', password='pass')
        response = self.client.get('/')
        self.assertContains(response, 'oneone_member_list')
```

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.NavigationTest
```

Expected: `AssertionError: b'admin_oneone_list' not found in response`

- [ ] **Step 3: 管理者ナビに1on1タブを追加**

`templates/reports/admin_base.html` の `</nav>` の直前（「ユーザー管理」リンクの後）に追加:

```html
  <a class="nav-link {% if request.resolver_match.url_name == 'admin_oneone_list' or request.resolver_match.url_name == 'admin_oneone_new' or request.resolver_match.url_name == 'admin_oneone_detail' or request.resolver_match.url_name == 'admin_oneone_member' or request.resolver_match.url_name == 'admin_oneone_questions' %}active bg-primary{% else %}text-secondary border border-secondary{% endif %}"
     href="{% url 'admin_oneone_list' %}">1on1</a>
```

- [ ] **Step 4: ホーム画面に1on1リンクを追加**

`templates/reports/home.html` の `{% endblock %}` の直前（凡例 `div` の後）に追加:

```html
<div class="mt-4">
  <a href="{% url 'oneone_member_list' %}" class="text-secondary">1on1の記録を見る →</a>
</div>
```

- [ ] **Step 5: テストを実行してパスを確認**

```
python manage.py test reports.tests.NavigationTest
```

Expected: `Ran 2 tests in ...s OK`

- [ ] **Step 6: 全テストを実行して回帰がないことを確認**

```
python manage.py test reports
```

Expected: `OK` （全テストがパスすること）

- [ ] **Step 7: コミット**

```bash
git add templates/reports/admin_base.html templates/reports/home.html reports/tests.py
git commit -m "feat: add 1on1 navigation links to admin nav and home page"
```
