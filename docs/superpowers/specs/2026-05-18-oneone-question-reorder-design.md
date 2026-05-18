# 1on1質問並び替え機能 設計ドキュメント

**日付:** 2026-05-18  
**対象アプリ:** weekly-report（Django）  
**実装方針:** 既存 `admin_oneone_questions_view` と `admin_oneone_questions.html` を変更

---

## 1. 概要

管理者が1on1質問管理画面（`/mgmt/oneone/questions/`）で、各セクション内の質問の表示順をドラッグ&ドロップで変更できるようにする。

- 並び替えはセクション内のみ（セクションをまたぐ移動は不可）
- ドロップ時にAJAXで自動保存（ページリロードなし）
- SortableJS（CDN）を使用

---

## 2. データモデルへの変更

なし。既存の `OneOnOneQuestion.order` フィールド（IntegerField）を更新するだけ。

---

## 3. URL・ビュー変更

### `admin_oneone_questions_view`（`reports/views_admin.py`）

既存の `action=add` / `action=toggle` に加え、`action=reorder` を追加する。

```
POST /mgmt/oneone/questions/
  action=reorder
  question_ids=3,1,2   # セクション内の新しい順番（カンマ区切りID）
```

レスポンス: `JsonResponse({'status': 'ok'})`（リダイレクトしない）

`question_ids` を受け取り、インデックス順に各 `OneOnOneQuestion.order` を `1, 2, 3, ...` と更新する。

---

## 4. テンプレート変更

### `templates/reports/admin_oneone_questions.html`

1. **SortableJS CDN** をページ末尾に追加
2. 各セクションの `<tbody>` に `id="sortable-{{ section_key.0 }}"` を付与
3. 各 `<tr>` に `data-question-id="{{ q.id }}"` を付与
4. 左端にドラッグハンドル列（`⠿` アイコン、`cursor: grab`）を追加
5. **JS**: 全 `sortable-*` tbody を SortableJS で初期化。`onEnd` イベントで `fetch` POST（`action=reorder`, `question_ids=comma-separated`）を送信

---

## 5. 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `reports/views_admin.py` | `action=reorder` ハンドラ追加（JsonResponse返却） |
| `templates/reports/admin_oneone_questions.html` | SortableJS追加、ドラッグハンドル、JS実装 |

---

## 6. 制約・注意事項

- 並び替えはセクション内のみ。`section_number` は変更しない
- `question_ids` に含まれないIDは更新しない（他セクションの質問を誤って変更しない）
- AJAX失敗時はコンソールエラーのみ（ユーザー向けエラー表示なし）。管理者ツールのため許容
- `action=reorder` は CSRF トークン付きで送信する（`fetch` の `body` に `csrfmiddlewaretoken` を含める）
