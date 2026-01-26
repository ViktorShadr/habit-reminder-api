from typing import Any, Mapping

from habits.models import Habit


def _get_value(source: Habit | Mapping[str, Any], key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def format_habit_message(source: Habit | Mapping[str, Any]) -> str:
    message = "⏰ Напоминание о привычке!\n\n"
    message += f"📍 Место: {_get_value(source, 'place', 'Не указано')}\n"
    message += f"🎯 Действие: {_get_value(source, 'action', 'Не указано')}\n"
    message += f"⏱️ Длительность: {_get_value(source, 'duration', 60)} секунд\n"

    reward = _get_value(source, "reward")
    if reward:
        message += f"🎁 Награда: {reward}\n"

    related_habit = _get_value(source, "related_habit")
    if related_habit:
        related_action = _get_value(related_habit, "action", related_habit)
        message += f"🔗 Связанная привычка: {related_action}\n"

    message += "\n💪 Не забудь выполнить свою привычку!"

    return message
