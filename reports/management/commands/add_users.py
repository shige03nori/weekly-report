from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

USERS = [
    ('ma.takahashi@vicent.co.jp', '高橋 誠',    'SES事業部',        True),
    ('s.yamato@vicent.co.jp',     '大和 宗一郎', 'SES事業部',        True),
    ('d.baba@vicent.co.jp',       '馬場 大輔',   'SES事業部 第2チーム', True),
    ('poeeiphyu@vicent.co.jp',    'POE EI PHYU', 'SES事業部 第2チーム', False),
    ('r.thapa@vicent.co.jp',      'タパ レシャム', 'SES事業部 第2チーム', False),
    ('a.ito@vicent.co.jp',        '伊藤 茜',     'SES事業部 第1チーム', False),
    ('r.tachibana@vicent.co.jp',  '橘 隆樹',     'SES事業部 第2チーム', False),
    ('y.honma@vicent.co.jp',      '宗宮 裕士',   'SES事業部 第1チーム', False),
    ('t.ogawa@vicent.co.jp',      '小川 達也',   'SES事業部 第1チーム', False),
    ('k.kamitaka@vicent.co.jp',   '上高 一樹',   'SES事業部 第2チーム', False),
    ('c.kawamoto@vicent.co.jp',   '川本 智恵',   'SES事業部 第1チーム', False),
    ('h.watanabe@vicent.co.jp',   '渡邊 博文',   'SES事業部 第1チーム', False),
    ('h.fujita@vicent.co.jp',     '藤田 春奈',   'SES事業部 第2チーム', False),
]


class Command(BaseCommand):
    help = 'VICENTユーザーを一括登録する'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for email, name, department, is_admin in USERS:
            if User.objects.filter(email=email).exists():
                self.stdout.write(f'スキップ（既存）: {email}')
                skipped += 1
                continue
            User.objects.create_user(
                email=email,
                password='1234',
                name=name,
                department=department,
                is_admin=is_admin,
            )
            self.stdout.write(f'作成: {name} ({email})')
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n完了: {created}件作成、{skipped}件スキップ'
        ))
