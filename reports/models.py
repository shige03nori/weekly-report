from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class WeeklyReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='ユーザー',
    )
    week_start = models.DateField(verbose_name='週開始日（月曜）')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提出日時')

    class Meta:
        unique_together = ('user', 'week_start')
        verbose_name = '週報'
        verbose_name_plural = '週報'
        ordering = ['-week_start']

    def __str__(self):
        return f'{self.user.name} - {self.week_start}週'

    def clean(self):
        if self.week_start and self.week_start.weekday() != 0:
            raise ValidationError({'week_start': '週開始日は月曜日を指定してください'})

    @property
    def is_submitted(self):
        return self.submitted_at is not None


class Q1ProjectField(models.Model):
    """Q1: プロジェクト情報（固定テーブル形式）"""
    report = models.ForeignKey(WeeklyReport, on_delete=models.CASCADE, related_name='q1_fields')
    label = models.CharField(max_length=100, verbose_name='項目名')
    value = models.TextField(blank=True, verbose_name='値')
    order = models.IntegerField(default=0, verbose_name='表示順')

    class Meta:
        ordering = ['order']
        verbose_name = 'Q1フィールド'
        verbose_name_plural = 'Q1フィールド'

    def __str__(self):
        return f'{self.label}: {self.value[:20]}'


class Q1FieldTemplate(models.Model):
    """Q1の項目テンプレート（管理者が編集する）"""
    label = models.CharField(max_length=100, verbose_name='項目名')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['order']
        verbose_name = 'Q1テンプレート'
        verbose_name_plural = 'Q1テンプレート'

    def __str__(self):
        return self.label


class QuestionSection(models.Model):
    SECTION_TYPES = [
        ('radio_matrix', 'ラジオマトリクス'),
        ('free_text', '自由記述'),
        ('select', '選択式'),
    ]
    title = models.CharField(max_length=200, verbose_name='セクションタイトル')
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, verbose_name='タイプ')
    scale_labels = models.JSONField(default=list, blank=True, verbose_name='選択肢ラベル')
    placeholder = models.CharField(max_length=200, blank=True, verbose_name='プレースホルダー')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['order']
        verbose_name = '質問セクション'
        verbose_name_plural = '質問セクション'

    def __str__(self):
        return self.title


class QuestionItem(models.Model):
    """ラジオマトリクスの各行"""
    section = models.ForeignKey(QuestionSection, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=200, verbose_name='項目名')
    order = models.IntegerField(default=0, verbose_name='表示順')

    class Meta:
        ordering = ['order']
        verbose_name = '質問項目'
        verbose_name_plural = '質問項目'

    def __str__(self):
        return f'{self.section.title} - {self.label}'


class Answer(models.Model):
    """動的Qセクションへの回答"""
    report = models.ForeignKey(WeeklyReport, on_delete=models.CASCADE, related_name='answers')
    question_section = models.ForeignKey(QuestionSection, on_delete=models.CASCADE)
    question_item = models.ForeignKey(
        QuestionItem, on_delete=models.SET_NULL, null=True, blank=True
    )
    value = models.TextField(blank=True, verbose_name='回答値')

    class Meta:
        verbose_name = '回答'
        verbose_name_plural = '回答'
        unique_together = ('report', 'question_section', 'question_item')

    def __str__(self):
        return f'{self.report} - {self.question_section.title} - {self.value[:20]}'


class OneOnOneQuestion(models.Model):
    section_number = models.IntegerField(verbose_name='セクション番号')
    section_title = models.CharField(max_length=100, verbose_name='セクション名')
    question_text = models.CharField(max_length=200, verbose_name='質問文')
    hint_text = models.CharField(max_length=200, blank=True, default='', verbose_name='補足テキスト')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')

    class Meta:
        ordering = ['section_number', 'order']
        verbose_name = '1on1質問'
        verbose_name_plural = '1on1質問'

    def __str__(self):
        return f'{self.section_number}. {self.question_text}'


class OneOnOneSession(models.Model):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oneone_sessions',
        verbose_name='メンバー',
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='oneone_interviews',
        verbose_name='担当管理者',
    )
    conducted_at = models.DateField(verbose_name='実施日')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-conducted_at']
        verbose_name = '1on1セッション'
        verbose_name_plural = '1on1セッション'

    def __str__(self):
        return f'{self.member.name} - {self.conducted_at}'


class OneOnOneAnswer(models.Model):
    session = models.ForeignKey(
        OneOnOneSession,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='セッション',
    )
    question = models.ForeignKey(
        OneOnOneQuestion,
        on_delete=models.PROTECT,
        verbose_name='質問',
    )
    text = models.TextField(blank=True, verbose_name='回答')

    class Meta:
        unique_together = ('session', 'question')
        verbose_name = '1on1回答'
        verbose_name_plural = '1on1回答'

    def __str__(self):
        return f'{self.session} - {self.question.question_text[:20]}'
