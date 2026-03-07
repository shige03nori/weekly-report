from datetime import date, timedelta
from functools import wraps
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import WeeklyReport
from .utils import get_week_start, today as get_today

User = get_user_model()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            return HttpResponseForbidden('管理者権限が必要です')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_status_view(request):
    week_str = request.GET.get('week')
    selected_week = date.fromisoformat(week_str) if week_str else get_week_start(get_today())

    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    submitted_users = set(
        WeeklyReport.objects.filter(
            week_start=selected_week,
            submitted_at__isnull=False,
        ).values_list('user_id', flat=True)
    )

    users_data = [
        {'user': u, 'submitted': u.id in submitted_users}
        for u in all_users
    ]

    current_week = get_week_start(get_today())
    week_choices = [current_week - timedelta(weeks=i) for i in range(12)]

    return render(request, 'reports/admin_status.html', {
        'users_data': users_data,
        'selected_week': selected_week,
        'week_choices': week_choices,
    })


@admin_required
def admin_summary_view(request):
    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')

    summary = []
    for user in all_users:
        total = WeeklyReport.objects.filter(user=user).count()
        submitted = WeeklyReport.objects.filter(user=user, submitted_at__isnull=False).count()
        summary.append({
            'user': user,
            'submitted': submitted,
            'not_submitted': total - submitted,
            'rate': round(submitted / total * 100) if total > 0 else 0,
        })

    return render(request, 'reports/admin_summary.html', {'summary': summary})


@admin_required
def admin_report_view(request, user_id, week_start_str):
    from .models import QuestionSection
    target_user = User.objects.get(id=user_id)
    week_start = date.fromisoformat(week_start_str)
    report = WeeklyReport.objects.get(user=target_user, week_start=week_start)
    sections = QuestionSection.objects.filter(is_active=True)
    answers = {
        (a.question_section_id, a.question_item_id): a.value
        for a in report.answers.all()
    }
    return render(request, 'reports/report_view.html', {
        'report': report,
        'week_start': week_start,
        'sections': sections,
        'answers': answers,
        'target_user': target_user,
    })
