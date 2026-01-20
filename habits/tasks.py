import logging
from datetime import timedelta

import httpx
from celery import shared_task
from django.utils import timezone

from habits.services import process_due_habits, process_single_habit

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_habit_reminders(self) -> dict:
    """
    Periodic task (celery beat):
    - calculates current moment
    - delegates to service layer
    - returns stats for logs/monitoring
    """
    now = timezone.now()

    started_at = timezone.now()
    stats = process_due_habits(now=now)
    elapsed = (timezone.now() - started_at).total_seconds()

    logger.info(
        "Habit reminders run finished: sent=%s skipped=%s errors=%s elapsed=%.2fs",
        stats["sent"],
        stats["skipped"],
        stats["errors"],
        elapsed,
    )
    return stats


@shared_task(
    bind=True,
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_single_habit_reminder(self, habit_id: int) -> dict:
    """
    Отправляет напоминание о выполнении привычки.
    """
    from .models import Habit
    from .services import process_single_habit

    try:
        habit = Habit.objects.get(id=habit_id)
        now = timezone.now()
        return process_single_habit(habit.id, now)
    except Habit.DoesNotExist:
        logger.warning(f"Habit with id {habit_id} not found")
        return {"sent": 0, "skipped": 0, "errors": 1}
