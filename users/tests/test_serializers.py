from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import serializers

from users.models import TelegramLink, User
from users.serializers import (
    TelegramConfirmSerializer,
    TelegramLinkCreateSerializer,
    UserCreateSerializer,
    UserSerializer,
)


class UserCreateSerializerTest(TestCase):
    def setUp(self):
        self.valid_data = {
            "email": "test@example.com",
            "password": "StrongPass123!",
            "phone_number": "+1234567890",
            "city": "Test City",
        }

    def test_create_user_with_valid_data(self):
        serializer = UserCreateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.email, self.valid_data["email"])
        self.assertEqual(user.phone_number, self.valid_data["phone_number"])
        self.assertEqual(user.city, self.valid_data["city"])
        self.assertTrue(user.check_password(self.valid_data["password"]))

    def test_create_user_with_minimal_data(self):
        minimal_data = {
            "email": "minimal@example.com",
            "password": "StrongPass123!",
        }
        
        serializer = UserCreateSerializer(data=minimal_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.email, minimal_data["email"])
        self.assertIsNone(user.phone_number)
        self.assertIsNone(user.city)

    def test_password_validation(self):
        invalid_data = self.valid_data.copy()
        invalid_data["password"] = "123"
        
        serializer = UserCreateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_email_required(self):
        data = self.valid_data.copy()
        del data["email"]
        
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_password_required(self):
        data = self.valid_data.copy()
        del data["password"]
        
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_write_only(self):
        serializer = UserCreateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        self.assertNotIn("password", serializer.data)


class UserSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            phone_number="+1234567890",
            city="Test City"
        )

    def test_serialization(self):
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["phone_number"], self.user.phone_number)
        self.assertEqual(data["city"], self.user.city)
        self.assertNotIn("password", data)

    def test_fields_contain_expected_fields(self):
        serializer = UserSerializer(self.user)
        expected_fields = {"email", "phone_number", "city", "avatar"}
        actual_fields = set(serializer.data.keys())
        
        self.assertEqual(expected_fields, actual_fields)


class TelegramLinkCreateSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.request = Mock()
        self.request.user = self.user

    def test_create_telegram_link(self):
        serializer = TelegramLinkCreateSerializer(
            context={"request": self.request}
        )
        
        result = serializer.create({})
            
        self.assertIn("code", result)
        self.assertIn("expires_at", result)
        self.assertIn("start_command", result)
        self.assertTrue(result["start_command"].startswith("/start "))
        
        link = TelegramLink.objects.get(user=self.user, code=result["code"])
        self.assertEqual(link.code, result["code"])
        self.assertFalse(link.is_used)
        self.assertFalse(link.is_expired)

    def test_expire_previous_links(self):
        old_link = TelegramLink.objects.create(
            user=self.user,
            code="OLD123456",
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        serializer = TelegramLinkCreateSerializer(
            context={"request": self.request}
        )
        serializer.create({})
        
        old_link.refresh_from_db()
        self.assertTrue(old_link.is_expired)

    def test_code_generation_format(self):
        serializer = TelegramLinkCreateSerializer(
            context={"request": self.request}
        )
        
        result = serializer.create({})
        code = result["code"]
        
        self.assertEqual(len(code), 10)
        self.assertTrue(code.isalnum())
        self.assertTrue(code.isupper())


class TelegramConfirmSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123"
        )
        self.valid_link = TelegramLink.objects.create(
            user=self.user,
            code="VALID123456",
            expires_at=timezone.now() + timedelta(minutes=15)
        )

    def test_confirm_valid_link(self):
        data = {
            "code": "VALID123456",
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        result = serializer.save()
        self.assertEqual(result["detail"], "Telegram успешно привязан.")
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, "123456789")
        
        self.valid_link.refresh_from_db()
        self.assertIsNotNone(self.valid_link.used_at)

    def test_code_validation_strips_and_uppercases(self):
        data = {
            "code": "  valid123456  ",
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "VALID123456")

    def test_confirm_nonexistent_code(self):
        data = {
            "code": "NONEXISTENT",
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        self.assertIn("code", cm.exception.detail)
        # Проверяем что есть ошибка по полю code
        self.assertIsNotNone(cm.exception.detail["code"][0])

    def test_confirm_used_code(self):
        self.valid_link.used_at = timezone.now()
        self.valid_link.save()
        
        data = {
            "code": "VALID123456",
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        self.assertIn("code", cm.exception.detail)
        # Проверяем что есть ошибка по полю code
        self.assertIsNotNone(cm.exception.detail["code"][0])

    def test_confirm_expired_code(self):
        self.valid_link.expires_at = timezone.now() - timedelta(minutes=1)
        self.valid_link.save()
        
        data = {
            "code": "VALID123456",
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        self.assertIn("code", cm.exception.detail)
        # Проверяем что есть ошибка по полю code
        self.assertIsNotNone(cm.exception.detail["code"][0])

    def test_chat_id_validation(self):
        data = {
            "code": "VALID123456",
            "chat_id": 0
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("chat_id", serializer.errors)

    def test_code_max_length(self):
        data = {
            "code": "A" * 33,
            "chat_id": 123456789
        }
        
        serializer = TelegramConfirmSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)
