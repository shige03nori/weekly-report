from datetime import date, timedelta


def today():
    """テストで差し替え可能な今日の日付関数"""
    return date.today()


def get_week_start(d: date) -> date:
    """その日の週の月曜日を返す"""
    return d - timedelta(days=d.weekday())


def is_editable_week(week_start: date) -> bool:
    """現在週から過去2週間以内（かつ未来でない）の週のみ編集可能"""
    current_week = get_week_start(today())
    two_weeks_ago = current_week - timedelta(weeks=2)
    return two_weeks_ago <= week_start <= current_week
