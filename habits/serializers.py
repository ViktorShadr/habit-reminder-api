from rest_framework import serializers
from habits.models import Habit


class HabitSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    # Ограничиваем выбор связанной привычки: только приятные привычки текущего пользователя
    related_habit = serializers.PrimaryKeyRelatedField(
        queryset=Habit.objects.none(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Habit
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            self.fields["related_habit"].queryset = Habit.objects.filter(
                user=request.user,
                is_pleasant=True,
            )

    def validate(self, attrs):
        instance = self.instance

        is_pleasant = attrs.get("is_pleasant", getattr(instance, "is_pleasant", False))
        reward = attrs.get("reward", getattr(instance, "reward", None))
        related_habit = attrs.get(
            "related_habit", getattr(instance, "related_habit", None)
        )
        duration = attrs.get("duration", getattr(instance, "duration", None))
        frequency = attrs.get("frequency", getattr(instance, "frequency", 1))

        errors = {}

        # P1: Защита от утечки данных (IDOR) — нельзя привязывать привычку другого пользователя
        request = self.context.get("request")
        if related_habit and request and request.user and request.user.is_authenticated:
            if related_habit.user_id != request.user.id:
                errors.setdefault(
                    "related_habit",
                    "Нельзя привязывать привычку другого пользователя.",
                )

        # P2: Защита от циклических зависимостей — нельзя связывать привычку с самой собой
        if related_habit and instance and related_habit.id == instance.id:
            errors.setdefault(
                "related_habit",
                "Нельзя связывать привычку с самой собой.",
            )

        # 1) У приятной привычки не может быть вознаграждения или связанной привычки
        if is_pleasant and (reward or related_habit):
            errors.setdefault(
                "is_pleasant",
                "У приятной привычки не может быть вознаграждения или связанной привычки.",
            )
            if reward:
                errors.setdefault(
                    "reward",
                    "Для приятной привычки нельзя указывать вознаграждение.",
                )
            if related_habit:
                errors.setdefault(
                    "related_habit",
                    "Для приятной привычки нельзя указывать связанную привычку.",
                )

        # 2) Нельзя одновременно указывать вознаграждение и связанную привычку
        if reward and related_habit:
            errors.setdefault(
                "reward",
                "Нельзя одновременно указывать вознаграждение и связанную привычку.",
            )
            errors.setdefault(
                "related_habit",
                "Нельзя одновременно указывать связанную привычку и вознаграждение.",
            )

        # 3) Время выполнения не должно превышать 120 секунд
        if duration is not None and duration > 120:
            errors.setdefault(
                "duration",
                "Время выполнения должно быть не больше 120 секунд.",
            )

        # 4) В связанные привычки могут попадать только привычки с признаком приятной привычки
        if related_habit and not getattr(related_habit, "is_pleasant", False):
            errors.setdefault(
                "related_habit",
                "В связанную привычку можно выбрать только привычку с признаком приятной.",
            )

        # 5) Нельзя выполнять привычку реже, чем 1 раз в 7 дней (frequency: от 1 до 7)
        if frequency is not None and (frequency < 1 or frequency > 7):
            errors.setdefault(
                "frequency",
                "Нельзя выполнять привычку реже, чем 1 раз в 7 дней (значение от 1 до 7).",
            )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class HabitPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            "id",
            "place",
            "time",
            "action",
            "is_pleasant",
            "frequency",
            "duration",
            "reward",
            "related_habit",
        ]

