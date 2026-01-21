from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from httpx import RequestError, Response

from users.services import TelegramNotificationService, get_telegram_service


class TelegramNotificationServiceTests(TestCase):
    """Тесты сервиса TelegramNotificationService"""

    def setUp(self):
        self.service = TelegramNotificationService()
        self.telegram_id = "123456789"
        self.message = "Тестовое сообщение"

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET="test-secret")
    def test_init_with_settings(self):
        """Тест инициализации с настройками"""
        service = TelegramNotificationService()
        self.assertEqual(service.telegram_api_base_url, "http://test-api.com")
        self.assertEqual(service.bot_secret, "test-secret")

    def test_init_without_settings(self):
        """Тест инициализации без настроек"""
        with override_settings(TELEGRAM_API_BASE_URL=None, TELEGRAM_BOT_SECRET=None):
            service = TelegramNotificationService()
            self.assertIsNone(service.telegram_api_base_url)
            self.assertIsNone(service.bot_secret)

    @override_settings(TELEGRAM_API_BASE_URL=None, TELEGRAM_BOT_SECRET="test-secret")
    def test_send_message_no_api_url(self):
        """Тест отправки сообщения без URL API"""
        result = self.service.send_message(self.telegram_id, self.message)
        self.assertFalse(result)

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET=None)
    def test_send_message_no_secret(self):
        """Тест отправки сообщения без секрета"""
        result = self.service.send_message(self.telegram_id, self.message)
        self.assertFalse(result)

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET="test-secret")
    @patch("users.services.httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Тест успешной отправки сообщения"""
        # Создаем сервис с нужными настройками
        with override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET="test-secret"):
            service = TelegramNotificationService()

            # Настраиваем мок ответа
            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = service.send_message(self.telegram_id, self.message)

            self.assertTrue(result)
            mock_client.post.assert_called_once_with(
                "http://test-api.com/send/",
                json={"telegram_id": self.telegram_id, "message": self.message},
                headers={
                    "X-BOT-SECRET": "test-secret",
                    "Content-Type": "application/json",
                },
            )

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET="test-secret")
    @patch("users.services.httpx.Client")
    def test_send_message_server_error(self, mock_client_class):
        """Тест отправки сообщения с ошибкой сервера"""
        # Настраиваем мок ответа с ошибкой
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.service.send_message(self.telegram_id, self.message)

        self.assertFalse(result)

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET="test-secret")
    @patch("users.services.httpx.Client")
    def test_send_message_network_error(self, mock_client_class):
        """Тест отправки сообщения с ошибкой сети"""
        # Настраиваем мок для выброса исключения сети
        mock_client = Mock()
        mock_client.post.side_effect = RequestError("Network error")
        mock_client_class.return_value.__enter__.return_value = mock_client

        result = self.service.send_message(self.telegram_id, self.message)

        self.assertFalse(result)

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com/", TELEGRAM_BOT_SECRET="test-secret")
    @patch("users.services.httpx.Client")
    def test_send_message_url_trailing_slash(self, mock_client_class):
        """Тест правильной обработки URL с завершающим слэшем"""
        with override_settings(TELEGRAM_API_BASE_URL="http://test-api.com/", TELEGRAM_BOT_SECRET="test-secret"):
            service = TelegramNotificationService()

            mock_response = Mock(spec=Response)
            mock_response.status_code = 200
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__enter__.return_value = mock_client

            result = service.send_message(self.telegram_id, self.message)

            self.assertTrue(result)
            # Проверяем, что URL правильно сформирован (без двойного слэша)
            mock_client.post.assert_called_once_with(
                "http://test-api.com/send/",
                json={"telegram_id": self.telegram_id, "message": self.message},
                headers={
                    "X-BOT-SECRET": "test-secret",
                    "Content-Type": "application/json",
                },
            )


class GetTelegramServiceTests(TestCase):
    """Тесты функции get_telegram_service"""

    def test_get_telegram_service_singleton(self):
        """Тест, что функция возвращает один и тот же экземпляр"""
        service1 = get_telegram_service()
        service2 = get_telegram_service()

        self.assertIs(service1, service2)
        self.assertIsInstance(service1, TelegramNotificationService)

    @patch("users.services._telegram_service", None)
    def test_get_telegram_service_lazy_init(self):
        """Тест ленивой инициализации сервиса"""
        with patch("users.services.TelegramNotificationService") as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance

            service = get_telegram_service()

            mock_service_class.assert_called_once()
            self.assertIs(service, mock_instance)


class TelegramNotificationServiceLoggingTests(TestCase):
    """Тесты логирования сервиса"""

    @patch("users.services.logger")
    def test_init_logging_warnings(self, mock_logger):
        """Тест логирования предупреждений при инициализации"""
        with override_settings(TELEGRAM_API_BASE_URL=None, TELEGRAM_BOT_SECRET=None):
            TelegramNotificationService()

        # Проверяем, что предупреждения logged
        mock_logger.warning.assert_any_call("TELEGRAM_API_BASE_URL не настроен (например: http://127.0.0.1:8001)")
        mock_logger.warning.assert_any_call("TELEGRAM_BOT_SECRET не настроен")

    @override_settings(TELEGRAM_API_BASE_URL=None, TELEGRAM_BOT_SECRET="test-secret")
    @patch("users.services.logger")
    def test_send_message_no_api_url_logging(self, mock_logger):
        """Тест логирования ошибки при отсутствии URL API"""
        service = TelegramNotificationService()
        service.send_message("123", "test")

        mock_logger.error.assert_called_with("TELEGRAM_API_BASE_URL не настроен — отправка невозможна")

    @override_settings(TELEGRAM_API_BASE_URL="http://test-api.com", TELEGRAM_BOT_SECRET=None)
    @patch("users.services.logger")
    def test_send_message_no_secret_logging(self, mock_logger):
        """Тест логирования ошибки при отсутствии секрета"""
        service = TelegramNotificationService()
        service.send_message("123", "test")

        mock_logger.error.assert_called_with("TELEGRAM_BOT_SECRET не настроен — отправка невозможна")
