# 週報システム 設計ドキュメント

作成日: 2026-03-06

---

## 概要

社内向け週報提出・管理システム。メールアドレスとパスワードでログインし、カレンダーから週を選択して週報を提出する。管理者は提出状況の確認・集計・質問フォームの管理が可能。

- 想定ユーザー数: 〜30人
- デプロイ先: AWS (EC2 + RDS)
- 技術スタック: Django (Python) + PostgreSQL

---

## アーキテクチャ

```
Internet
    │
[Route 53] → ドメイン名解決
    │
[ACM] → SSL証明書（HTTPS）
    │
[EC2: t3.small]
  ├── Nginx（リバースプロキシ + 静的ファイル配信）
  └── Gunicorn（Django アプリサーバー）
    │
[RDS: PostgreSQL db.t3.micro]
```

- 静的ファイル: `collectstatic` → Nginx で直接配信（S3不要）
- シークレット管理: `.env` ファイル（SECRET_KEY, DB接続情報等）
- バックアップ: RDS自動バックアップ（7日間保持）
- Security Group: 80/443ポートのみ外部公開、5432はEC2からのみ

---

## データモデル

### User（カスタムユーザー）
| フィールド | 型 | 説明 |
|---|---|---|
| email | EmailField (unique) | ログインID |
| name | CharField | 氏名 |
| is_admin | BooleanField | 管理者フラグ |
| is_active | BooleanField | 有効フラグ |

### WeeklyReport（週報）
| フィールド | 型 | 説明 |
|---|---|---|
| user | FK → User | 提出者 |
| week_start | DateField | その週の月曜日 |
| submitted_at | DateTimeField | 提出日時 |
| is_draft | BooleanField | 下書きフラグ（将来拡張用）|

### Q1_ProjectInfo（プロジェクト情報 - 管理者編集可）

Q1はAdmin UIで項目名・行の追加・削除・並び替えが可能。
直前に提出した週報のQ1内容をデフォルト値として表示する。

| フィールド | 型 | 説明 |
|---|---|---|
| report | FK → WeeklyReport | |
| field_label | CharField | 項目名（例: "プロジェクト名"）|
| field_value | TextField | 回答値 |
| order | IntegerField | 表示順 |

### QuestionSection（動的質問セクション定義）
| フィールド | 型 | 説明 |
|---|---|---|
| title | CharField | セクションタイトル（例: "Q2 現在のあなたの状態について"）|
| section_type | CharField | `radio_matrix` / `free_text` / `select` |
| scale_labels | JSONField | 選択肢ラベル（例: ["いいえ","ややいいえ","ややはい","はい"]）|
| order | IntegerField | 表示順 |
| is_active | BooleanField | 有効/無効 |
| placeholder | CharField | free_textの場合のプレースホルダー |

### QuestionItem（セクション内の行）
| フィールド | 型 | 説明 |
|---|---|---|
| section | FK → QuestionSection | |
| label | CharField | 行ラベル（例: "稼働時間"）|
| order | IntegerField | 表示順 |

### Answer（回答）
| フィールド | 型 | 説明 |
|---|---|---|
| report | FK → WeeklyReport | |
| question_item | FK → QuestionItem (nullable) | radio_matrixの行 |
| question_section | FK → QuestionSection | |
| value | TextField | 回答値 |

---

## 初期プリセット質問セクション

| # | タイトル | 形式 | 備考 |
|---|------|------|------|
| Q1 | 現場について教えてください | テーブル形式 | 固定構造・前回値デフォルト表示・管理者編集可 |
| Q2 | 現在のあなたの状態について教えてください | ラジオマトリクス（5段階） | 稼働時間・仕事の人間関係・健康状態・精神状態 |
| Q3 | 現場の状況について教えてください | ラジオマトリクス（4段階） | タスク量・難易度・増減員・営業情報 |
| Q4 | 今週の残業時間 | 選択式 | 0h / 〜10h / 10〜20h / 20h超 |
| Q5 | 来週の予定タスク | 自由記述 | placeholder: "決まっていれば" |
| Q6 | スキルアップ・学習したこと | 自由記述 | |
| Q7 | ハラスメント・困りごとの有無 | はい/いいえ + 自由記述 | |
| Q8 | その他・共有や相談事項 | 自由記述 | |

---

## 画面構成

### ユーザー側

| 画面 | URL | 内容 |
|------|-----|------|
| ログイン | `/login` | メールアドレス + パスワード |
| ホーム（カレンダー） | `/` | 月表示カレンダー。週をクリックで週報へ |
| 週報入力・編集 | `/report/<week_start>/` | Q1〜Q8の入力フォーム |
| 週報確認（閲覧） | `/report/<week_start>/view/` | 提出済み週報の読み取り専用表示 |
| パスワード変更 | `/password/change/` | 現在のPW + 新PW + 確認 |

#### カレンダーの色分け仕様
- **緑**: 提出済み
- **ピンク/赤**: 未提出（過去の週）
- **グレー**: 未来の週（提出不可）
- **現在の週**: 枠線でハイライト

#### 提出・編集の制限
- 未来の週: 表示のみ（提出不可）
- 現在〜過去2週間: 提出・編集可能
- 過去3週間以降: 閲覧のみ（編集不可）

### 管理者側

| 画面 | URL | 内容 |
|------|-----|------|
| 提出状況一覧 | `/admin/status/` | 週を選択 → 提出済み・未提出ユーザー一覧 |
| 提出率集計 | `/admin/summary/` | ユーザーごとの提出回数・未提出回数・提出率 |
| 週報閲覧 | `/admin/report/<user_id>/<week_start>/` | 任意ユーザーの週報閲覧 |
| 質問管理 | `/admin/questions/` | QuestionSectionの追加・編集・並び替え・有効/無効 |
| ユーザー管理 | `/admin/users/` | アカウント作成・管理者権限付与 |

---

## デプロイ手順（概要）

1. EC2インスタンス起動（Amazon Linux 2 / Ubuntu）
2. Python, Nginx, PostgreSQL クライアントインストール
3. RDSインスタンス作成・接続設定
4. Django アプリをEC2に配置、`.env` 設定
5. `pip install -r requirements.txt`
6. `python manage.py migrate`
7. `python manage.py collectstatic`
8. Gunicornをsystemdサービスとして登録
9. Nginx設定（リバースプロキシ + HTTPS）
10. Route 53でドメイン設定

---

## 技術スタック

| 項目 | 選択 |
|------|------|
| バックエンド | Django 5.x |
| データベース | PostgreSQL 16 |
| Webサーバー | Nginx + Gunicorn |
| フロントエンド | Django Templates + Bootstrap 5 |
| カレンダーUI | FullCalendar.js または自作 |
| インフラ | AWS EC2 (t3.small) + RDS (db.t3.micro) |
| Python | 3.12 |
