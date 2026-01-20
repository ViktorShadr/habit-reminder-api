import logging
from datetime import datetime
from typing import Dict, List

from habits.models import Habit
from habits.notifications import format_habit_message
from users.services import get_telegram_service

logger = logging.getLogger(__name__)


def get_due_habits(now: datetime) -> List[Habit]:
    """
    Возвращает привычки, для которых нужно отправить напоминание в указанное время.
    Логика:
    - сравнение по часу и минуте (beat работает раз в минуту)
    - frequency = раз в N дней
    """

    # now уже должен приходить timezone-aware и в локальном времени (timezone.localtime)
    current_time = now.time()
    current_date = now.date()

    qs = Habit.objects.filter(
        time__hour=current_time.hour,
        time__minute=current_time.minute,
    )

    # Если у тебя есть такие поля — раскомментируй:
    # qs = qs.filter(is_active=True, is_pleasant=False)

    habits = list(qs.select_related("user"))

    due: List[Habit] = []
    for habit in habits:
        if habit.last_reminder:
            days_since = (current_date - habit.last_reminder.date()).days
        else:
            days_since = (current_date - habit.created_at.date()).days

        # frequency - раз в N дней
        # если frequency=1 → каждый день, frequency=2 → раз в 2 дня и т.д.
        if days_since >= habit.frequency:
            due.append(habit)

    return due


def send_telegram_notification(telegram_id: str, message: str) -> bool:
    """
    Отправляет уведомление в Telegram через сервис уведомлений.
    """
    return get_telegram_service().send_message(telegram_id, message)


def process_single_habit(habit_id: int, now: datetime) -> Dict[str, int]:
    """
    Отправляет уведомление по одной привычке.
    Обновляет last_reminder только если отправка успешна.
    """
    stats = {"sent": 0, "skipped": 0, "errors": 0}

    try:
        habit = Habit.objects.select_related("user").get(id=habit_id)
    except Habit.DoesNotExist:
        logger.warning("Habit not found: id=%s", habit_id)
        stats["errors"] += 1
        return stats

    # Если у тебя есть такие поля — раскомментируй:
    # if not habit.is_active or habit.is_pleasant:
    #     stats["skipped"] += 1
    #     return stats

    if not getattr(habit.user, "telegram_id", None):
        logger.warning("User %s has no telegram_id linked", getattr(habit.user, "email", habit.user_id))
        stats["skipped"] += 1
        return stats

    try:
        message = format_habit_message(habit)
        success = send_telegram_notification(habit.user.telegram_id, message)

        if success:
            habit.last_reminder = now
            habit.save(update_fields=["last_reminder"])
            stats["sent"] += 1
        else:
            stats["errors"] += 1
            logger.error("Telegram send failed for habit_id=%s", habit.id)

    except Exception as e:
        stats["errors"] += 1
        logger.exception("Error processing habit_id=%s: %s", habit.id, e)

    return stats


def enqueue_due_habits(now: datetime) -> Dict[str, int]:
    """
    Находит привычки, которым пора, и СТАВИТ задачи в очередь.
    Ничего не отправляет напрямую.
    """
    stats = {"enqueued": 0, "skipped": 0, "errors": 0}

    try:
        due_habits = get_due_habits(now)

        if not due_habits:
            logger.info("No due habits at %s", now.isoformat())
            return stats

        logger.info("Due habits found=%s at %s", len(due_habits), now.isoformat())

        # Импорт внутри функции, чтобы не ловить циклические импорты:
        from .tasks import send_single_habit_reminder

        # Важно: мы НЕ делаем отправку тут. Только enqueue.
        for habit in due_habits:
            # Пропуск, если телега не привязана (иначе очередь будет забита бессмысленными задачами)
            if not getattr(habit.user, "telegram_id", None):
                stats["skipped"] += 1
                continue

            # Опционально: чтобы не было дублей в пределах одной минуты,
            # можно задать детерминированный task_id:
            task_id = f"habit:{habit.id}:{now.strftime('%Y%m%d%H%M')}"

            send_single_habit_reminder.apply_async(
                args=[habit.id],
                task_id=task_id,
            )
            stats["enqueued"] += 1

    except Exception as e:
        stats["errors"] += 1
        logger.exception("Critical error in enqueue_due_habits: %s", e)

    return stats
