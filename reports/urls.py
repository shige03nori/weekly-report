from django.urls import path
from . import views, views_admin

urlpatterns = [
    path('', views.home_view, name='home'),
    path('report/<str:week_start_str>/', views.report_view, name='report_form'),
    path('report/<str:week_start_str>/view/', views.report_readonly_view, name='report_readonly'),
    path('mgmt/status/', views_admin.admin_status_view, name='admin_status'),
    path('mgmt/summary/', views_admin.admin_summary_view, name='admin_summary'),
    path('admin-view/<int:user_id>/<str:week_start_str>/', views_admin.admin_report_view, name='admin_report'),
]
