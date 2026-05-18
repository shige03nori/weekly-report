# 1on1ミーティング機能 設計ドキュメント

**日付:** 2026-05-18  
**対象アプリ:** weekly-report（Django）  
**実装方針:** 既存 `reports` アプリに追記

---

## 1. 概要

月1回実施する1on1ミーティングの記録・閲覧機能を追加する。

- 管理者（`is_admin=True`）のみが記録を作成・編集できる
- メンバーは自分が受けた1on1の記録を読み取り専用で閲覧できる
- 質問内容はDBで管理し、管理者が後から追加・有効化/無効化できる

---

## 2. データモデル

### `OneOnOneQuestion`

1on1で使う質問（管理者が編集可能）。

| フィールド | 型 | 説明 |
|---|---|---|
| `section_number` | IntegerField | セクション番号（1〜6） |
| `section_title` | CharField(100) | セクション名（例: 現場状況確認） |
| `question_text` | CharField(200) | 質問文 |
| `hint_text` | CharField(200, blank) | 補足テキスト（例: ふんわり聞く） |
| `order` | IntegerField | 表示順 |
| `is_active` | BooleanField | 有効/無効（削除せず無効化で対応） |

### `OneOnOneSession`

1on1の1回分のセッション。

| フィールド | 型 | 説明 |
|---|---|---|
| `member` | FK → User | 面談を受けたメンバー |
| `interviewer` | FK → User | 実施した管理者（作成者） |
| `conducted_at` | DateField | 実施日 |
| `created_at` | DateTimeField(auto) | 作成日時 |

### `OneOnOneAnswer`

セッションの各質問への回答。

| フィールド | 型 | 説明 |
|---|---|---|
| `session` | FK → OneOnOneSession | 対応セッション |
| `question` | FK → OneOnOneQuestion (SET_NULL) | 対応質問 |
| `text` | TextField(blank) | 回答テキスト |

- セッション作成時に `is_active=True` の全質問に対して Answer レコードを自動生成する
- `question` は `PROTECT`（回答が存在する質問はDBから削除不可）。無効化は `is_active=False` のみで行う
- アプリ側で同一 `(session, question)` の重複生成を防ぐ（DBの `unique_together` は設けない。将来の NULL 問題を回避）

---

## 3. 初期データ

マイグレーション（`data migration`）で以下を自動投入する。

### セクション 1: 現場状況確認
1. 最近の業務はどう？ ／ ヒント: ふんわり聞く　狙い：自分の意志が出やすくなる
2. 人間関係はどうか？
3. 作業量は多すぎない？
4. その他、困っていることある？
5. 今後の見通し

### セクション 2: 技術・業務の成長確認
1. 今勉強していることある？ ／ ヒント: AIとか・・・
2. 気になっている事ある？
3. 最近出来るようになったこと ／ ヒント: IT以外の些細な所も

### セクション 3: メンタル・コンディション確認
1. 疲れてない？
2. 休日リフレッシュできてる？
3. 会社に対して不安ある？

### セクション 4: キャリア確認
1. 今後どういうエンジニアになりたい？
2. 将来的にリーダーやってみたい？

### セクション 5: 会社への要望・改善
1. やってみたい企画やイベント

### セクション 6: 次回までのアクション（宿題）
1. 個人目標どう？
2. 来月の1on1までになにをするか？
3. 次回予定日

---

## 4. URL 構造

```
# 管理者向け
mgmt/oneone/                     → admin_oneone_list_view    (name: admin_oneone_list)
mgmt/oneone/new/                 → admin_oneone_new_view     (name: admin_oneone_new)
mgmt/oneone/<int:session_id>/    → admin_oneone_detail_view  (name: admin_oneone_detail)
mgmt/oneone/questions/           → admin_oneone_questions_view (name: admin_oneone_questions)

# メンバー向け
oneone/                          → oneone_member_list_view   (name: oneone_member_list)
oneone/<int:session_id>/         → oneone_member_detail_view (name: oneone_member_detail)
```

---

## 5. ビュー仕様

### 管理者向け

| ビュー | 権限 | 内容 |
|---|---|---|
| `admin_oneone_list_view` | `is_admin` | メンバー一覧（部署フィルター付き）。各メンバーの最終実施日・実施回数・担当管理者を表示。未実施メンバーも表示する |
| `admin_oneone_new_view` | `is_admin` | GET: メンバー選択・実施日入力フォーム。POST: セッション作成＋全アクティブ質問の Answer レコード生成。interviewer は `request.user` で自動セット。成功後は `admin_oneone_detail` にリダイレクト |
| `admin_oneone_detail_view` | `is_admin` | セッション詳細の閲覧・編集。POST で各 Answer のテキストを更新 |
| `admin_oneone_questions_view` | `is_admin` | 質問一覧表示。POST: 質問追加 / 有効化・無効化切り替え |

### メンバー向け

| ビュー | 権限 | 内容 |
|---|---|---|
| `oneone_member_list_view` | ログイン済み | `request.user` が member のセッション一覧（実施日降順） |
| `oneone_member_detail_view` | ログイン済み | セッション詳細（読み取り専用）。自分のセッション以外は 403 |

---

## 6. テンプレート構成

```
templates/reports/
  admin_oneone_list.html       # admin_base.html を extend
  admin_oneone_new.html        # admin_base.html を extend
  admin_oneone_detail.html     # admin_base.html を extend
  admin_oneone_questions.html  # admin_base.html を extend
  oneone_member_list.html      # base.html を extend
  oneone_member_detail.html    # base.html を extend
```

---

## 7. ナビゲーション変更

### 管理者ナビ（`admin_base.html`）

既存タブに「1on1」を追加する。

```
週次 | 月次 | 年次 | 集計 | 質問管理 | ユーザー管理 | 1on1
```

### ホーム画面（`home.html`）

週報リストの下に「1on1の記録を見る →」リンクを追加する（メンバー向け）。

---

## 8. 既存ファイルへの変更

| ファイル | 変更内容 |
|---|---|
| `reports/models.py` | 3モデル追加 |
| `reports/views_admin.py` | 管理者ビュー4本追加 |
| `reports/views.py` | メンバービュー2本追加 |
| `reports/urls.py` | 6 URL追加 |
| `reports/forms_admin.py` | `OneOnOneSessionForm`・`OneOnOneQuestionForm` 追加 |
| `templates/reports/admin_base.html` | 1on1タブ追加 |
| `templates/reports/home.html` | 1on1リンク追加 |
| `reports/migrations/` | モデル追加マイグレーション＋データマイグレーション |

---

## 9. 制約・注意事項

- 質問は削除せず `is_active=False` で無効化する（過去の Answer レコードとの整合性を保つため）
- `OneOnOneAnswer.question` は `PROTECT`。回答が存在する質問はDBから削除できない
- 新規質問追加時の `order` は該当セクションの最大値 + 1 を自動セット
- メンバーは自分以外のセッション詳細に直接URLアクセスしても 403 を返す
- 管理者は全メンバーのセッションを閲覧・編集できる
