from django import forms
from django.contrib.auth import get_user_model
from .models import QuestionSection, Q1FieldTemplate, OneOnOneSession, OneOnOneQuestion

User = get_user_model()


class QuestionSectionForm(forms.ModelForm):
    class Meta:
        model = QuestionSection
        fields = ['title', 'section_type', 'scale_labels', 'placeholder', 'order', 'is_active']
        widgets = {
            'scale_labels': forms.Textarea(attrs={'rows': 3, 'placeholder': '["選択肢1", "選択肢2"]'}),
        }


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='パスワード')

    class Meta:
        model = User
        fields = ['email', 'name', 'department', 'is_admin', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'name', 'department', 'is_admin']


class OneOnOneSessionForm(forms.ModelForm):
    class Meta:
        model = OneOnOneSession
        fields = ['member', 'conducted_at']
        widgets = {
            'conducted_at': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['member'].queryset = User.objects.filter(is_active=True).order_by('name')
        self.fields['member'].label = 'メンバー'
        self.fields['conducted_at'].label = '実施日'


class OneOnOneQuestionForm(forms.ModelForm):
    SECTION_TITLES = {
        1: '現場状況確認',
        2: '技術・業務の成長確認',
        3: 'メンタル・コンディション確認',
        4: 'キャリア確認',
        5: '会社への要望・改善',
        6: '次回までのアクション',
    }

    section_number = forms.TypedChoiceField(
        choices=[(i, str(i)) for i in range(1, 7)],
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='セクション番号',
    )

    class Meta:
        model = OneOnOneQuestion
        fields = ['section_number', 'question_text', 'hint_text']
        widgets = {
            'question_text': forms.TextInput(attrs={'class': 'form-control'}),
            'hint_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '任意'}),
        }
        labels = {
            'question_text': '質問文',
            'hint_text': '補足テキスト',
        }

    def get_section_title(self):
        return self.SECTION_TITLES.get(int(self.cleaned_data['section_number']), '')
