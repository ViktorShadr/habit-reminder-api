from django.urls import path
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.urls import set_script_prefix

from habits.apps import HabitsConfig
from habits.views import HabitViewSet, PublicListAPIView

if getattr(settings, "FORCE_SCRIPT_NAME", None):
    set_script_prefix(settings.FORCE_SCRIPT_NAME)

app_name = HabitsConfig.name

router = DefaultRouter()
router.register(r"", HabitViewSet, basename="habits")

urlpatterns = [
    path("public/", PublicListAPIView.as_view(), name="public-habits"),
] + router.urls
