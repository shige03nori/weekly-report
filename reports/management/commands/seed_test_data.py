import random
from datetime import date, timedelta, datetime, timezone

from django.core.management.base import BaseCommand

from accounts.models import User
from reports.models import WeeklyReport
from reports.utils import get_week_start


USER_NAMES = [
    '田中 太郎', '佐藤 花子', '鈴木 一郎', '高橋 美咲', '伊藤 健二',
    '渡辺 さくら', '山本 拓也', '中村 由美', '小林 浩司', '加藤 綾乃',
    '吉田 誠', '山田 麻衣', '佐々木 雄大', '松本 彩', '井上 翔太',
    '木村 奈々', '林 大輔', '清水 理恵', '山口 優斗', '池田 美穂',
]


def get_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


class Command(BaseCommand):
    help = '20名のテストユーザーと週報データを投入する'

    def handle(self, *args, **options):
        today = date.today()
        # 過去13週 + 今週 = 14週分
        weeks = []
        w = get_monday(today) - timedelta(weeks=13)
        while w <= get_monday(today):
            weeks.append(w)
            w += timedelta(weeks=1)

        created_users = 0
        created_reports = 0

        for i, name in enumerate(USER_NAMES):
            email = f'user{i+1:02d}@example.com'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'name': name, 'is_admin': False},
            )
            if created:
                user.set_password('password123')
                user.save()
                created_users += 1

            # 提出パターン: 提出率をユーザーごとに変える（高・中・低・ゼロ）
            if i < 5:
                submit_rate = 0.95   # ほぼ全員提出
            elif i < 12:
                submit_rate = 0.60   # 半分程度
            elif i < 18:
                submit_rate = 0.30   # たまに提出
            else:
                submit_rate = 0.0    # 全く提出しない

            for week_start in weeks:
                if random.random() < submit_rate:
                    # 提出済み: 月曜〜金曜の間のランダムな時刻
                    days_offset = random.randint(0, 4)
                    submitted_dt = datetime(
                        week_start.year, week_start.month, week_start.day,
                        random.randint(9, 18), random.randint(0, 59),
                        tzinfo=timezone.utc
                    ) + timedelta(days=days_offset)
                    report, _ = WeeklyReport.objects.get_or_create(
                        user=user, week_start=week_start,
                        defaults={'submitted_at': submitted_dt},
                    )
                    if report.submitted_at is None:
                        report.submitted_at = submitted_dt
                        report.save()
                    created_reports += 1
                else:
                    # 未提出: submitted_at=None でレコード作成
                    WeeklyReport.objects.get_or_create(
                        user=user, week_start=week_start,
                        defaults={'submitted_at': None},
                    )
                    created_reports += 1

        self.stdout.write(self.style.SUCCESS(
            f'テストデータ投入完了: ユーザー {created_users} 名作成, '
            f'週報 {created_reports} 件作成/更新'
        ))
        self.stdout.write(f'  総ユーザー数: {User.objects.count()} 名')
        self.stdout.write(f'  総週報数: {WeeklyReport.objects.count()} 件')
