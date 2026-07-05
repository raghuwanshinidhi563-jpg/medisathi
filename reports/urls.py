from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('voice/', views.voice_assistant, name='voice_assistant'),
    path('upload/', views.upload_report, name='upload_report'),
    path('history/', views.history, name='history'),
]