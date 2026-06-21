from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_report, name='upload'),
    path('history/', views.history, name='history'),
]