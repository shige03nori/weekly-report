from django import forms
from django.contrib.auth import get_user_model
from .models import QuestionSection, Q1FieldTemplate

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


from .models import OneOnOneSession, OneOnOneQuestion


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
    class Meta:
        model = OneOnOneQuestion
        fields = ['section_number', 'question_text', 'hint_text']
        widgets = {
            'section_number': forms.Select(
                choices=[(i, f'{i}') for i in range(1, 7)],
                attrs={'class': 'form-select'},
            ),
            'question_text': forms.TextInput(attrs={'class': 'form-control'}),
            'hint_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '任意'}),
        }
        labels = {
            'section_number': 'セクション番号',
            'question_text': '質問文',
            'hint_text': '補足テキスト',
        }
