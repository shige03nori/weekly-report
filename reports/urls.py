from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('report/<str:week_start_str>/', views.report_view, name='report_form'),
    path('report/<str:week_start_str>/view/', views.report_readonly_view, name='report_readonly'),
]
