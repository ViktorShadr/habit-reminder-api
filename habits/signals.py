from datetime import timedelta
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from celery import current_app
from .models import Habit
from .tasks import send_single_habit_reminder


@receiver(post_save, sender=Habit)
def schedule_habit_reminder(sender, instance, created, **kwargs):
    """
    Сигнал, который ставит задачу на отправку уведомления о привычке в очередь Celery.
    Обрабатывает как создание, так и обновление привычки.
    """
    # Отменяем все предыдущие задачи для этой привычки
    revoke_habit_tasks(instance.id)
    
    # Получаем текущее время
    now = timezone.now()
    
    # Рассчитываем следующее время напоминания с учетом периодичности
    next_reminder_time = calculate_next_reminder_time(instance, now)
    
    if next_reminder_time:
        # Вычисляем задержку в секундах до времени уведомления
        delay_seconds = (next_reminder_time - now).total_seconds()
        
        # Ставим задачу в очередь с отложенным выполнением и уникальным ID
        task_id = f"habit_reminder_{instance.id}_{int(next_reminder_time.timestamp())}"
        send_single_habit_reminder.apply_async(
            args=[instance.id],
            countdown=delay_seconds,
            task_id=task_id
        )


@receiver(post_delete, sender=Habit)
def cleanup_habit_tasks(sender, instance, **kwargs):
    """
    Сигнал, который отменяет все задачи для удаленной привычки.
    """
    revoke_habit_tasks(instance.id)


def revoke_habit_tasks(habit_id: int):
    """
    Отменяет все активные задачи для указанной привычки.
    """
    # Ищем все задачи, связанные с этой привычкой
    inspect = current_app.control.inspect()
    active_tasks = inspect.active()
    
    if active_tasks:
        for worker, tasks in active_tasks.items():
            for task in tasks:
                if (task.get('name') == 'habits.tasks.send_single_habit_reminder' and 
                    len(task.get('args', [])) > 0 and 
                    task['args'][0] == habit_id):
                    # Отменяем задачу
                    current_app.control.revoke(task['id'], terminate=True)


def calculate_next_reminder_time(habit: Habit, now: timezone.datetime) -> timezone.datetime:
    """
    Рассчитывает следующее время напоминания с учетом периодичности.
    """
    # Комбинируем текущую дату с временем привычки
    reminder_time = now.replace(
        hour=habit.time.hour,
        minute=habit.time.minute,
        second=0,
        microsecond=0
    )
    
    # Если время уведомления уже прошло сегодня, переносим на завтра
    if reminder_time < now:
        reminder_time += timedelta(days=1)
    
    # Проверяем периодичность
    if habit.last_reminder:
        days_since_last = (reminder_time.date() - habit.last_reminder.date()).days
        if days_since_last < habit.frequency:
            # Добавляем дни до следующего напоминания
            days_to_add = habit.frequency - days_since_last
            reminder_time += timedelta(days=days_to_add)
    
    return reminder_time