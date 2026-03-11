from datetime import date, timedelta
from functools import wraps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from .models import WeeklyReport, QuestionSection, Q1FieldTemplate
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
    selected_dept = request.GET.get('department', '')

    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    departments = sorted(set(all_users.values_list('department', flat=True)))
    if selected_dept:
        all_users = all_users.filter(department=selected_dept)

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
        'departments': departments,
        'selected_dept': selected_dept,
    })


@admin_required
def admin_summary_view(request):
    today = get_today()
    fiscal_year = today.year if today.month >= 4 else today.year - 1
    fiscal_start = date(fiscal_year, 4, 1)
    selected_dept = request.GET.get('department', '')

    current_week = get_week_start(today)
    all_users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    departments = sorted(set(all_users.values_list('department', flat=True)))
    if selected_dept:
        all_users = all_users.filter(department=selected_dept)

    summary = []
    for user in all_users:
        total = WeeklyReport.objects.filter(user=user, week_start__gte=fiscal_start, week_start__lt=current_week).count()
        submitted = WeeklyReport.objects.filter(user=user, week_start__gte=fiscal_start, week_start__lt=current_week, submitted_at__isnull=False).count()
        summary.append({
            'user': user,
            'submitted': submitted,
            'not_submitted': total - submitted,
            'rate': round(submitted / total * 100) if total > 0 else 0,
        })

    return render(request, 'reports/admin_summary.html', {
        'summary': summary,
        'fiscal_year': fiscal_year,
        'departments': departments,
        'selected_dept': selected_dept,
    })


@admin_required
def admin_report_view(request, user_id, week_start_str):
    from .models import QuestionSection
    target_user = User.objects.get(id=user_id)
    week_start = date.fromisoformat(week_start_str)
    report = WeeklyReport.objects.get(user=target_user, week_start=week_start)
    sections = QuestionSection.objects.filter(is_active=True)
    q1_fields = report.q1_fields.all()
    current_answers = {}
    for a in report.answers.all():
        sid = a.question_section_id
        iid = a.question_item_id
        if sid not in current_answers:
            current_answers[sid] = {}
        current_answers[sid][iid] = a.value
    return render(request, 'reports/report_view.html', {
        'report': report,
        'week_start': week_start,
        'sections': sections,
        'q1_fields': q1_fields,
        'current_answers': current_answers,
        'target_user': target_user,
    })


@admin_required
def admin_questions_view(request):
    if request.method == 'POST':
        from .forms_admin import QuestionSectionForm
        action = request.POST.get('action')
        if action == 'add_section':
            form = QuestionSectionForm(request.POST)
            if form.is_valid():
                form.save()
        elif action == 'toggle_active':
            section_id = request.POST.get('section_id')
            section = QuestionSection.objects.get(id=section_id)
            section.is_active = not section.is_active
            section.save()
        elif action == 'reorder':
            for key, val in request.POST.items():
                if key.startswith('order_'):
                    sid = key.replace('order_', '')
                    QuestionSection.objects.filter(id=sid).update(order=int(val))
        return redirect('admin_questions')

    from .forms_admin import QuestionSectionForm
    sections = QuestionSection.objects.all().order_by('order')
    form = QuestionSectionForm()
    q1_templates = Q1FieldTemplate.objects.all().order_by('order')
    return render(request, 'reports/admin_questions.html', {
        'sections': sections,
        'form': form,
        'q1_templates': q1_templates,
    })


@admin_required
def admin_users_view(request):
    from .forms_admin import UserCreateForm
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザーを作成しました')
            return redirect('admin_users')
    else:
        form = UserCreateForm()

    users = User.objects.filter(is_active=True).order_by('name')
    return render(request, 'reports/admin_users.html', {'users': users, 'form': form})


@admin_required
def admin_edit_user_view(request, user_id):
    from .forms_admin import UserEditForm
    target = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, 'ユーザー情報を更新しました')
    return redirect('admin_users')


@admin_required
def admin_toggle_admin_view(request, user_id):
    if request.method == 'POST':
        target = User.objects.get(id=user_id)
        target.is_admin = not target.is_admin
        target.save()
    return redirect('admin_users')


@admin_required
def admin_monthly_view(request):
    today = get_today()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    # その月に含まれる週を計算（週の開始日がその月内のものだけ）
    first_day = date(year, month, 1)
    last_day = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year + 1, 1, 1) - timedelta(days=1)
    week_start = get_week_start(first_day)
    if week_start < first_day:
        week_start += timedelta(weeks=1)
    weeks = []
    while week_start <= last_day:
        weeks.append(week_start)
        week_start += timedelta(weeks=1)

    selected_dept = request.GET.get('department', '')
    users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    departments = sorted(set(users.values_list('department', flat=True)))
    if selected_dept:
        users = users.filter(department=selected_dept)

    submitted_set = set(
        WeeklyReport.objects.filter(
            week_start__in=weeks,
            submitted_at__isnull=False,
        ).values_list('user_id', 'week_start')
    )

    matrix = []
    for user in users:
        cells = [(w, (user.id, w) in submitted_set) for w in weeks]
        submitted_count = sum(1 for _, ok in cells if ok)
        matrix.append({'user': user, 'cells': cells, 'submitted': submitted_count, 'total': len(weeks)})

    # 年月セレクタ用
    year_choices = list(range(today.year - 2, today.year + 1))
    month_choices = list(range(1, 13))

    return render(request, 'reports/admin_monthly.html', {
        'matrix': matrix,
        'weeks': weeks,
        'year': year,
        'month': month,
        'year_choices': year_choices,
        'month_choices': month_choices,
        'departments': departments,
        'selected_dept': selected_dept,
    })


@admin_required
def admin_yearly_view(request):
    today = get_today()
    current_fiscal_year = today.year if today.month >= 4 else today.year - 1
    year = int(request.GET.get('year', current_fiscal_year))

    # その年度の全週を計算（4/1を含む週〜翌3/31を含む週）
    first_day = date(year, 4, 1)
    last_day = date(year + 1, 3, 31)
    week_start = get_week_start(first_day)
    all_weeks = []
    while week_start <= last_day:
        all_weeks.append(week_start)
        week_start += timedelta(weeks=1)

    # 週を月ごとにグループ化（週の月曜日が属する月）
    month_groups = {}
    for w in all_weeks:
        m = w.month
        month_groups.setdefault(m, []).append(w)

    selected_dept = request.GET.get('department', '')
    users = User.objects.filter(is_active=True, is_admin=False).order_by('name')
    departments = sorted(set(users.values_list('department', flat=True)))
    if selected_dept:
        users = users.filter(department=selected_dept)

    submitted_set = set(
        WeeklyReport.objects.filter(
            week_start__in=all_weeks,
            submitted_at__isnull=False,
        ).values_list('user_id', 'week_start')
    )

    matrix = []
    for user in users:
        cells = [(w, (user.id, w) in submitted_set) for w in all_weeks]
        submitted_count = sum(1 for _, ok in cells if ok)
        matrix.append({'user': user, 'cells': cells, 'submitted': submitted_count, 'total': len(all_weeks)})

    year_choices = list(range(current_fiscal_year - 2, current_fiscal_year + 1))

    return render(request, 'reports/admin_yearly.html', {
        'matrix': matrix,
        'all_weeks': all_weeks,
        'month_groups': month_groups,
        'year': year,
        'year_choices': year_choices,
        'departments': departments,
        'selected_dept': selected_dept,
    })
