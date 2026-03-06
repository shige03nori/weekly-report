from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import WeeklyReport
from .utils import get_week_start, is_editable_week, today as get_today


@login_required
def home_view(request):
    today = get_today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # その月の全週を計算（月の最初の月曜日から）
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

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
        if ws in submitted_weeks:
            status = 'submitted'
        elif ws > current_week:
            status = 'future'
        elif is_editable_week(ws):
            status = 'editable'
        else:
            status = 'past'
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
