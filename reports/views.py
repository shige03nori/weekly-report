from datetime import date, datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import (
    WeeklyReport, Q1ProjectField, Q1FieldTemplate,
    QuestionSection, QuestionItem, Answer
)
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


@login_required
def report_view(request, week_start_str):
    week_start = date.fromisoformat(week_start_str)
    editable = is_editable_week(week_start)

    report, _ = WeeklyReport.objects.get_or_create(
        user=request.user, week_start=week_start
    )

    # Q1テンプレート取得
    q1_templates = Q1FieldTemplate.objects.filter(is_active=True)

    # Q1プリセット: 直前の提出済み週報のQ1値
    prev_report = (
        WeeklyReport.objects.filter(
            user=request.user,
            submitted_at__isnull=False,
            week_start__lt=week_start,
        )
        .order_by('-week_start')
        .first()
    )
    prev_q1 = {}
    if prev_report:
        prev_q1 = {f.label: f.value for f in prev_report.q1_fields.all()}

    # 現在のQ1値（既存回答があれば優先）
    current_q1 = {f.label: f.value for f in report.q1_fields.all()}
    q1_defaults = {
        t.label: current_q1.get(t.label, prev_q1.get(t.label, ''))
        for t in q1_templates
    }

    # 動的Qセクション
    sections = QuestionSection.objects.filter(is_active=True)

    # current_answers: {section_id: {item_id: value}} (item_id=None for select/free_text)
    current_answers = {}
    for a in report.answers.all():
        sid = a.question_section_id
        iid = a.question_item_id
        if sid not in current_answers:
            current_answers[sid] = {}
        current_answers[sid][iid] = a.value

    if request.method == 'POST' and editable:
        # Q1保存
        report.q1_fields.all().delete()
        for t in q1_templates:
            Q1ProjectField.objects.create(
                report=report,
                label=t.label,
                value=request.POST.get(f'q1_{t.label}', ''),
                order=t.order,
            )

        # 動的Q保存
        report.answers.all().delete()
        for section in sections:
            if section.section_type == 'radio_matrix':
                for item in section.items.all():
                    val = request.POST.get(f'answer_{section.id}_{item.id}', '')
                    if val:
                        Answer.objects.create(
                            report=report,
                            question_section=section,
                            question_item=item,
                            value=val,
                        )
            else:
                val = request.POST.get(f'answer_{section.id}', '')
                Answer.objects.create(
                    report=report,
                    question_section=section,
                    value=val,
                )

        if request.POST.get('action') == 'submit':
            report.submitted_at = datetime.now()
            report.save()
            messages.success(request, '週報を提出しました')
        else:
            report.save()
            messages.success(request, '下書きを保存しました')

        return redirect('home')

    return render(request, 'reports/report_form.html', {
        'report': report,
        'week_start': week_start,
        'editable': editable,
        'q1_templates': q1_templates,
        'q1_defaults': q1_defaults,
        'sections': sections,
        'current_answers': current_answers,
    })


@login_required
def report_readonly_view(request, week_start_str):
    week_start = date.fromisoformat(week_start_str)
    report = get_object_or_404(WeeklyReport, user=request.user, week_start=week_start)
    q1_fields = report.q1_fields.all()
    sections = QuestionSection.objects.filter(is_active=True)
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
        'q1_fields': q1_fields,
        'sections': sections,
        'current_answers': current_answers,
    })
