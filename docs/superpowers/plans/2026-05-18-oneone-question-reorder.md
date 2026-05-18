# 1on1質問並び替え機能 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理者が1on1質問管理画面でドラッグ&ドロップにより質問の表示順を変更できるようにする

**Architecture:** `admin_oneone_questions_view` に `action=reorder` POSTハンドラを追加し、JSONレスポンスを返す。テンプレートに SortableJS（CDN）を追加し、ドロップ時に fetch でサーバーへ新順序を送信する。

**Tech Stack:** Django 4.x、SortableJS 1.x（CDN）、Vanilla JS（fetch API）

---

## ファイル構成

**変更ファイル:**
- `reports/views_admin.py` — `action=reorder` ハンドラ追加（JsonResponse返却）
- `templates/reports/admin_oneone_questions.html` — SortableJS追加、ドラッグハンドル、JS実装
- `reports/tests.py` — `AdminOneOnOneReorderTest` クラス追加

---

## Task 1: reorder ハンドラとテンプレート更新

**Files:**
- Modify: `reports/views_admin.py`（`admin_oneone_questions_view` の POST 分岐に追記）
- Modify: `templates/reports/admin_oneone_questions.html`
- Modify: `reports/tests.py`

---

- [ ] **Step 1: テストを書く（失敗するはず）**

`reports/tests.py` の `AdminOneOnOneQuestionsViewTest` クラスの後に以下を追加:

```python
class AdminOneOnOneReorderTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            email='adminR@test.com', password='pass', name='AdminR', is_admin=True
        )
        self.client.login(email='adminR@test.com', password='pass')
        self.q1 = OneOnOneQuestion.objects.filter(section_number=1, order=1).first()
        self.q2 = OneOnOneQuestion.objects.filter(section_number=1, order=2).first()
        self.q3 = OneOnOneQuestion.objects.filter(section_number=1, order=3).first()

    def test_reorder_updates_order(self):
        response = self.client.post('/mgmt/oneone/questions/', {
            'action': 'reorder',
            'question_ids': f'{self.q3.id},{self.q1.id},{self.q2.id}',
        })
        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'ok')
        self.q3.refresh_from_db()
        self.q1.refresh_from_db()
        self.q2.refresh_from_db()
        self.assertEqual(self.q3.order, 1)
        self.assertEqual(self.q1.order, 2)
        self.assertEqual(self.q2.order, 3)

    def test_reorder_requires_admin(self):
        self.client.logout()
        User.objects.create_user(
            email='memberR@test.com', password='pass', name='MemberR'
        )
        self.client.login(email='memberR@test.com', password='pass')
        response = self.client.post('/mgmt/oneone/questions/', {
            'action': 'reorder',
            'question_ids': f'{self.q1.id},{self.q2.id}',
        })
        self.assertEqual(response.status_code, 403)
```

---

- [ ] **Step 2: テストを実行して失敗を確認**

```
python manage.py test reports.tests.AdminOneOnOneReorderTest
```

Expected: `test_reorder_updates_order` が失敗（`action=reorder` は現在リダイレクトを返す）

---

- [ ] **Step 3: `action=reorder` ハンドラを実装**

`reports/views_admin.py` の `admin_oneone_questions_view` 内、`elif action == 'toggle':` ブロックの直後（`return redirect(...)` の前）に追加:

```python
        elif action == 'reorder':
            from django.http import JsonResponse
            question_ids = request.POST.get('question_ids', '')
            id_list = [x.strip() for x in question_ids.split(',') if x.strip().isdigit()]
            for index, qid in enumerate(id_list):
                OneOnOneQuestion.objects.filter(id=int(qid)).update(order=index + 1)
            return JsonResponse({'status': 'ok'})
```

変更後の `if request.method == 'POST':` ブロック全体:

```python
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            form = OneOnOneQuestionForm(request.POST)
            if form.is_valid():
                q = form.save(commit=False)
                q.section_title = form.get_section_title()
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
        elif action == 'reorder':
            from django.http import JsonResponse
            question_ids = request.POST.get('question_ids', '')
            id_list = [x.strip() for x in question_ids.split(',') if x.strip().isdigit()]
            for index, qid in enumerate(id_list):
                OneOnOneQuestion.objects.filter(id=int(qid)).update(order=index + 1)
            return JsonResponse({'status': 'ok'})
        return redirect('admin_oneone_questions')
```

---

- [ ] **Step 4: テストを実行してパスを確認**

```
python manage.py test reports.tests.AdminOneOnOneReorderTest
```

Expected: `Ran 2 tests in ...s OK`

---

- [ ] **Step 5: テンプレートを更新**

`templates/reports/admin_oneone_questions.html` を以下の内容に全体置き換え:

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
    <tbody id="sortable-{{ section_key.0 }}">
      {% for q in items %}
      <tr class="{% if not q.is_active %}opacity-50{% endif %}" data-question-id="{{ q.id }}">
        <td class="drag-handle" style="cursor:grab;color:#555;width:20px;user-select:none">⠿</td>
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

<script src="https://cdn.jsdelivr.net/npm/sortablejs@1/Sortable.min.js"></script>
<script>
(function () {
  var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

  document.querySelectorAll('[id^="sortable-"]').forEach(function (tbody) {
    Sortable.create(tbody, {
      handle: '.drag-handle',
      animation: 150,
      onEnd: function () {
        var ids = Array.from(tbody.querySelectorAll('tr')).map(function (tr) {
          return tr.dataset.questionId;
        });
        var body = new URLSearchParams();
        body.append('action', 'reorder');
        body.append('question_ids', ids.join(','));
        body.append('csrfmiddlewaretoken', csrfToken);
        fetch('', { method: 'POST', body: body });
      }
    });
  });
}());
</script>
{% endblock %}
```

---

- [ ] **Step 6: 全テストを実行して回帰がないことを確認**

```
python manage.py test reports
```

Expected: `Ran 35 tests in ...s OK`

---

- [ ] **Step 7: コミット**

```
git add reports/views_admin.py templates/reports/admin_oneone_questions.html reports/tests.py
git commit -m "feat: add drag-and-drop reordering for 1on1 questions"
```
