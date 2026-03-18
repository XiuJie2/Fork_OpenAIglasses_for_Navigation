from django.urls import path
from .views import SiteContentView

urlpatterns = [
    path('', SiteContentView.as_view(), name='site-content'),
]
