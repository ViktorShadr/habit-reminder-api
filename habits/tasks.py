import logging

import httpx
from celery import shared_task
from django.utils import timezone

from habits.services import process_due_habits, process_single_habit
from .models import Habit
from .services import process_single_habit

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
    Отправляет напоминание о выполнении привычки и создает следующее напоминание.
    """
    try:
        habit = Habit.objects.get(id=habit_id)
        now = timezone.now()
        
        # Отправляем текущее напоминание
        stats = process_single_habit(habit.id, now)
        
        # Если напоминание успешно отправлено, создаем следующее
        if stats["sent"] > 0:
            from .signals import calculate_next_reminder_time
            
            # Рассчитываем следующее время напоминания
            next_reminder_time = calculate_next_reminder_time(habit, now)
            
            if next_reminder_time:
                # Вычисляем задержку до следующего напоминания
                delay_seconds = (next_reminder_time - now).total_seconds()
                
                # Создаем следующую задачу с уникальным ID
                task_id = f"habit_reminder_{habit.id}_{int(next_reminder_time.timestamp())}"
                send_single_habit_reminder.apply_async(
                    args=[habit.id],
                    countdown=delay_seconds,
                    task_id=task_id
                )
                
                logger.info(f"Запланировано следующее напоминание для привычки {habit.id} на {next_reminder_time}")
        
        return stats
        
    except Habit.DoesNotExist:
        logger.warning(f"Habit with id {habit_id} not found")
        return {"sent": 0, "skipped": 0, "errors": 1}
