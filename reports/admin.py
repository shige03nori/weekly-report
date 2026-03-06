from django.contrib import admin
from .models import WeeklyReport, QuestionSection, QuestionItem, Q1FieldTemplate, Answer


class QuestionItemInline(admin.TabularInline):
    model = QuestionItem
    extra = 1


@admin.register(QuestionSection)
class QuestionSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'section_type', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    inlines = [QuestionItemInline]


@admin.register(Q1FieldTemplate)
class Q1FieldTemplateAdmin(admin.ModelAdmin):
    list_display = ('label', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start', 'submitted_at')
    list_filter = ('week_start',)
    search_fields = ('user__name', 'user__email')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('report', 'question_section', 'question_item', 'value')
    list_filter = ('question_section',)
