from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Habit
from .tasks import send_single_habit_reminder


@receiver(post_save, sender=Habit)
def schedule_habit_reminder(sender, instance, created, **kwargs):
    """
    Сигнал, который ставит задачу на отправку уведомления о привычке в очередь Celery.
    """
    if created:
        # Получаем текущее время
        now = timezone.now()
        # Комбинируем текущую дату с временем привычки
        reminder_time = now.replace(
            hour=instance.time.hour,
            minute=instance.time.minute,
            second=0,
            microsecond=0
        )

        # Если время уведомления уже прошло сегодня, переносим на завтра
        if reminder_time < now:
            reminder_time += timedelta(days=1)

        # Вычисляем задержку в секундах до времени уведомления
        delay_seconds = (reminder_time - now).total_seconds()

        # Ставим задачу в очередь с отложенным выполнением
        send_single_habit_reminder.apply_async(
            args=[instance.id],
            countdown=delay_seconds
        )