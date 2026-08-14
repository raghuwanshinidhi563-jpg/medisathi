from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('voice/', views.voice_assistant, name='voice_assistant'),
    path('disease-detector/', views.disease_detector, name='disease_detector'),
    path('find-doctors/', views.find_doctors, name='find_doctors'),
    path('book-consultation/', views.book_consultation, name='book_consultation'),
    path('upload/', views.upload_report, name='upload_report'),
    path('history/', views.history, name='history'),
]