import logging

import httpx
from celery import shared_task
from django.utils import timezone

from .services import enqueue_due_habits, process_single_habit

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(httpx.RequestError, httpx.HTTPStatusError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_habit_reminders(self) -> dict:
    """Периодическая задача: ищет привычки и ставит задачи в очередь."""
    now = timezone.localtime(timezone.now())

    started_at = timezone.now()
    stats = enqueue_due_habits(now=now)
    elapsed = (timezone.now() - started_at).total_seconds()

    logger.info(
        "Habit reminders tick: enqueued=%s skipped=%s errors=%s elapsed=%.2fs now=%s",
        stats.get("enqueued", 0),
        stats.get("skipped", 0),
        stats.get("errors", 0),
        elapsed,
        now.isoformat(),
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
    """Воркер: отправляет одно напоминание по одной привычке."""
    now = timezone.localtime(timezone.now())
    stats = process_single_habit(habit_id=habit_id, now=now)

    logger.info(
        "Habit reminder processed: habit_id=%s sent=%s skipped=%s errors=%s",
        habit_id,
        stats.get("sent", 0),
        stats.get("skipped", 0),
        stats.get("errors", 0),
    )
    return stats
