import logging
from typing import Dict, List

from django.utils import timezone

from habits.models import Habit
from users.services import telegram_service

logger = logging.getLogger(__name__)


def get_due_habits(now: timezone.datetime) -> List[Habit]:
    """
    Возвращает привычки, для которых нужно отправить напоминание в указанное время.
    
    Args:
        now: Текущее время для проверки
        
    Returns:
        Список привычек, которые нужно выполнить сейчас
    """
    current_time = now.time()
    current_date = now.date()
    
    # Получаем все привычки
    habits = Habit.objects.all()
    
    due_habits = []
    
    for habit in habits:
        # Проверяем, совпадает ли время
        if habit.time != current_time:
            continue
            
        # Проверяем периодичность (frequency - раз в N дней)
        days_since_last_reminder = None
        if habit.last_reminder:
            days_since_last_reminder = (current_date - habit.last_reminder.date()).days
        else:
            # Если напоминаний еще не было, считаем дни с создания привычки
            days_since_last_reminder = (current_date - habit.created_at.date()).days
        
        # Если пора отправлять напоминание
        if days_since_last_reminder is None or days_since_last_reminder >= habit.frequency:
            due_habits.append(habit)
    
    return due_habits


def format_habit_message(habit: Habit) -> str:
    """
    Форматирует сообщение о привычке для отправки в Telegram.
    
    Args:
        habit: Объект привычки
        
    Returns:
        Отформатированное сообщение
    """
    message = f"⏰ Напоминание о привычке!\n\n"
    message += f"📍 Место: {habit.place}\n"
    message += f"🎯 Действие: {habit.action}\n"
    message += f"⏱️ Длительность: {habit.duration} секунд\n"
    
    if habit.reward:
        message += f"🎁 Награда: {habit.reward}\n"
    
    if habit.related_habit:
        message += f"🔗 Связанная привычка: {habit.related_habit.action}\n"
    
    message += f"\n💪 Не забудь выполнить свою привычку!"
    
    return message


def send_telegram_notification(telegram_id: str, message: str) -> bool:
    """
    Отправляет уведомление в Telegram через сервис уведомлений.
    
    Args:
        telegram_id: ID пользователя в Telegram
        message: Текст сообщения
        
    Returns:
        True если отправка успешна, False в противном случае
    """
    return telegram_service.send_message(telegram_id, message)


def process_single_habit(habit_id: int, now: timezone.datetime) -> Dict[str, int]:
    """
    Обрабатывает одну привычку - отправляет уведомление если нужно.
    
    Args:
        habit_id: ID привычки
        now: Текущее время
        
    Returns:
        Статистика обработки
    """
    stats = {"sent": 0, "skipped": 0, "errors": 0}
    
    try:
        habit = Habit.objects.get(id=habit_id)
        
        # Проверяем, есть ли у пользователя telegram_id
        if not habit.user.telegram_id:
            logger.warning(f"У пользователя {habit.user.email} не привязан Telegram")
            stats["skipped"] += 1
            return stats
        
        # Формируем и отправляем сообщение
        message = format_habit_message(habit)
        success = send_telegram_notification(habit.user.telegram_id, message)
        
        if success:
            # Обновляем время последнего напоминания
            habit.last_reminder = now
            habit.save(update_fields=['last_reminder'])
            stats["sent"] += 1
            logger.info(f"Отправлено напоминание для привычки {habit.id}")
        else:
            stats["errors"] += 1
            logger.error(f"Ошибка отправки напоминания для привычки {habit.id}")
            
    except Habit.DoesNotExist:
        logger.error(f"Привычка с ID {habit_id} не найдена")
        stats["errors"] += 1
    except Exception as e:
        logger.error(f"Ошибка обработки привычки {habit_id}: {e}")
        stats["errors"] += 1
    
    return stats


def process_due_habits(now: timezone.datetime) -> Dict[str, int]:
    """
    Обрабатывает все привычки, для которых пора отправить напоминания.
    
    Args:
        now: Текущее время
        
    Returns:
        Статистика обработки
    """
    stats = {"sent": 0, "skipped": 0, "errors": 0}
    
    try:
        due_habits = get_due_habits(now)
        
        if not due_habits:
            logger.info("Нет привычек для напоминания")
            return stats
        
        logger.info(f"Найдено {len(due_habits)} привычек для напоминания")
        
        for habit in due_habits:
            # Проверяем, есть ли у пользователя telegram_id
            if not habit.user.telegram_id:
                logger.warning(f"У пользователя {habit.user.email} не привязан Telegram")
                stats["skipped"] += 1
                continue
            
            # Формируем и отправляем сообщение
            message = format_habit_message(habit)
            success = send_telegram_notification(habit.user.telegram_id, message)
            
            if success:
                # Обновляем время последнего напоминания
                habit.last_reminder = now
                habit.save(update_fields=['last_reminder'])
                stats["sent"] += 1
                logger.info(f"Отправлено напоминание для привычки {habit.id}")
            else:
                stats["errors"] += 1
                logger.error(f"Ошибка отправки напоминания для привычки {habit.id}")
        
        logger.info(f"Обработка завершена: отправлено {stats['sent']}, "
                   f"пропущено {stats['skipped']}, ошибок {stats['errors']}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при обработке привычек: {e}")
        stats["errors"] += 1
    
    return stats
