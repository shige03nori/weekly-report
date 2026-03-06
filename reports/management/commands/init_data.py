from django.core.management.base import BaseCommand
from reports.models import QuestionSection, QuestionItem, Q1FieldTemplate


class Command(BaseCommand):
    help = '初期質問データを投入する（既存データがある場合はスキップ）'

    def handle(self, *args, **options):
        # Q1テンプレート
        q1_fields = [
            'プロジェクト名', '商流', '参加フェーズ', '使用技術', '使用ツール',
            '実施中のタスク１（状況）', '実施中のタスク２（状況）', '実施中のタスク３（状況）',
        ]
        for i, label in enumerate(q1_fields):
            Q1FieldTemplate.objects.get_or_create(
                label=label,
                defaults={'order': i + 1}
            )

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
            QuestionItem.objects.get_or_create(
                section=q2, label=label, defaults={'order': i + 1}
            )

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
            QuestionItem.objects.get_or_create(
                section=q3, label=label, defaults={'order': i + 1}
            )

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

        # Q7: ハラスメント・困りごとの有無
        QuestionSection.objects.get_or_create(
            title='Q7 ハラスメント・困りごとの有無',
            defaults={'section_type': 'free_text', 'order': 7}
        )

        # Q8: その他・共有や相談事項
        QuestionSection.objects.get_or_create(
            title='Q8 その他・共有や相談事項',
            defaults={'section_type': 'free_text', 'order': 8}
        )

        self.stdout.write(self.style.SUCCESS('初期データを投入しました'))
        self.stdout.write(f'  Q1テンプレート: {Q1FieldTemplate.objects.count()} 件')
        self.stdout.write(f'  質問セクション: {QuestionSection.objects.count()} 件')
        self.stdout.write(f'  質問項目: {QuestionItem.objects.count()} 件')
