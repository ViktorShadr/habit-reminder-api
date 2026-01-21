from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from habits.models import Habit
from habits.serializers import HabitPublicSerializer, HabitSerializer

User = get_user_model()


class HabitSerializerTests(TestCase):
    """Тесты сериализатора HabitSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/")
        self.request.user = self.user

        # Создаем приятную привычку для тестов
        self.pleasant_habit = Habit.objects.create(
            user=self.user, place="Дом", time=time(10, 0), action="Съесть конфету", is_pleasant=True, duration=30
        )

    def get_serializer_context(self):
        """Получаем контекст для сериализатора"""
        return {"request": self.request}

    def test_valid_habit_creation(self):
        """Тест создания валидной привычки"""
        data = {"place": "Офис", "time": "09:00:00", "action": "Делать зарядку", "duration": 60, "frequency": 1}

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertTrue(serializer.is_valid())

        habit = serializer.save()
        self.assertEqual(habit.user, self.user)
        self.assertEqual(habit.place, "Офис")
        self.assertEqual(habit.action, "Делать зарядку")

    def test_valid_habit_with_related_habit(self):
        """Тест создания привычки со связанной приятной привычкой"""
        data = {
            "place": "Дом",
            "time": "08:00:00",
            "action": "Утренняя пробежка",
            "duration": 90,
            "frequency": 2,
            "related_habit": self.pleasant_habit.id,
        }

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertTrue(serializer.is_valid())

        habit = serializer.save()
        self.assertEqual(habit.related_habit, self.pleasant_habit)

    def test_valid_habit_with_reward(self):
        """Тест создания привычки с вознаграждением"""
        data = {
            "place": "Офис",
            "time": "18:00:00",
            "action": "Закончить работу",
            "duration": 30,
            "frequency": 1,
            "reward": "Посмотреть фильм",
        }

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertTrue(serializer.is_valid())

    def test_pleasant_habit_cannot_have_reward_or_related(self):
        """Тест: приятная привычка не может иметь вознаграждение или связанную привычку"""
        # Тест с вознаграждением
        data1 = {
            "place": "Дом",
            "time": "20:00:00",
            "action": "Читать книгу",
            "is_pleasant": True,
            "reward": "Чай с печеньем",
        }

        serializer1 = HabitSerializer(data=data1, context=self.get_serializer_context())
        self.assertFalse(serializer1.is_valid())
        self.assertIn("is_pleasant", serializer1.errors)
        self.assertIn("reward", serializer1.errors)

        # Тест со связанной привычкой
        data2 = {
            "place": "Дом",
            "time": "21:00:00",
            "action": "Медитировать",
            "is_pleasant": True,
            "related_habit": self.pleasant_habit.id,
        }

        serializer2 = HabitSerializer(data=data2, context=self.get_serializer_context())
        self.assertFalse(serializer2.is_valid())
        self.assertIn("is_pleasant", serializer2.errors)
        self.assertIn("related_habit", serializer2.errors)

    def test_cannot_have_both_reward_and_related_habit(self):
        """Тест: нельзя указывать одновременно вознаграждение и связанную привычку"""
        data = {
            "place": "Офис",
            "time": "12:00:00",
            "action": "Обед",
            "reward": "Кофе",
            "related_habit": self.pleasant_habit.id,
        }

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn("reward", serializer.errors)
        self.assertIn("related_habit", serializer.errors)

    def test_duration_max_120_seconds(self):
        """Тест: время выполнения не должно превышать 120 секунд"""
        data = {
            "place": "Спортзал",
            "time": "19:00:00",
            "action": "Тренировка",
            "duration": 150,  # Превышает 120 секунд
        }

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn("duration", serializer.errors)

    def test_frequency_between_1_and_7(self):
        """Тест: частота должна быть от 1 до 7 дней"""
        # Тест с частотой меньше 1
        data1 = {"place": "Дом", "time": "07:00:00", "action": "Подъем", "frequency": 0}

        serializer1 = HabitSerializer(data=data1, context=self.get_serializer_context())
        self.assertFalse(serializer1.is_valid())
        self.assertIn("frequency", serializer1.errors)

        # Тест с частотой больше 7
        data2 = {"place": "Дом", "time": "22:00:00", "action": "Отбой", "frequency": 8}

        serializer2 = HabitSerializer(data=data2, context=self.get_serializer_context())
        self.assertFalse(serializer2.is_valid())
        self.assertIn("frequency", serializer2.errors)

    def test_related_habit_must_be_pleasant(self):
        """Тест: связанная привычка должна быть приятной"""
        # Создаем обычную (не приятную) привычку
        normal_habit = Habit.objects.create(
            user=self.user, place="Офис", time=time(9, 0), action="Работать", is_pleasant=False
        )

        data = {"place": "Офис", "time": "08:00:00", "action": "Прийти на работу", "related_habit": normal_habit.id}

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn("related_habit", serializer.errors)

    def test_cannot_link_habit_to_itself(self):
        """Тест: нельзя связывать привычку с самой собой"""
        habit = Habit.objects.create(user=self.user, place="Дом", time=time(10, 0), action="Тестовая привычка")

        data = {"place": habit.place, "time": habit.time, "action": habit.action, "related_habit": habit.id}

        serializer = HabitSerializer(data=data, instance=habit, context=self.get_serializer_context())
        self.assertFalse(serializer.is_valid())
        self.assertIn("related_habit", serializer.errors)

    def test_related_habit_queryset_filtered_by_user(self):
        """Тест: queryset для related_habit фильтруется по пользователю"""
        # Создаем привычку другого пользователя
        other_user = User.objects.create_user(email="other@example.com", password="pass123")
        other_habit = Habit.objects.create(
            user=other_user, place="Другое место", time=time(15, 0), action="Чужая привычка", is_pleasant=True
        )

        # Проверяем, что в queryset только привычки текущего пользователя
        serializer = HabitSerializer(context=self.get_serializer_context())
        queryset = serializer.fields["related_habit"].queryset

        self.assertIn(self.pleasant_habit, queryset)
        self.assertNotIn(other_habit, queryset)

    def test_user_field_hidden(self):
        """Тест: поле user скрыто и устанавливается автоматически"""
        data = {"place": "Дом", "time": "20:00:00", "action": "Ужин"}

        serializer = HabitSerializer(data=data, context=self.get_serializer_context())
        self.assertTrue(serializer.is_valid())

        habit = serializer.save()
        self.assertEqual(habit.user, self.user)
        self.assertNotIn("user", data)


class HabitPublicSerializerTests(TestCase):
    """Тесты сериализатора HabitPublicSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")
        self.habit = Habit.objects.create(
            user=self.user,
            place="Парк",
            time=time(17, 0),
            action="Прогулка",
            is_pleasant=True,
            duration=45,
            frequency=3,
            reward="Мороженое",
        )

    def test_public_serializer_fields(self):
        """Тест: публичный сериализатор содержит только нужные поля"""
        serializer = HabitPublicSerializer(self.habit)
        data = serializer.data

        expected_fields = [
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

        for field in expected_fields:
            self.assertIn(field, data)

        # Проверяем, что приватные поля отсутствуют
        private_fields = ["user", "is_public", "created_at", "updated_at", "last_reminder"]
        for field in private_fields:
            self.assertNotIn(field, data)

    def test_public_serializer_data_correctness(self):
        """Тест: данные в публичном сериализаторе корректны"""
        serializer = HabitPublicSerializer(self.habit)
        data = serializer.data

        self.assertEqual(data["id"], self.habit.id)
        self.assertEqual(data["place"], self.habit.place)
        self.assertEqual(data["time"], str(self.habit.time))
        self.assertEqual(data["action"], self.habit.action)
        self.assertEqual(data["is_pleasant"], self.habit.is_pleasant)
        self.assertEqual(data["frequency"], self.habit.frequency)
        self.assertEqual(data["duration"], self.habit.duration)
        self.assertEqual(data["reward"], self.habit.reward)
        self.assertIsNone(data["related_habit"])
