import os

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, set_script_prefix
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

if getattr(settings, "FORCE_SCRIPT_NAME", None):
    set_script_prefix(settings.FORCE_SCRIPT_NAME)

BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1")

schema_view = get_schema_view(
    openapi.Info(
        title="API Habit Reminder",
        default_version="v1",
        description="API documentation for Habit Reminder",
        terms_of_service="https://www.example.com/policies/terms/",
        contact=openapi.Contact(email="v.viktor.shadrin@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url=f"{BASE_URL}{settings.FORCE_SCRIPT_NAME}",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/habits/", include("habits.urls")),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
