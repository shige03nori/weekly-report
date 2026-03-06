# 週報システム Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 社内向け週報提出・管理Webアプリ（Django + PostgreSQL + AWS EC2）を構築する。

**Architecture:** Djangoのカスタムユーザーモデル（メールアドレスをID）で認証し、カレンダーUIから週を選んで週報を提出する。Q1は固定テーブル形式（前回値プリセット）、Q2以降は管理者がブラウザ上で動的追加可能なフォームセクション。管理者は提出状況・集計・質問管理・ユーザー管理を専用画面から行う。

**Tech Stack:** Python 3.12, Django 5.x, PostgreSQL 16 (開発時はSQLite), Bootstrap 5, Gunicorn, Nginx, AWS EC2 + RDS

---

## Task 1: Djangoプロジェクトのセットアップ

**Files:**
- Create: `requirements.txt`
- Create: `weekly_report/settings.py` (Django設定)
- Create: `weekly_report/settings_local.py` (ローカル開発用)
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: 仮想環境の作成と依存パッケージのインストール**

```bash
cd C:\Users\shige\weekly-report
python -m venv venv
venv\Scripts\activate   # Windows
pip install django psycopg2-binary python-dotenv gunicorn
pip freeze > requirements.txt
```

**Step 2: Djangoプロジェクトの初期化**

```bash
django-admin startproject weekly_report .
```

**Step 3: `.gitignore` を作成**

```
venv/
__pycache__/
*.pyc
.env
db.sqlite3
staticfiles/
```

**Step 4: `.env.example` を作成**

```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

**Step 5: `weekly_report/settings.py` を編集**

`settings.py` の末尾に追記:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

# Database
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
    )
}

AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

LANGUAGE_CODE = 'ja'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

**Step 6: `requirements.txt` に `dj-database-url` を追加**

```bash
pip install dj-database-url
pip freeze > requirements.txt
```

**Step 7: 動作確認**

```bash
python manage.py check
```
Expected: `System check identified no issues (0 silenced).`

**Step 8: コミット**

```bash
git add .
git commit -m "chore: initialize Django project with settings"
```

---

## Task 2: カスタムユーザーモデル

**Files:**
- Create: `accounts/models.py`
- Create: `accounts/admin.py`
- Create: `tests/test_accounts.py`
- Modify: `weekly_report/settings.py`

**Step 1: accountsアプリを作成**

```bash
python manage.py startapp accounts
```

`weekly_report/settings.py` の `INSTALLED_APPS` に `'accounts'` を追加。

**Step 2: テストを書く**

`tests/test_accounts.py`:

```python
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
```

**Step 3: テストが失敗することを確認**

```bash
pip install pytest pytest-django
```

`conftest.py` をプロジェクトルートに作成:
```python
import django
from django.conf import settings

def pytest_configure():
    settings.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth', 'accounts'],
        AUTH_USER_MODEL='accounts.User',
    )
```

実際には `pytest.ini` を使う方が良い:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = weekly_report.settings
```

```bash
pytest tests/test_accounts.py -v
```
Expected: FAIL (User model not defined)

**Step 4: カスタムユーザーモデルを実装**

`accounts/models.py`:

```python
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='メールアドレス')
    name = models.CharField(max_length=100, verbose_name='氏名')
    is_admin = models.BooleanField(default=False, verbose_name='管理者')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'

    def __str__(self):
        return f'{self.name} ({self.email})'
```

**Step 5: マイグレーション**

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

**Step 6: テストが通ることを確認**

```bash
pytest tests/test_accounts.py -v
```
Expected: 3 tests PASS

**Step 7: コミット**

```bash
git add accounts/ tests/test_accounts.py conftest.py pytest.ini
git commit -m "feat: add custom User model with email as login ID"
```

---

## Task 3: 認証画面（ログイン・ログアウト・パスワード変更）

**Files:**
- Create: `accounts/views.py`
- Create: `accounts/urls.py`
- Create: `accounts/forms.py`
- Create: `templates/base.html`
- Create: `templates/accounts/login.html`
- Create: `templates/accounts/password_change.html`
- Create: `tests/test_auth.py`
- Modify: `weekly_report/urls.py`
- Modify: `weekly_report/settings.py`

**Step 1: テストを書く**

`tests/test_auth.py`:

```python
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
        'new_password1': 'newpass456!',
        'new_password2': 'newpass456!',
    })
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password('newpass456!')
```

**Step 2: テストが失敗することを確認**

```bash
pytest tests/test_auth.py -v
```
Expected: FAIL

**Step 3: `accounts/views.py` を実装**

```python
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', '/'))
    elif request.method == 'POST':
        messages.error(request, 'メールアドレスまたはパスワードが正しくありません')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def password_change_view(request):
    form = PasswordChangeForm(request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'パスワードを変更しました')
        return redirect('home')
    return render(request, 'accounts/password_change.html', {'form': form})
```

**Step 4: `accounts/urls.py` を作成**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password/change/', views.password_change_view, name='password_change'),
]
```

**Step 5: `weekly_report/urls.py` に追加**

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
]
```

**Step 6: テンプレートの設定**

`weekly_report/settings.py` の `TEMPLATES` の `DIRS` を修正:
```python
'DIRS': [BASE_DIR / 'templates'],
```

`templates/base.html` を作成:

```html
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}週報システム{% endblock %}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
{% if user.is_authenticated %}
<nav class="navbar navbar-expand-lg navbar-dark bg-primary">
  <div class="container">
    <a class="navbar-brand" href="/">週報システム</a>
    <div class="ms-auto d-flex align-items-center gap-3">
      <span class="text-white">{{ user.name }}</span>
      {% if user.is_admin %}
        <a class="btn btn-outline-light btn-sm" href="{% url 'admin_status' %}">管理者画面</a>
      {% endif %}
      <a class="btn btn-outline-light btn-sm" href="{% url 'password_change' %}">PW変更</a>
      <form method="post" action="{% url 'logout' %}" class="d-inline">
        {% csrf_token %}
        <button type="submit" class="btn btn-outline-light btn-sm">ログアウト</button>
      </form>
    </div>
  </div>
</nav>
{% endif %}
<div class="container mt-4">
  {% for message in messages %}
    <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
      {{ message }}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  {% endfor %}
  {% block content %}{% endblock %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

`templates/accounts/login.html`:

```html
{% extends 'base.html' %}
{% block title %}ログイン - 週報システム{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-5">
    <div class="card shadow-sm mt-5">
      <div class="card-body p-4">
        <h4 class="card-title text-center mb-4">週報システム ログイン</h4>
        <form method="post">
          {% csrf_token %}
          <div class="mb-3">
            <label class="form-label">メールアドレス</label>
            <input type="email" name="username" class="form-control" required autofocus>
          </div>
          <div class="mb-3">
            <label class="form-label">パスワード</label>
            <input type="password" name="password" class="form-control" required>
          </div>
          {% if messages %}
            {% for message in messages %}
              <div class="alert alert-danger">{{ message }}</div>
            {% endfor %}
          {% endif %}
          <button type="submit" class="btn btn-primary w-100">ログイン</button>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

`templates/accounts/password_change.html`:

```html
{% extends 'base.html' %}
{% block title %}パスワード変更{% endblock %}
{% block content %}
<div class="row justify-content-center">
  <div class="col-md-6">
    <h3 class="mb-4">パスワード変更</h3>
    <form method="post">
      {% csrf_token %}
      {% for field in form %}
        <div class="mb-3">
          <label class="form-label">{{ field.label }}</label>
          {{ field }}
          {% if field.errors %}
            <div class="text-danger">{{ field.errors }}</div>
          {% endif %}
        </div>
      {% endfor %}
      <button type="submit" class="btn btn-primary">変更する</button>
      <a href="/" class="btn btn-secondary ms-2">キャンセル</a>
    </form>
  </div>
</div>
{% endblock %}
```

**Step 7: テストが通ることを確認**

```bash
pytest tests/test_auth.py -v
```
Expected: 6 tests PASS

**Step 8: コミット**

```bash
git add accounts/ templates/ weekly_report/urls.py
git commit -m "feat: add login, logout, password change views"
```

---

## Task 4: 週報・質問モデル

**Files:**
- Create: `reports/models.py`
- Create: `reports/apps.py`
- Create: `tests/test_models.py`
- Modify: `weekly_report/settings.py`

**Step 1: reportsアプリを作成**

```bash
python manage.py startapp reports
```

`INSTALLED_APPS` に `'reports'` を追加。

**Step 2: テストを書く**

`tests/test_models.py`:

```python
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
```

**Step 3: テストが失敗することを確認**

```bash
pytest tests/test_models.py -v
```
Expected: FAIL

**Step 4: `reports/models.py` を実装**

```python
from django.db import models
from django.conf import settings


class WeeklyReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='ユーザー',
    )
    week_start = models.DateField(verbose_name='週開始日（月曜）')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提出日時')

    class Meta:
        unique_together = ('user', 'week_start')
        verbose_name = '週報'
        verbose_name_plural = '週報'
        ordering = ['-week_start']

    def __str__(self):
        return f'{self.user.name} - {self.week_start}週'

    @property
    def is_submitted(self):
        return self.submitted_at is not None


class Q1ProjectField(models.Model):
    """Q1: プロジェクト情報（固定テーブル形式・管理者編集可）"""
    report = models.ForeignKey(WeeklyReport, on_delete=models.CASCADE, related_name='q1_fields')
    label = models.CharField(max_length=100, verbose_name='項目名')
    value = models.TextField(blank=True, verbose_name='値')
    order = models.IntegerField(default=0, verbose_name='表示順')

    class Meta:
        ordering = ['order']
        verbose_name = 'Q1フィールド'


class Q1FieldTemplate(models.Model):
    """Q1の項目テンプレート（管理者が編集する）"""
    label = models.CharField(max_length=100, verbose_name='項目名')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['order']
        verbose_name = 'Q1テンプレート'

    def __str__(self):
        return self.label


class QuestionSection(models.Model):
    SECTION_TYPES = [
        ('radio_matrix', 'ラジオマトリクス'),
        ('free_text', '自由記述'),
        ('select', '選択式'),
    ]
    title = models.CharField(max_length=200, verbose_name='セクションタイトル')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, verbose_name='タイプ')
    scale_labels = models.JSONField(default=list, blank=True, verbose_name='選択肢ラベル')
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='プレースホルダー')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['order']
        verbose_name = '質問セクション'
        verbose_name_plural = '質問セクション'

    def __str__(self):
        return self.title


class QuestionItem(models.Model):
    """ラジオマトリクスの各行"""
    section = models.ForeignKey(QuestionSection, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=200, verbose_name='項目名')
    order = models.IntegerField(default=0, verbose_name='表示順')

    class Meta:
        ordering = ['order']
        verbose_name = '質問項目'

    def __str__(self):
        return f'{self.section.title} - {self.label}'


class Answer(models.Model):
    """動的Qセクションへの回答"""
    report = models.ForeignKey(WeeklyReport, on_delete=models.CASCADE, related_name='answers')
    question_section = models.ForeignKey(QuestionSection, on_delete=models.CASCADE)
    question_item = models.ForeignKey(
        QuestionItem, on_delete=models.CASCADE, null=True, blank=True
    )
    value = models.TextField(blank=True, verbose_name='回答値')

    class Meta:
        verbose_name = '回答'
```

**Step 5: マイグレーション**

```bash
python manage.py makemigrations reports
python manage.py migrate
```

**Step 6: テストが通ることを確認**

```bash
pytest tests/test_models.py -v
```
Expected: 4 tests PASS

**Step 7: コミット**

```bash
git add reports/ tests/test_models.py
git commit -m "feat: add WeeklyReport, QuestionSection, Answer models"
```

---

## Task 5: 初期データ（プリセット質問セクション）

**Files:**
- Create: `reports/fixtures/initial_questions.json`
- Create: `reports/management/commands/init_data.py`

**Step 1: 管理コマンドを作成**

`reports/management/__init__.py` と `reports/management/commands/__init__.py` を作成（空ファイル）。

`reports/management/commands/init_data.py`:

```python
from django.core.management.base import BaseCommand
from reports.models import QuestionSection, QuestionItem, Q1FieldTemplate


class Command(BaseCommand):
    help = '初期質問データを投入する'

    def handle(self, *args, **options):
        # Q1テンプレート
        q1_fields = [
            'プロジェクト名', '商流', '参加フェーズ', '使用技術', '使用ツール',
            '実施中のタスク１（状況）', '実施中のタスク２（状況）', '実施中のタスク３（状況）',
        ]
        for i, label in enumerate(q1_fields):
            Q1FieldTemplate.objects.get_or_create(label=label, defaults={'order': i + 1})

        # Q2: 現在のあなたの状態
        q2, _ = QuestionSection.objects.get_or_create(
            title='Q2 現在のあなたの状態について教えてください',
            defaults={
                'section_type': 'radio_matrix',
                'scale_labels': ['非常に問題', '少し問題', '普通', '良い状態', '非常に良い状態'],
                'order': 2,
            }
        )
        for i, label in enumerate(['稼働時間', '仕事の人間関係', '健康状態', '精神状態']):
            QuestionItem.objects.get_or_create(section=q2, label=label, defaults={'order': i + 1})

        # Q3: 現場の状況
        q3, _ = QuestionSection.objects.get_or_create(
            title='Q3 現場の状況について教えてください',
            defaults={
                'section_type': 'radio_matrix',
                'scale_labels': ['いいえ', 'ややいいえ', 'ややはい', 'はい'],
                'order': 3,
            }
        )
        for i, label in enumerate([
            'タスクの量は安定している', 'タスクの難易度は丁度よい',
            '増員の話を聞いている', '減員の話を聞いている', '現場で営業情報を収集している',
        ]):
            QuestionItem.objects.get_or_create(section=q3, label=label, defaults={'order': i + 1})

        # Q4: 今週の残業時間
        QuestionSection.objects.get_or_create(
            title='Q4 今週の残業時間',
            defaults={
                'section_type': 'select',
                'scale_labels': ['0h', '〜10h', '10〜20h', '20h超'],
                'order': 4,
            }
        )

        # Q5: 来週の予定タスク
        QuestionSection.objects.get_or_create(
            title='Q5 来週の予定タスク',
            defaults={
                'section_type': 'free_text',
                'placeholder': '決まっていれば',
                'order': 5,
            }
        )

        # Q6: スキルアップ・学習したこと
        QuestionSection.objects.get_or_create(
            title='Q6 スキルアップ・学習したこと',
            defaults={'section_type': 'free_text', 'order': 6}
        )

        # Q7: ハラスメント・困りごと
        QuestionSection.objects.get_or_create(
            title='Q7 ハラスメント・困りごとの有無',
            defaults={'section_type': 'free_text', 'order': 7}
        )

        # Q8: その他
        QuestionSection.objects.get_or_create(
            title='Q8 その他・共有や相談事項',
            defaults={'section_type': 'free_text', 'order': 8}
        )

        self.stdout.write(self.style.SUCCESS('初期データを投入しました'))
```

**Step 2: 初期データを投入**

```bash
python manage.py init_data
```
Expected: `初期データを投入しました`

**Step 3: コミット**

```bash
git add reports/management/ reports/fixtures/
git commit -m "feat: add initial question data seeder command"
```

---

## Task 6: カレンダー画面（ホーム）

**Files:**
- Create: `reports/views.py`（home_view）
- Create: `reports/urls.py`
- Create: `templates/reports/home.html`
- Create: `tests/test_calendar.py`
- Modify: `weekly_report/urls.py`

**Step 1: テストを書く**

`tests/test_calendar.py`:

```python
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
```

**Step 2: テストが失敗することを確認**

```bash
pytest tests/test_calendar.py -v
```
Expected: FAIL

**Step 3: `reports/utils.py` を作成**

```python
from datetime import date, timedelta


def today():
    return date.today()


def get_week_start(d: date) -> date:
    """その日の週の月曜日を返す"""
    return d - timedelta(days=d.weekday())


def is_editable_week(week_start: date) -> bool:
    """過去2週間以内かつ未来ではない週のみ編集可能"""
    current_week = get_week_start(today())
    two_weeks_ago = current_week - timedelta(weeks=2)
    return two_weeks_ago <= week_start <= current_week
```

**Step 4: `reports/views.py` に home_view を追加**

```python
from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import WeeklyReport
from .utils import get_week_start, is_editable_week, today as get_today


@login_required
def home_view(request):
    # 表示月を決定（GETパラメータで prev/next 対応）
    today = get_today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # その月の全週を計算
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # 月の最初の月曜日から最後の週まで収集
    week_start = get_week_start(first_day)
    weeks = []
    while week_start <= last_day:
        weeks.append(week_start)
        week_start += timedelta(weeks=1)

    # 提出済み週報を取得
    submitted_weeks = set(
        WeeklyReport.objects.filter(
            user=request.user,
            week_start__in=weeks,
            submitted_at__isnull=False,
        ).values_list('week_start', flat=True)
    )

    current_week = get_week_start(today)

    weeks_data = []
    for ws in weeks:
        status = 'submitted' if ws in submitted_weeks else (
            'future' if ws > current_week else (
                'editable' if is_editable_week(ws) else 'past'
            )
        )
        weeks_data.append({'week_start': ws, 'status': status})

    # 前月・次月のナビゲーション
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return render(request, 'reports/home.html', {
        'weeks': weeks_data,
        'year': year,
        'month': month,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'current_week': current_week,
    })
```

**Step 5: `reports/urls.py` を作成**

```python
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
]
```

**Step 6: `weekly_report/urls.py` に追加**

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('', include('reports.urls')),
]
```

**Step 7: `templates/reports/home.html` を作成**

```html
{% extends 'base.html' %}
{% block title %}ホーム - 週報システム{% endblock %}
{% block content %}
<div class="d-flex align-items-center mb-3 gap-3">
  <a href="?year={{ prev_year }}&month={{ prev_month }}" class="btn btn-outline-secondary btn-sm">◀</a>
  <h4 class="mb-0">{{ year }}年 {{ month }}月</h4>
  <a href="?year={{ next_year }}&month={{ next_month }}" class="btn btn-outline-secondary btn-sm">▶</a>
</div>

<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
{% for week in weeks %}
  {% if week.status == 'submitted' %}
    <div class="col">
      <a href="/report/{{ week.week_start }}/" class="text-decoration-none">
        <div class="card border-success bg-success bg-opacity-10">
          <div class="card-body text-center">
            <div class="fw-bold text-success">{{ week.week_start }} 〜</div>
            <small class="text-success">✓ 提出済み</small>
          </div>
        </div>
      </a>
    </div>
  {% elif week.status == 'editable' %}
    <div class="col">
      <a href="/report/{{ week.week_start }}/" class="text-decoration-none">
        <div class="card border-warning bg-warning bg-opacity-10 {% if week.week_start == current_week %}border-3{% endif %}">
          <div class="card-body text-center">
            <div class="fw-bold">{{ week.week_start }} 〜</div>
            <small class="text-danger">未提出</small>
          </div>
        </div>
      </a>
    </div>
  {% elif week.status == 'past' %}
    <div class="col">
      <div class="card border-danger bg-danger bg-opacity-10">
        <div class="card-body text-center">
          <div class="fw-bold text-muted">{{ week.week_start }} 〜</div>
          <small class="text-danger">期限切れ</small>
        </div>
      </div>
    </div>
  {% else %}
    <div class="col">
      <div class="card bg-light border-0">
        <div class="card-body text-center">
          <div class="text-muted">{{ week.week_start }} 〜</div>
          <small class="text-muted">まだ提出できません</small>
        </div>
      </div>
    </div>
  {% endif %}
{% endfor %}
</div>
{% endblock %}
```

**Step 8: テストが通ることを確認**

```bash
pytest tests/test_calendar.py -v
```
Expected: 9 tests PASS

**Step 9: コミット**

```bash
git add reports/ templates/reports/ tests/test_calendar.py
git commit -m "feat: add calendar home view with weekly report status"
```

---

## Task 7: 週報入力・提出・閲覧

**Files:**
- Create: `reports/forms.py`
- Modify: `reports/views.py`（report_view, report_readonly_view）
- Create: `templates/reports/report_form.html`
- Create: `templates/reports/report_view.html`
- Create: `tests/test_report_form.py`
- Modify: `reports/urls.py`

**Step 1: テストを書く**

`tests/test_report_form.py`:

```python
import pytest
from datetime import date
from django.urls import reverse
from django.contrib.auth import get_user_model
from reports.models import WeeklyReport, QuestionSection, QuestionItem, Q1FieldTemplate

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email='u@test.com', password='pass', name='テスト')


@pytest.fixture
def q1_template(db):
    Q1FieldTemplate.objects.create(label='プロジェクト名', order=1)
    Q1FieldTemplate.objects.create(label='商流', order=2)


@pytest.fixture
def section(db):
    s = QuestionSection.objects.create(
        title='Q2 状態', section_type='radio_matrix',
        scale_labels=['普通', '良い'], order=2,
    )
    QuestionItem.objects.create(section=s, label='稼働時間', order=1)
    return s


@pytest.mark.django_db
def test_report_form_get(client, user, q1_template, section):
    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('report_form', args=['2026-03-02']))
    assert response.status_code == 200


@pytest.mark.django_db
def test_report_submit(client, user, q1_template, section):
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


@pytest.mark.django_db
def test_report_prefill_q1_from_previous(client, user, q1_template):
    """Q1は直前の週報の値をデフォルト表示する"""
    # 前週の週報を作成
    prev_report = WeeklyReport.objects.create(
        user=user, week_start=date(2026, 2, 23)
    )
    from reports.models import Q1ProjectField
    Q1ProjectField.objects.create(report=prev_report, label='プロジェクト名', value='前回のプロジェクト', order=1)
    prev_report.submitted_at = date(2026, 2, 23)
    prev_report.save()

    client.login(username='u@test.com', password='pass')
    response = client.get(reverse('report_form', args=['2026-03-02']))
    assert response.status_code == 200
    assert '前回のプロジェクト' in response.content.decode()
```

**Step 2: テストが失敗することを確認**

```bash
pytest tests/test_report_form.py -v
```

**Step 3: `reports/views.py` に report_view を追加**

```python
from datetime import date, datetime
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from .models import (
    WeeklyReport, Q1ProjectField, Q1FieldTemplate,
    QuestionSection, QuestionItem, Answer
)
from .utils import is_editable_week


@login_required
def report_view(request, week_start_str):
    week_start = date.fromisoformat(week_start_str)
    editable = is_editable_week(week_start)

    report, created = WeeklyReport.objects.get_or_create(
        user=request.user, week_start=week_start
    )

    # Q1テンプレート取得
    q1_templates = Q1FieldTemplate.objects.filter(is_active=True)

    # Q1プリセット: 直前提出済み週報のQ1値
    prev_report = (
        WeeklyReport.objects.filter(
            user=request.user,
            submitted_at__isnull=False,
            week_start__lt=week_start,
        )
        .order_by('-week_start')
        .first()
    )
    prev_q1 = {}
    if prev_report:
        prev_q1 = {f.label: f.value for f in prev_report.q1_fields.all()}

    # 現在のQ1値（既存回答があれば優先）
    current_q1 = {f.label: f.value for f in report.q1_fields.all()}
    q1_defaults = {t.label: current_q1.get(t.label, prev_q1.get(t.label, '')) for t in q1_templates}

    # 動的Q セクション
    sections = QuestionSection.objects.filter(is_active=True)
    current_answers = {
        (a.question_section_id, a.question_item_id): a.value
        for a in report.answers.all()
    }

    if request.method == 'POST' and editable:
        # Q1保存
        report.q1_fields.all().delete()
        for t in q1_templates:
            Q1ProjectField.objects.create(
                report=report,
                label=t.label,
                value=request.POST.get(f'q1_{t.label}', ''),
                order=t.order,
            )

        # 動的Q保存
        report.answers.all().delete()
        for section in sections:
            if section.section_type == 'radio_matrix':
                for item in section.items.all():
                    val = request.POST.get(f'answer_{section.id}_{item.id}', '')
                    if val:
                        Answer.objects.create(
                            report=report,
                            question_section=section,
                            question_item=item,
                            value=val,
                        )
            else:
                val = request.POST.get(f'answer_{section.id}', '')
                Answer.objects.create(
                    report=report,
                    question_section=section,
                    value=val,
                )

        if request.POST.get('action') == 'submit':
            report.submitted_at = datetime.now()
            report.save()
            messages.success(request, '週報を提出しました')
        else:
            messages.success(request, '下書きを保存しました')

        return redirect('home')

    if not editable and report.is_submitted:
        return redirect('report_readonly', week_start_str=week_start_str)

    return render(request, 'reports/report_form.html', {
        'report': report,
        'week_start': week_start,
        'editable': editable,
        'q1_templates': q1_templates,
        'q1_defaults': q1_defaults,
        'sections': sections,
        'current_answers': current_answers,
    })


@login_required
def report_readonly_view(request, week_start_str):
    week_start = date.fromisoformat(week_start_str)
    report = get_object_or_404(WeeklyReport, user=request.user, week_start=week_start)
    sections = QuestionSection.objects.filter(is_active=True)
    answers = {
        (a.question_section_id, a.question_item_id): a.value
        for a in report.answers.all()
    }
    return render(request, 'reports/report_view.html', {
        'report': report,
        'week_start': week_start,
        'sections': sections,
        'answers': answers,
    })
```

**Step 4: `reports/urls.py` に追加**

```python
urlpatterns = [
    path('', views.home_view, name='home'),
    path('report/<str:week_start_str>/', views.report_view, name='report_form'),
    path('report/<str:week_start_str>/view/', views.report_readonly_view, name='report_readonly'),
]
```

**Step 5: `templates/reports/report_form.html` を作成**

```html
{% extends 'base.html' %}
{% block title %}週報入力 - {{ week_start }}{% endblock %}
{% block content %}
<h3>週報 {{ week_start }} 〜</h3>
{% if not editable %}
  <div class="alert alert-warning">この週は編集できません（提出期限を過ぎています）</div>
{% endif %}
<form method="post">
  {% csrf_token %}

  {# Q1: プロジェクト情報 #}
  <div class="card mb-4">
    <div class="card-header bg-light fw-bold">Q1 現場について教えてください</div>
    <div class="card-body">
      <table class="table table-bordered">
        <thead><tr><th>項目</th><th>回答</th></tr></thead>
        <tbody>
        {% for t in q1_templates %}
          <tr>
            <td class="fw-bold">{{ t.label }}</td>
            <td>
              {% if editable %}
                <input type="text" name="q1_{{ t.label }}" class="form-control"
                       value="{{ q1_defaults|get_item:t.label }}">
              {% else %}
                {{ q1_defaults|get_item:t.label }}
              {% endif %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  {# 動的Qセクション #}
  {% for section in sections %}
  <div class="card mb-4">
    <div class="card-header bg-light fw-bold">{{ section.title }}</div>
    <div class="card-body">
      {% if section.section_type == 'radio_matrix' %}
        <table class="table table-bordered">
          <thead>
            <tr>
              <th>項目</th>
              {% for label in section.scale_labels %}
                <th class="text-center">{{ label }}</th>
              {% endfor %}
            </tr>
          </thead>
          <tbody>
          {% for item in section.items.all %}
            <tr>
              <td>{{ item.label }}</td>
              {% for label in section.scale_labels %}
                <td class="text-center">
                  {% if editable %}
                    <input type="radio" name="answer_{{ section.id }}_{{ item.id }}"
                           value="{{ label }}"
                           {% if current_answers|get_item:section.id|get_item:item.id == label %}checked{% endif %}>
                  {% else %}
                    {% if current_answers|get_item:section.id|get_item:item.id == label %}○{% endif %}
                  {% endif %}
                </td>
              {% endfor %}
            </tr>
          {% endfor %}
          </tbody>
        </table>
      {% elif section.section_type == 'select' %}
        <select name="answer_{{ section.id }}" class="form-select" {% if not editable %}disabled{% endif %}>
          <option value="">選択してください</option>
          {% for label in section.scale_labels %}
            <option value="{{ label }}" {% if current_answers|get_item:section.id|get_item:None == label %}selected{% endif %}>
              {{ label }}
            </option>
          {% endfor %}
        </select>
      {% else %}
        <textarea name="answer_{{ section.id }}" class="form-control" rows="3"
                  placeholder="{{ section.placeholder }}" {% if not editable %}readonly{% endif %}>{{ current_answers|get_item:section.id|get_item:None }}</textarea>
      {% endif %}
    </div>
  </div>
  {% endfor %}

  {% if editable %}
  <div class="d-flex gap-2">
    <button type="submit" name="action" value="draft" class="btn btn-outline-secondary">下書き保存</button>
    <button type="submit" name="action" value="submit" class="btn btn-primary">提出する</button>
  </div>
  {% endif %}
</form>
{% endblock %}
```

**Step 6: テンプレートタグ `get_item` を作成**

`reports/templatetags/__init__.py` と `reports/templatetags/report_tags.py`:

```python
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''
```

**Step 7: テストが通ることを確認**

テンプレートの `current_answers` のキーを `(section_id, item_id)` のタプルにしているため、テンプレートタグも合わせて調整が必要。テストを実行して修正:

```bash
pytest tests/test_report_form.py -v
```
Expected: 4 tests PASS

**Step 8: コミット**

```bash
git add reports/ templates/reports/ tests/test_report_form.py
git commit -m "feat: add weekly report form with Q1 prefill and dynamic questions"
```

---

## Task 8: 管理者 - 提出状況・集計

**Files:**
- Create: `reports/views_admin.py`
- Create: `templates/reports/admin_status.html`
- Create: `templates/reports/admin_summary.html`
- Create: `tests/test_admin_views.py`
- Modify: `reports/urls.py`

**Step 1: テストを書く**

`tests/test_admin_views.py`:

```python
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
    WeeklyReport.objects.create(
        user=regular_user, week_start=date(2026, 3, 2),
        submitted_at=date(2026, 3, 3)
    )
    response = client.get(reverse('admin_status') + '?week=2026-03-02')
    assert response.status_code == 200
    assert '一般ユーザー' in response.content.decode()


def test_admin_summary(client, admin_user, regular_user):
    client.login(username='admin@test.com', password='pass')
    response = client.get(reverse('admin_summary'))
    assert response.status_code == 200
```

**Step 2: テストが失敗することを確認**

```bash
pytest tests/test_admin_views.py -v
```

**Step 3: `reports/views_admin.py` を作成**

```python
from datetime import date, timedelta
from functools import wraps
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import WeeklyReport
from .utils import get_week_start, today as get_today

User = get_user_model()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return HttpResponseForbidden('管理者権限が必要です')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_status_view(request):
    week_str = request.GET.get('week')
    selected_week = date.fromisoformat(week_str) if week_str else get_week_start(get_today())

    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    submitted_users = set(
        WeeklyReport.objects.filter(
            week_start=selected_week,
            submitted_at__isnull=False,
        ).values_list('user_id', flat=True)
    )

    users_data = [
        {'user': u, 'submitted': u.id in submitted_users}
        for u in all_users
    ]

    # 過去12週のリスト（週選択用）
    current_week = get_week_start(get_today())
    week_choices = [current_week - timedelta(weeks=i) for i in range(12)]

    return render(request, 'reports/admin_status.html', {
        'users_data': users_data,
        'selected_week': selected_week,
        'week_choices': week_choices,
    })


@admin_required
def admin_summary_view(request):
    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')

    # 全週報の提出回数を集計
    from django.db.models import Count, Q
    summary = []
    for user in all_users:
        total = WeeklyReport.objects.filter(user=user).count()
        submitted = WeeklyReport.objects.filter(user=user, submitted_at__isnull=False).count()
        summary.append({
            'user': user,
            'submitted': submitted,
            'not_submitted': total - submitted,
            'rate': round(submitted / total * 100) if total > 0 else 0,
        })

    return render(request, 'reports/admin_summary.html', {'summary': summary})


@admin_required
def admin_report_view(request, user_id, week_start_str):
    from .models import QuestionSection
    target_user = User.objects.get(id=user_id)
    week_start = date.fromisoformat(week_start_str)
    report = WeeklyReport.objects.get(user=target_user, week_start=week_start)
    sections = QuestionSection.objects.filter(is_active=True)
    answers = {
        (a.question_section_id, a.question_item_id): a.value
        for a in report.answers.all()
    }
    return render(request, 'reports/report_view.html', {
        'report': report,
        'week_start': week_start,
        'sections': sections,
        'answers': answers,
        'target_user': target_user,
    })
```

**Step 4: テンプレートを作成**

`templates/reports/admin_status.html`:

```html
{% extends 'base.html' %}
{% block title %}提出状況{% endblock %}
{% block content %}
<h3>提出状況一覧</h3>
<form method="get" class="d-flex gap-2 mb-4 align-items-center">
  <select name="week" class="form-select w-auto">
    {% for w in week_choices %}
      <option value="{{ w }}" {% if w == selected_week %}selected{% endif %}>{{ w }} 〜</option>
    {% endfor %}
  </select>
  <button class="btn btn-primary">表示</button>
</form>

<h5>{{ selected_week }} 〜 の週</h5>
<table class="table table-striped">
  <thead><tr><th>氏名</th><th>状態</th><th>週報</th></tr></thead>
  <tbody>
  {% for ud in users_data %}
    <tr>
      <td>{{ ud.user.name }}</td>
      <td>
        {% if ud.submitted %}
          <span class="badge bg-success">提出済み</span>
        {% else %}
          <span class="badge bg-danger">未提出</span>
        {% endif %}
      </td>
      <td>
        {% if ud.submitted %}
          <a href="/admin-view/{{ ud.user.id }}/{{ selected_week }}/" class="btn btn-sm btn-outline-primary">閲覧</a>
        {% endif %}
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

`templates/reports/admin_summary.html`:

```html
{% extends 'base.html' %}
{% block title %}提出率集計{% endblock %}
{% block content %}
<h3>提出率集計</h3>
<table class="table table-striped">
  <thead>
    <tr><th>氏名</th><th>提出回数</th><th>未提出回数</th><th>提出率</th></tr>
  </thead>
  <tbody>
  {% for s in summary %}
    <tr>
      <td>{{ s.user.name }}</td>
      <td>{{ s.submitted }}</td>
      <td>{{ s.not_submitted }}</td>
      <td>
        <div class="progress" style="height:20px;">
          <div class="progress-bar bg-success" style="width:{{ s.rate }}%">{{ s.rate }}%</div>
        </div>
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% endblock %}
```

**Step 5: `reports/urls.py` に追加**

```python
from . import views, views_admin

urlpatterns += [
    path('admin/status/', views_admin.admin_status_view, name='admin_status'),
    path('admin/summary/', views_admin.admin_summary_view, name='admin_summary'),
    path('admin-view/<int:user_id>/<str:week_start_str>/', views_admin.admin_report_view, name='admin_report'),
]
```

**Step 6: テストが通ることを確認**

```bash
pytest tests/test_admin_views.py -v
```
Expected: 4 tests PASS

**Step 7: コミット**

```bash
git add reports/views_admin.py templates/reports/admin_*.html tests/test_admin_views.py
git commit -m "feat: add admin status and summary views"
```

---

## Task 9: 管理者 - 質問管理・ユーザー管理

**Files:**
- Create: `reports/forms_admin.py`
- Modify: `reports/views_admin.py`
- Create: `templates/reports/admin_questions.html`
- Create: `templates/reports/admin_users.html`
- Modify: `reports/urls.py`

**Step 1: `reports/forms_admin.py` を作成**

```python
from django import forms
from django.contrib.auth import get_user_model
from .models import QuestionSection, QuestionItem, Q1FieldTemplate

User = get_user_model()


class QuestionSectionForm(forms.ModelForm):
    class Meta:
        model = QuestionSection
        fields = ['title', 'section_type', 'scale_labels', 'placeholder', 'order', 'is_active']
        widgets = {
            'scale_labels': forms.Textarea(attrs={'rows': 3, 'placeholder': '["選択肢1", "選択肢2"]'}),
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='パスワード')

    class Meta:
        model = User
        fields = ['email', 'name', 'is_admin', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
```

**Step 2: `reports/views_admin.py` に質問管理・ユーザー管理ビューを追加**

```python
from .forms_admin import QuestionSectionForm, UserCreateForm
from .models import QuestionSection, Q1FieldTemplate


@admin_required
def admin_questions_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_section':
            form = QuestionSectionForm(request.POST)
            if form.is_valid():
                form.save()
        elif action == 'toggle_active':
            section_id = request.POST.get('section_id')
            section = QuestionSection.objects.get(id=section_id)
            section.is_active = not section.is_active
            section.save()
        elif action == 'reorder':
            for key, val in request.POST.items():
                if key.startswith('order_'):
                    sid = key.replace('order_', '')
                    QuestionSection.objects.filter(id=sid).update(order=int(val))
        return redirect('admin_questions')

    sections = QuestionSection.objects.all()
    form = QuestionSectionForm()
    q1_templates = Q1FieldTemplate.objects.all()
    return render(request, 'reports/admin_questions.html', {
        'sections': sections,
        'form': form,
        'q1_templates': q1_templates,
    })


@admin_required
def admin_users_view(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザーを作成しました')
            return redirect('admin_users')
    else:
        form = UserCreateForm()

    users = User.objects.filter(is_active=True).order_by('name')
    return render(request, 'reports/admin_users.html', {'users': users, 'form': form})


@admin_required
def admin_toggle_admin_view(request, user_id):
    if request.method == 'POST':
        target = User.objects.get(id=user_id)
        target.is_admin = not target.is_admin
        target.save()
    return redirect('admin_users')
```

**Step 3: URLを追加**

```python
urlpatterns += [
    path('admin/questions/', views_admin.admin_questions_view, name='admin_questions'),
    path('admin/users/', views_admin.admin_users_view, name='admin_users'),
    path('admin/users/<int:user_id>/toggle-admin/', views_admin.admin_toggle_admin_view, name='admin_toggle_admin'),
]
```

**Step 4: テンプレートを作成**

`templates/reports/admin_questions.html`:

```html
{% extends 'base.html' %}
{% block title %}質問管理{% endblock %}
{% block content %}
<h3>質問セクション管理</h3>

<h5 class="mt-4">Q1 フィールドテンプレート</h5>
<table class="table table-bordered">
  <thead><tr><th>順序</th><th>項目名</th><th>有効</th></tr></thead>
  <tbody>
  {% for t in q1_templates %}
    <tr><td>{{ t.order }}</td><td>{{ t.label }}</td><td>{% if t.is_active %}✓{% endif %}</td></tr>
  {% endfor %}
  </tbody>
</table>

<h5 class="mt-4">動的質問セクション一覧</h5>
<form method="post">
  {% csrf_token %}
  <input type="hidden" name="action" value="reorder">
  <table class="table table-bordered">
    <thead><tr><th>順序</th><th>タイトル</th><th>タイプ</th><th>有効</th><th>操作</th></tr></thead>
    <tbody>
    {% for s in sections %}
      <tr>
        <td><input type="number" name="order_{{ s.id }}" value="{{ s.order }}" class="form-control form-control-sm" style="width:70px;"></td>
        <td>{{ s.title }}</td>
        <td>{{ s.get_section_type_display }}</td>
        <td>{% if s.is_active %}<span class="badge bg-success">有効</span>{% else %}<span class="badge bg-secondary">無効</span>{% endif %}</td>
        <td>
          <form method="post" class="d-inline">
            {% csrf_token %}
            <input type="hidden" name="action" value="toggle_active">
            <input type="hidden" name="section_id" value="{{ s.id }}">
            <button class="btn btn-sm btn-outline-secondary">切替</button>
          </form>
        </td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <button type="submit" class="btn btn-primary">順序を保存</button>
</form>

<h5 class="mt-4">新しいセクションを追加</h5>
<form method="post">
  {% csrf_token %}
  <input type="hidden" name="action" value="add_section">
  {% for field in form %}
    <div class="mb-3">
      <label class="form-label">{{ field.label }}</label>
      {{ field }}
    </div>
  {% endfor %}
  <button type="submit" class="btn btn-success">追加</button>
</form>
{% endblock %}
```

`templates/reports/admin_users.html`:

```html
{% extends 'base.html' %}
{% block title %}ユーザー管理{% endblock %}
{% block content %}
<h3>ユーザー管理</h3>

<table class="table table-striped">
  <thead><tr><th>氏名</th><th>メールアドレス</th><th>管理者</th><th>操作</th></tr></thead>
  <tbody>
  {% for u in users %}
    <tr>
      <td>{{ u.name }}</td>
      <td>{{ u.email }}</td>
      <td>{% if u.is_admin %}<span class="badge bg-warning text-dark">管理者</span>{% endif %}</td>
      <td>
        <form method="post" action="{% url 'admin_toggle_admin' u.id %}">
          {% csrf_token %}
          <button class="btn btn-sm btn-outline-secondary">
            {% if u.is_admin %}管理者解除{% else %}管理者にする{% endif %}
          </button>
        </form>
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<h5 class="mt-4">新しいユーザーを作成</h5>
<form method="post">
  {% csrf_token %}
  {% for field in form %}
    <div class="mb-3">
      <label class="form-label">{{ field.label }}</label>
      {{ field }}
      {% if field.errors %}<div class="text-danger">{{ field.errors }}</div>{% endif %}
    </div>
  {% endfor %}
  <button type="submit" class="btn btn-success">作成</button>
</form>
{% endblock %}
```

**Step 5: 動作確認**

```bash
python manage.py runserver
```

管理者アカウントを作成して各画面を確認:
```bash
python manage.py createsuperuser --email admin@example.com
python manage.py init_data
```

**Step 6: コミット**

```bash
git add reports/forms_admin.py reports/views_admin.py templates/reports/admin_*.html
git commit -m "feat: add question management and user management for admin"
```

---

## Task 10: Django Admin設定・スーパーユーザー管理

**Files:**
- Modify: `accounts/admin.py`
- Modify: `reports/admin.py`

**Step 1: `accounts/admin.py` を設定**

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'is_admin', 'is_active')
    list_filter = ('is_admin', 'is_active')
    search_fields = ('email', 'name')
    ordering = ('name',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('個人情報', {'fields': ('name',)}),
        ('権限', {'fields': ('is_admin', 'is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'name', 'password1', 'password2', 'is_admin')}),
    )
```

**Step 2: `reports/admin.py` を設定**

```python
from django.contrib import admin
from .models import WeeklyReport, QuestionSection, QuestionItem, Q1FieldTemplate


@admin.register(QuestionSection)
class QuestionSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section_type', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    inlines = []


@admin.register(Q1FieldTemplate)
class Q1FieldTemplateAdmin(admin.ModelAdmin):
    list_display = ('label', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start', 'submitted_at')
    list_filter = ('week_start',)
    search_fields = ('user__name', 'user__email')
```

**Step 3: コミット**

```bash
git add accounts/admin.py reports/admin.py
git commit -m "chore: configure Django admin for User and Report models"
```

---

## Task 11: 全テストの実行と最終確認

**Step 1: 全テストを実行**

```bash
pytest -v
```
Expected: 全テストPASS

**Step 2: 開発サーバーで動作確認**

```bash
python manage.py migrate
python manage.py init_data
python manage.py runserver
```

以下を手動確認:
- [ ] ログイン・ログアウト
- [ ] パスワード変更
- [ ] カレンダー表示（月ナビゲーション・色分け）
- [ ] 週報入力・提出（Q1前回値プリセット確認）
- [ ] 過去2週間の編集可能、3週間前は閲覧のみ
- [ ] 管理者: 提出状況一覧・集計
- [ ] 管理者: 質問追加・順序変更
- [ ] 管理者: ユーザー作成・権限変更

**Step 3: コミット**

```bash
git add .
git commit -m "chore: final cleanup and verification"
```

---

## Task 12: AWS デプロイ設定

**Files:**
- Create: `deploy/nginx.conf`
- Create: `deploy/gunicorn.service`
- Create: `deploy/setup.sh`
- Create: `weekly_report/settings_production.py`

**Step 1: `weekly_report/settings_production.py` を作成**

```python
from .settings import *

DEBUG = False
ALLOWED_HOSTS = [os.environ.get('ALLOWED_HOSTS', '')]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Step 2: `deploy/nginx.conf` を作成**

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;

    location /static/ {
        alias /home/ec2-user/weekly-report/staticfiles/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Step 3: `deploy/gunicorn.service` を作成（systemd）**

```ini
[Unit]
Description=Gunicorn daemon for weekly-report
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/weekly-report
EnvironmentFile=/home/ec2-user/weekly-report/.env
ExecStart=/home/ec2-user/weekly-report/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    weekly_report.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Step 4: `deploy/setup.sh` を作成**

```bash
#!/bin/bash
# EC2 初回セットアップスクリプト（Amazon Linux 2）

sudo yum update -y
sudo yum install -y python3 python3-pip nginx git

cd /home/ec2-user
git clone <YOUR_REPO_URL> weekly-report
cd weekly-report

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# .env を設定してから実行
cp .env.example .env
# nano .env  # 実際の値を設定

export DJANGO_SETTINGS_MODULE=weekly_report.settings_production
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py init_data

# Gunicorn をsystemdに登録
sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

# Nginx 設定
sudo cp deploy/nginx.conf /etc/nginx/conf.d/weekly-report.conf
sudo systemctl enable nginx
sudo systemctl restart nginx
```

**Step 5: コミット**

```bash
git add deploy/ weekly_report/settings_production.py
git commit -m "chore: add AWS deployment configuration"
```

---

## 完了チェックリスト

- [ ] Task 1: Djangoプロジェクトセットアップ
- [ ] Task 2: カスタムユーザーモデル
- [ ] Task 3: 認証画面（ログイン・ログアウト・PW変更）
- [ ] Task 4: 週報・質問モデル
- [ ] Task 5: 初期データ投入コマンド
- [ ] Task 6: カレンダーホーム画面
- [ ] Task 7: 週報入力・提出・閲覧
- [ ] Task 8: 管理者 - 提出状況・集計
- [ ] Task 9: 管理者 - 質問管理・ユーザー管理
- [ ] Task 10: Django Admin設定
- [ ] Task 11: 全テスト実行・動作確認
- [ ] Task 12: AWSデプロイ設定
