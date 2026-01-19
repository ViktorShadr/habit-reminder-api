from rest_framework import serializers
from habits.models import Habit


class HabitSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Habit
        fields = "__all__"

    def validate(self, attrs):
        instance = self.instance

        is_pleasant = attrs.get("is_pleasant", getattr(instance, "is_pleasant", False))
        reward = attrs.get("reward", getattr(instance, "reward", None))
        related_habit = attrs.get("related_habit", getattr(instance, "related_habit", None))
        duration = attrs.get("duration", getattr(instance, "duration", None))
        frequency = attrs.get("frequency", getattr(instance, "frequency", 1))

        errors = {}

        # 1) У приятной привычки не может быть вознаграждения или связанной привычки
        if is_pleasant and (reward or related_habit):
            errors["is_pleasant"] = "У приятной привычки не может быть вознаграждения или связанной привычки."
            if reward:
                errors["reward"] = "Для приятной привычки нельзя указывать вознаграждение."
            if related_habit:
                errors["related_habit"] = "Для приятной привычки нельзя указывать связанную привычку."

        # 2) Нельзя одновременно указывать вознаграждение и связанную привычку
        if reward and related_habit:
            errors["reward"] = "Нельзя одновременно указывать вознаграждение и связанную привычку."
            errors["related_habit"] = "Нельзя одновременно указывать связанную привычку и вознаграждение."

        # 3) Время выполнения не должно превышать 120 секунд
        if duration is not None and duration > 120:
            errors["duration"] = "Время выполнения должно быть не больше 120 секунд."

        # 4) В связанные привычки могут попадать только привычки с признаком приятной привычки
        if related_habit and not getattr(related_habit, "is_pleasant", False):
            errors["related_habit"] = "В связанную привычку можно выбрать только привычку с признаком приятной."

        # 5) Нельзя выполнять привычку реже, чем 1 раз в 7 дней (frequency: от 1 до 7)
        if frequency is not None and (frequency < 1 or frequency > 7):
            errors["frequency"] = "Нельзя выполнять привычку реже, чем 1 раз в 7 дней (значение от 1 до 7)."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs
