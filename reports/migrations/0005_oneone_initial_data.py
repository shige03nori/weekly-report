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
    seeded_texts = [
        '最近の業務はどう？', '人間関係はどうか？', '作業量は多すぎない？',
        'その他、困っていることある？', '今後の見通し',
        '今勉強していることある？', '気になっている事ある？', '最近出来るようになったこと',
        '疲れてない？', '休日リフレッシュできてる？', '会社に対して不安ある？',
        '今後どういうエンジニアになりたい？', '将来的にリーダーやってみたい？',
        'やってみたい企画やイベント',
        '個人目標どう？', '来月の1on1までになにをするか？', '次回予定日',
    ]
    OneOnOneQuestion.objects.filter(question_text__in=seeded_texts).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('reports', '0004_alter_oneononeanswer_unique_together'),
    ]

    operations = [
        migrations.RunPython(create_initial_questions, reverse_initial_questions),
    ]
