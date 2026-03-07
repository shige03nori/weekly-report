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
        fields = ['email', 'name', 'is_admin', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user
