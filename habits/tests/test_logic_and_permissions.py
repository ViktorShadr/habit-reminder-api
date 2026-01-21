from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone as dj_timezone
from rest_framework.test import APIClient

from habits.models import Habit
from habits.services import is_habit_due


class HabitReminderLogicTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@example.com",
            password="pass12345",
        )

    def _make_now(self) -> datetime:
        return dj_timezone.make_aware(
            datetime(2024, 1, 1, 10, 30),
            dj_timezone.get_current_timezone(),
        )

    def _create_habit(self, **kwargs) -> Habit:
        defaults = {
            "user": self.user,
            "place": "Дом",
            "time": self._make_now().time(),
            "action": "Привычка",
        }
        defaults.update(kwargs)
        return Habit.objects.create(**defaults)

    def test_timezone_normalization(self):
        # last_reminder — в UTC (datetime.timezone.utc), это tz-aware datetime
        last_reminder = datetime(2024, 1, 1, 7, 0, tzinfo=dt_timezone.utc)

        # переводим в локальную таймзону проекта (Django TIME_ZONE)
        now_local = dj_timezone.localtime(last_reminder + timedelta(days=1))

        habit = self._create_habit(
            time=now_local.time(),
            last_reminder=last_reminder,
            frequency=1,
        )

        self.assertTrue(is_habit_due(habit, now_local))


class HabitPermissionsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="owner@example.com",
            password="pass12345",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="pass12345",
        )
        self.client = APIClient()

    def test_user_cannot_access_other_habit(self):
        habit = Habit.objects.create(
            user=self.user,
            place="Офис",
            time=dj_timezone.make_aware(
                datetime(2024, 1, 1, 9, 0),
                dj_timezone.get_current_timezone(),
            ).time(),
            action="Зарядка",
        )

        self.client.force_authenticate(user=self.other_user)
        url = reverse("habits:habits-detail", args=[habit.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
