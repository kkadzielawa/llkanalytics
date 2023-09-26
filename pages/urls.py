from django.urls import path
from . import views
from django.views.generic import TemplateView

app_name = 'pages'

urlpatterns = [
        path('', TemplateView.as_view(template_name='home.html'), name='home'),
        path('services/', TemplateView.as_view(template_name='services.html'), name='services'),
    ]

