from datetime import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from habits.models import Habit
from habits.tasks import send_habit_reminders, send_single_habit_reminder
from users.models import User


class SendHabitRemindersTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123", telegram_id="123456789")

    @patch("habits.tasks.enqueue_due_habits")
    def test_send_habit_reminders_success(self, mock_enqueue):
        mock_enqueue.return_value = {"enqueued": 2, "skipped": 1, "errors": 0}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            # Настраиваем mock для трех вызовов timezone.now()
            mock_now.side_effect = [base_time, base_time, base_time]

            result = send_habit_reminders()

            self.assertEqual(result, {"enqueued": 2, "skipped": 1, "errors": 0})
            mock_enqueue.assert_called_once_with(now=timezone.localtime(base_time))

    @patch("habits.tasks.enqueue_due_habits")
    def test_send_habit_reminders_empty_stats(self, mock_enqueue):
        mock_enqueue.return_value = {}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            # Настраиваем mock для трех вызовов timezone.now()
            mock_now.side_effect = [base_time, base_time, base_time]

            result = send_habit_reminders()

            self.assertEqual(result, {})

    @patch("habits.tasks.enqueue_due_habits")
    def test_send_habit_reminders_with_elapsed_time(self, mock_enqueue):
        mock_enqueue.return_value = {"enqueued": 1, "skipped": 0, "errors": 0}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            later_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 1))
            # Настраиваем mock для трех вызовов timezone.now()
            mock_now.side_effect = [base_time, later_time, later_time]

            result = send_habit_reminders()

            self.assertEqual(result, {"enqueued": 1, "skipped": 0, "errors": 0})


class SendSingleHabitReminderTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="testpass123", telegram_id="123456789")
        self.habit = Habit.objects.create(
            user=self.user, place="Home", time="10:00:00", action="Exercise", frequency=1
        )

    @patch("habits.tasks.process_single_habit")
    def test_send_single_habit_reminder_success(self, mock_process):
        mock_process.return_value = {"sent": 1, "skipped": 0, "errors": 0}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            mock_now.return_value = base_time

            result = send_single_habit_reminder(self.habit.id)

            self.assertEqual(result, {"sent": 1, "skipped": 0, "errors": 0})
            mock_process.assert_called_once_with(habit_id=self.habit.id, now=timezone.localtime(base_time))

    @patch("habits.tasks.process_single_habit")
    def test_send_single_habit_reminder_skipped(self, mock_process):
        mock_process.return_value = {"sent": 0, "skipped": 1, "errors": 0}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            mock_now.return_value = base_time

            result = send_single_habit_reminder(self.habit.id)

            self.assertEqual(result, {"sent": 0, "skipped": 1, "errors": 0})

    @patch("habits.tasks.process_single_habit")
    def test_send_single_habit_reminder_error(self, mock_process):
        mock_process.return_value = {"sent": 0, "skipped": 0, "errors": 1}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            mock_now.return_value = base_time

            result = send_single_habit_reminder(self.habit.id)

            self.assertEqual(result, {"sent": 0, "skipped": 0, "errors": 1})

    @patch("habits.tasks.process_single_habit")
    def test_send_single_habit_reminder_nonexistent_habit(self, mock_process):
        mock_process.return_value = {"sent": 0, "skipped": 0, "errors": 1}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            mock_now.return_value = base_time

            result = send_single_habit_reminder(999)

            self.assertEqual(result, {"sent": 0, "skipped": 0, "errors": 1})
            mock_process.assert_called_once_with(habit_id=999, now=timezone.localtime(base_time))

    @patch("habits.tasks.process_single_habit")
    def test_send_single_habit_reminder_empty_stats(self, mock_process):
        mock_process.return_value = {}

        with patch("habits.tasks.timezone.now") as mock_now:
            base_time = timezone.make_aware(datetime(2023, 1, 1, 10, 0, 0))
            mock_now.return_value = base_time

            result = send_single_habit_reminder(self.habit.id)

            self.assertEqual(result, {})


class TaskConfigurationTest(TestCase):
    def test_send_habit_reminders_retry_configuration(self):
        task = send_habit_reminders

        self.assertTrue(task.autoretry_for)
        self.assertTrue(task.retry_backoff)
        self.assertTrue(task.retry_jitter)
        self.assertEqual(task.max_retries, 5)

    def test_send_single_habit_reminder_retry_configuration(self):
        task = send_single_habit_reminder

        self.assertTrue(task.autoretry_for)
        self.assertTrue(task.retry_backoff)
        self.assertTrue(task.retry_jitter)
        self.assertEqual(task.max_retries, 5)

    def test_tasks_are_shared_tasks(self):
        self.assertTrue(hasattr(send_habit_reminders, "delay"))
        self.assertTrue(hasattr(send_single_habit_reminder, "delay"))
