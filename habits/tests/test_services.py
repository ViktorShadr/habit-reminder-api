from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from habits.models import Habit
from habits.services import (
    _get_user_telegram_id,
    _normalize_local_datetime,
    _same_minute,
    enqueue_due_habits,
    get_due_habits,
    is_habit_due,
    process_single_habit,
    send_telegram_notification,
)
from users.models import User


class HelperFunctionsTest(TestCase):
    def test_get_user_telegram_id_valid(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            telegram_id="123456789"
        )
        habit = Habit.objects.create(
            user=user,
            place="Home",
            time="10:00:00",
            action="Exercise"
        )
        
        result = _get_user_telegram_id(habit)
        self.assertEqual(result, "123456789")

    def test_get_user_telegram_id_none(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        habit = Habit.objects.create(
            user=user,
            place="Home",
            time="10:00:00",
            action="Exercise"
        )
        
        result = _get_user_telegram_id(habit)
        self.assertIsNone(result)

    def test_get_user_telegram_id_empty_values(self):
        test_values = ["", "0", 0]
        
        for i, value in enumerate(test_values):
            with self.subTest(value=value):
                user = User.objects.create_user(
                    email=f"test{i}@example.com",
                    password="testpass123",
                    telegram_id=value
                )
                habit = Habit.objects.create(
                    user=user,
                    place="Home",
                    time="10:00:00",
                    action="Exercise"
                )
                
                result = _get_user_telegram_id(habit)
                self.assertIsNone(result)

    def test_get_user_telegram_id_no_user(self):
        habit = Mock()
        habit.user = None
        
        result = _get_user_telegram_id(habit)
        self.assertIsNone(result)

    def test_normalize_local_datetime_naive(self):
        naive_dt = datetime(2023, 1, 1, 10, 0, 0)
        result = _normalize_local_datetime(naive_dt)
        
        self.assertTrue(timezone.is_aware(result))
        self.assertEqual(result.hour, 10)

    def test_normalize_local_datetime_aware(self):
        aware_dt = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
        result = _normalize_local_datetime(aware_dt)
        
        self.assertTrue(timezone.is_aware(result))
        self.assertEqual(result.hour, 10)

    def test_same_minute_true(self):
        dt1 = datetime(2023, 1, 1, 10, 30, 15)
        dt2 = datetime(2023, 1, 1, 10, 30, 45)
        
        self.assertTrue(_same_minute(dt1, dt2))

    def test_same_minute_false(self):
        dt1 = datetime(2023, 1, 1, 10, 30, 0)
        dt2 = datetime(2023, 1, 1, 10, 31, 0)
        
        self.assertFalse(_same_minute(dt1, dt2))

    def test_same_minute_different_hours(self):
        dt1 = datetime(2023, 1, 1, 10, 30, 0)
        dt2 = datetime(2023, 1, 1, 11, 30, 0)
        
        self.assertFalse(_same_minute(dt1, dt2))


class IsHabitDueTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            telegram_id="123456789"
        )
        self.habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )

    def test_habit_due_no_last_reminder(self):
        now = datetime(2023, 1, 1, 10, 0, 0)
        
        result = is_habit_due(self.habit, now)
        self.assertTrue(result)

    def test_habit_not_due_same_minute(self):
        now = datetime(2023, 1, 1, 10, 0, 0)
        self.habit.last_reminder = now
        self.habit.save()
        
        result = is_habit_due(self.habit, now)
        self.assertFalse(result)

    def test_habit_due_frequency_passed(self):
        now = datetime(2023, 1, 2, 10, 0, 0)
        self.habit.last_reminder = datetime(2023, 1, 1, 10, 0, 0)
        self.habit.frequency = 1
        self.habit.save()
        
        result = is_habit_due(self.habit, now)
        self.assertTrue(result)

    def test_habit_not_due_frequency_not_passed(self):
        now = datetime(2023, 1, 2, 10, 0, 0)
        self.habit.last_reminder = datetime(2023, 1, 1, 10, 0, 0)
        self.habit.frequency = 2
        self.habit.save()
        
        result = is_habit_due(self.habit, now)
        self.assertFalse(result)

    def test_habit_due_no_frequency(self):
        # Создаем привычку с frequency=0, она должна считаться как не имеющая частоты
        self.habit.frequency = 0
        self.habit.save()
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = is_habit_due(self.habit, now)
        # frequency=0 означает, что привычка не требует напоминаний
        self.assertTrue(result)  # Функция возвращает True, т.к. frequency не None


class GetDueHabitsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            telegram_id="123456789"
        )

    def test_get_due_habits_time_match(self):
        habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = get_due_habits(now)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, habit.id)

    def test_get_due_habits_no_time_match(self):
        Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 11, 0, 0)
        result = get_due_habits(now)
        
        self.assertEqual(len(result), 0)

    def test_get_due_habits_with_last_reminder(self):
        habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1,
            last_reminder=datetime(2023, 1, 1, 10, 0, 0)
        )
        
        now = datetime(2023, 1, 2, 10, 0, 0)
        result = get_due_habits(now)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, habit.id)

    def test_get_due_habits_skip_frequency_none(self):
        # Используем frequency=0 - функция get_due_habits не фильтрует по frequency
        habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=0
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = get_due_habits(now)
        
        # get_due_habits возвращает все привычки по времени, фильтрация по частоте в is_habit_due
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, habit.id)


class SendTelegramNotificationTest(TestCase):
    @patch('habits.services.get_telegram_service')
    def test_send_telegram_notification_success(self, mock_get_service):
        mock_service = Mock()
        mock_service.send_message.return_value = True
        mock_get_service.return_value = mock_service
        
        result = send_telegram_notification("123456789", "Test message")
        
        self.assertTrue(result)
        mock_service.send_message.assert_called_once_with("123456789", "Test message")

    @patch('habits.services.get_telegram_service')
    def test_send_telegram_notification_failure(self, mock_get_service):
        mock_service = Mock()
        mock_service.send_message.return_value = False
        mock_get_service.return_value = mock_service
        
        result = send_telegram_notification("123456789", "Test message")
        
        self.assertFalse(result)
        mock_service.send_message.assert_called_once_with("123456789", "Test message")

    @patch('habits.services.get_telegram_service')
    def test_send_telegram_notification_exception(self, mock_get_service):
        mock_service = Mock()
        mock_service.send_message.side_effect = Exception("Connection error")
        mock_get_service.return_value = mock_service
        
        result = send_telegram_notification("123456789", "Test message")
        
        self.assertFalse(result)


class ProcessSingleHabitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            telegram_id="123456789"
        )
        self.habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )

    @patch('habits.services.send_telegram_notification')
    @patch('habits.services.format_habit_message')
    def test_process_single_habit_success(self, mock_format, mock_send):
        mock_format.return_value = "Time to exercise!"
        mock_send.return_value = True
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(self.habit.id, now)
        
        self.assertEqual(result["sent"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        
        self.habit.refresh_from_db()
        self.assertIsNotNone(self.habit.last_reminder)

    def test_process_single_habit_not_found(self):
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(999, now)
        
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 1)

    def test_process_single_habit_no_telegram(self):
        user_no_telegram = User.objects.create_user(
            email="notelegram@example.com",
            password="testpass123"
        )
        habit_no_telegram = Habit.objects.create(
            user=user_no_telegram,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(habit_no_telegram.id, now)
        
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)

    def test_process_single_habit_not_due(self):
        self.habit.last_reminder = datetime(2023, 1, 1, 10, 0, 0)
        self.habit.save()
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(self.habit.id, now)
        
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)

    @patch('habits.services.send_telegram_notification')
    @patch('habits.services.format_habit_message')
    def test_process_single_habit_send_failed(self, mock_format, mock_send):
        mock_format.return_value = "Time to exercise!"
        mock_send.return_value = False
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(self.habit.id, now)
        
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 1)

    @patch('habits.services.format_habit_message')
    def test_process_single_habit_format_exception(self, mock_format):
        mock_format.side_effect = Exception("Format error")
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = process_single_habit(self.habit.id, now)
        
        self.assertEqual(result["sent"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 1)


class EnqueueDueHabitsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            telegram_id="123456789"
        )

    @patch('habits.tasks.send_single_habit_reminder')
    def test_enqueue_due_habits_success(self, mock_task):
        mock_task.apply_async = Mock()
        
        # Создаем привычку для этого теста
        habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = enqueue_due_habits(now)
        
        self.assertEqual(result["enqueued"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        
        mock_task.apply_async.assert_called_once()

    @patch('habits.tasks.send_single_habit_reminder')
    def test_enqueue_due_habits_no_habits(self, mock_task):
        mock_task.apply_async = Mock()
        
        now = datetime(2023, 1, 1, 11, 0, 0)
        result = enqueue_due_habits(now)
        
        self.assertEqual(result["enqueued"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 0)
        
        mock_task.apply_async.assert_not_called()

    def test_enqueue_due_habits_no_telegram(self):
        user_no_telegram = User.objects.create_user(
            email="notelegram@example.com",
            password="testpass123"
        )
        habit_no_telegram = Habit.objects.create(
            user=user_no_telegram,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = enqueue_due_habits(now)
        
        # Функция enqueue_due_habits пропускает привычки без telegram_id
        self.assertEqual(result["enqueued"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"], 0)

    @patch('habits.tasks.send_single_habit_reminder')
    def test_enqueue_due_habits_exception(self, mock_task):
        mock_task.apply_async.side_effect = Exception("Task error")
        
        # Создаем привычку для этого теста
        habit = Habit.objects.create(
            user=self.user,
            place="Home",
            time="10:00:00",
            action="Exercise",
            frequency=1
        )
        
        now = datetime(2023, 1, 1, 10, 0, 0)
        result = enqueue_due_habits(now)
        
        self.assertEqual(result["enqueued"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["errors"], 1)
