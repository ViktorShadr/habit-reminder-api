import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.utils import timezone

from habits.models import Habit
from habits.notifications import format_habit_message
from users.services import get_telegram_service

logger = logging.getLogger(__name__)


def _get_user_telegram_id(habit: Habit) -> Optional[str]:
    """Возвращает telegram_id пользователя или None, если не привязан."""
    user = getattr(habit, "user", None)
    if not user:
        return None

    telegram_id = getattr(user, "telegram_id", None)

    if telegram_id in (None, "", 0, "0"):
        return None

    return str(telegram_id)


def _normalize_local_datetime(value: datetime) -> datetime:
    """Нормализует datetime до aware и локальной зоны."""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return timezone.localtime(value)


def _same_minute(left: datetime, right: datetime) -> bool:
    """Проверяет, что два времени попадают в одну минуту."""
    return left.replace(second=0, microsecond=0) == right.replace(second=0, microsecond=0)


def is_habit_due(habit: Habit, now: datetime, *, last_reminder_local: datetime | None = None) -> bool:
    """Определяет, нужно ли отправлять напоминание по привычке сейчас."""
    if habit.frequency is None:
        return False

    now_local = _normalize_local_datetime(now)
    if habit.last_reminder is None:
        return True

    last_reminder = last_reminder_local or _normalize_local_datetime(habit.last_reminder)
    if _same_minute(last_reminder, now_local):
        return False

    days_since = (now_local.date() - last_reminder.date()).days
    return days_since >= habit.frequency


def get_due_habits(now: datetime) -> List[Habit]:
    """Возвращает привычки, для которых нужно отправить напоминание сейчас."""

    now_local = _normalize_local_datetime(now)
    current_time = now_local.time()

    logger.debug(
        "get_due_habits: start now=%s (date=%s time=%02d:%02d)",
        now_local.isoformat(),
        now_local.date(),
        current_time.hour,
        current_time.minute,
    )

    qs = Habit.objects.filter(
        time__hour=current_time.hour,
        time__minute=current_time.minute,
    ).select_related("user")

    habits = list(qs)

    logger.debug("get_due_habits: candidates found=%s", len(habits))

    due: List[Habit] = []
    for habit in habits:
        if habit.frequency is None:
            logger.warning("Habit id=%s has frequency=None; skipping candidate", habit.id)
            continue

        if habit.last_reminder is None:
            logger.info(
                "Habit id=%s due: first reminder (last_reminder is None), frequency=%s user_id=%s",
                habit.id,
                habit.frequency,
                habit.user_id,
            )
            due.append(habit)
            continue

        last_reminder = _normalize_local_datetime(habit.last_reminder)
        if is_habit_due(habit, now_local, last_reminder_local=last_reminder):
            days_since = (now_local.date() - last_reminder.date()).days
            logger.info(
                "Habit id=%s due: days_since=%s >= frequency=%s last_reminder=%s user_id=%s",
                habit.id,
                days_since,
                habit.frequency,
                habit.last_reminder.isoformat() if habit.last_reminder else None,
                habit.user_id,
            )
            due.append(habit)
        else:
            days_since = (now_local.date() - last_reminder.date()).days
            logger.debug(
                "Habit id=%s not due: days_since=%s < frequency=%s last_reminder=%s",
                habit.id,
                days_since,
                habit.frequency,
                habit.last_reminder.isoformat(),
            )

    logger.info("get_due_habits: due found=%s at now=%s", len(due), now_local.isoformat())
    return due


def send_telegram_notification(telegram_id: str, message: str) -> bool:
    """Отправляет уведомление в Telegram через сервис уведомлений."""
    try:
        return get_telegram_service().send_message(telegram_id, message)
    except Exception:
        logger.exception("Telegram send crashed for telegram_id=%s", telegram_id)
        return False


def process_single_habit(habit_id: int, now: datetime) -> Dict[str, int]:
    """Отправляет напоминание по одной привычке и обновляет last_reminder при успехе."""
    stats = {"sent": 0, "skipped": 0, "errors": 0}

    now_local = _normalize_local_datetime(now)
    logger.info("process_single_habit: start habit_id=%s now=%s", habit_id, now_local.isoformat())

    try:
        habit = Habit.objects.select_related("user").get(id=habit_id)
    except Habit.DoesNotExist:
        logger.warning("process_single_habit: habit not found id=%s", habit_id)
        stats["errors"] += 1
        return stats

    telegram_id = _get_user_telegram_id(habit)
    if not telegram_id:
        logger.warning(
            "process_single_habit: skipped habit_id=%s user_id=%s reason=telegram_not_linked",
            habit.id,
            habit.user_id,
        )
        stats["skipped"] += 1
        return stats

    if not is_habit_due(habit, now_local):
        logger.info(
            "process_single_habit: skipped habit_id=%s user_id=%s reason=not_due",
            habit.id,
            habit.user_id,
        )
        stats["skipped"] += 1
        return stats

    try:
        message = format_habit_message(habit)
    except Exception:
        logger.exception("process_single_habit: message format failed habit_id=%s", habit.id)
        stats["errors"] += 1
        return stats

    logger.info(
        "process_single_habit: sending habit_id=%s user_id=%s telegram_id=%s",
        habit.id,
        habit.user_id,
        telegram_id,
    )

    success = send_telegram_notification(telegram_id, message)

    if success:
        habit.last_reminder = now_local
        habit.save(update_fields=["last_reminder"])
        stats["sent"] += 1
        logger.info(
            "process_single_habit: sent OK habit_id=%s user_id=%s last_reminder=%s",
            habit.id,
            habit.user_id,
            now_local.isoformat(),
        )
    else:
        stats["errors"] += 1
        logger.error("process_single_habit: send failed habit_id=%s user_id=%s", habit.id, habit.user_id)

    return stats


def enqueue_due_habits(now: datetime) -> Dict[str, int]:
    """Находит привычки, которым пора, и ставит задачи в очередь."""
    stats = {"enqueued": 0, "skipped": 0, "errors": 0}

    now_local = _normalize_local_datetime(now)
    logger.info("enqueue_due_habits: tick now=%s", now_local.isoformat())

    try:
        due_habits = get_due_habits(now_local)

        if not due_habits:
            logger.info("enqueue_due_habits: no due habits now=%s", now_local.isoformat())
            return stats

        logger.info("enqueue_due_habits: due habits count=%s now=%s", len(due_habits), now_local.isoformat())

        from .tasks import send_single_habit_reminder

        for habit in due_habits:
            telegram_id = _get_user_telegram_id(habit)
            if not telegram_id:
                logger.info(
                    "enqueue_due_habits: skipped enqueue habit_id=%s user_id=%s reason=telegram_not_linked",
                    habit.id,
                    habit.user_id,
                )
                stats["skipped"] += 1
                continue

            task_id = f"habit:{habit.id}:{now_local.strftime('%Y%m%d%H%M')}"

            logger.info(
                "enqueue_due_habits: enqueue habit_id=%s user_id=%s task_id=%s telegram_id=%s",
                habit.id,
                habit.user_id,
                task_id,
                telegram_id,
            )

            send_single_habit_reminder.apply_async(
                args=[habit.id],
                task_id=task_id,
            )
            stats["enqueued"] += 1

    except Exception as e:
        stats["errors"] += 1
        logger.exception("enqueue_due_habits: critical error: %s", e)

    logger.info(
        "enqueue_due_habits: done enqueued=%s skipped=%s errors=%s now=%s",
        stats["enqueued"],
        stats["skipped"],
        stats["errors"],
        now_local.isoformat(),
    )
    return stats
