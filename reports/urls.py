from django.urls import path
from . import views, views_admin

urlpatterns = [
    path('', views.home_view, name='home'),
    path('report/<str:week_start_str>/', views.report_view, name='report_form'),
    path('report/<str:week_start_str>/view/', views.report_readonly_view, name='report_readonly'),
    path('mgmt/status/', views_admin.admin_status_view, name='admin_status'),
    path('mgmt/summary/', views_admin.admin_summary_view, name='admin_summary'),
    path('admin-view/<int:user_id>/<str:week_start_str>/', views_admin.admin_report_view, name='admin_report'),
    path('mgmt/questions/', views_admin.admin_questions_view, name='admin_questions'),
    path('mgmt/users/', views_admin.admin_users_view, name='admin_users'),
    path('mgmt/users/<int:user_id>/toggle-admin/', views_admin.admin_toggle_admin_view, name='admin_toggle_admin'),
    path('mgmt/users/<int:user_id>/edit/', views_admin.admin_edit_user_view, name='admin_edit_user'),
    path('mgmt/monthly/', views_admin.admin_monthly_view, name='admin_monthly'),
    path('mgmt/yearly/', views_admin.admin_yearly_view, name='admin_yearly'),
]
