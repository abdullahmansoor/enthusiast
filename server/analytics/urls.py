"""
URL configuration for Analytics API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from analytics.views import AnalyticsDashboardViewSet

# Create router
router = DefaultRouter()
router.register(r'analytics', AnalyticsDashboardViewSet, basename='analytics')

urlpatterns = [
    path('api/', include(router.urls)),
]
