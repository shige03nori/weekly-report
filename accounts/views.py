from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages


def login_view(request):
    if request.user.is_authenticated:
        return redirect('/')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(request.GET.get('next', '/'))
    elif request.method == 'POST':
        messages.error(request, 'メールアドレスまたはパスワードが正しくありません')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def password_change_view(request):
    form = PasswordChangeForm(request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'パスワードを変更しました')
        return redirect('/')
    return render(request, 'accounts/password_change.html', {'form': form})
