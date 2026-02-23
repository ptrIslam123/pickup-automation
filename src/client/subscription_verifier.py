"""
Модуль верификации подписки для клиентского приложения.
Использует NTP для получения точного времени и кэширует статус подписки локально.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

import requests
import ntplib

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SubscriptionValidator:
    """
    Валидатор подписок для клиентского приложения.
    
    Особенности:
    - Проверяет подписку через сервер
    - Кэширует статус локально для работы офлайн
    - Использует NTP для защиты от перевода часов
    - Поддерживает принудительную проверку при истечении срока
    
    Пример использования:
        validator = SubscriptionValidator(
            server_url="https://api.example.com",
            user_id="user_123",
            cache_file="subscription.cache"
        )
        
        if validator.is_subscription_active():
            print("Доступ разрешен")
            validator.run_application()
        else:
            print("Требуется оплата")
    """
    
    def __init__(
        self,
        server_url: str,
        user_id: str,
        cache_file: str = "subscription.cache",
        ntp_server: str = "pool.ntp.org",
        max_cache_days: int = 30,
        request_timeout: int = 5
    ):
        """
        Инициализация валидатора.
        
        Args:
            server_url: URL сервера для проверки подписок
            user_id: Идентификатор пользователя
            cache_file: Путь к файлу кэша
            ntp_server: NTP сервер для получения точного времени
            max_cache_days: Максимальный срок хранения кэша (дни)
            request_timeout: Таймаут запросов в секундах
        """
        self.server_url = server_url.rstrip('/')
        self.user_id = user_id
        self.cache_file = cache_file
        self.ntp_server = ntp_server
        self.max_cache_days = max_cache_days
        self.request_timeout = request_timeout
        
        self.ntp_client = ntplib.NTPClient()
        self.session = requests.Session()
        
        logger.info(f"Инициализирован валидатор для пользователя {user_id}")
    
    def get_trusted_time(self) -> Optional[datetime]:
        """
        Получает точное текущее время от NTP сервера.
        
        Returns:
            datetime объект с UTC временем или None при ошибке
        """
        try:
            response = self.ntp_client.request(self.ntp_server, version=3, timeout=3)
            trusted_time = datetime.fromtimestamp(response.tx_time)
            logger.debug(f"Получено доверенное время: {trusted_time}")
            return trusted_time
        except Exception as e:
            logger.warning(f"Не удалось получить время с NTP: {e}")
            return None
    
    def _verify_with_server(self) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """
        Проверяет статус подписки на сервере.
        
        Returns:
            Кортеж (доступ разрешен, expires_at, причина отказа)
        """
        try:
            # Формируем запрос
            payload = {
                "user_id": self.user_id
            }
            
            logger.info(f"Отправка запроса на сервер: {self.server_url}/check")
            
            # Отправляем POST запрос
            response = self.session.post(
                f"{self.server_url}/check",
                json=payload,
                timeout=self.request_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # Проверяем статус ответа
            if response.status_code != 200:
                logger.error(f"Сервер вернул код {response.status_code}")
                return False, None, f"server_error_{response.status_code}"
            
            # Парсим JSON
            data = response.json()
            
            # Проверяем обязательное поле access
            if 'access' not in data:
                logger.error("Ответ сервера не содержит поле 'access'")
                return False, None, "invalid_response"
            
            access = data['access']
            expires_at = None
            reason = data.get('reason')
            
            # Если есть expires_at, парсим его
            if data.get('expires_at'):
                try:
                    expires_at = datetime.fromisoformat(
                        data['expires_at'].replace('Z', '+00:00')
                    )
                except (ValueError, AttributeError):
                    logger.warning("Не удалось распарсить expires_at")
            
            logger.info(f"Ответ сервера: access={access}, expires_at={expires_at}")
            return access, expires_at, reason
            
        except requests.exceptions.Timeout:
            logger.error("Таймаут при обращении к серверу")
            return False, None, "timeout"
        except requests.exceptions.ConnectionError:
            logger.error("Не удалось подключиться к серверу")
            return False, None, "connection_error"
        except ValueError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return False, None, "json_error"
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return False, None, "unknown_error"
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """
        Загружает данные из кэш-файла.
        
        Returns:
            Словарь с данными кэша или None
        """
        if not os.path.exists(self.cache_file):
            return None
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру
            if 'expires_at' not in data:
                return None
            
            # Конвертируем строку в datetime
            data['expires_at'] = datetime.fromisoformat(data['expires_at'])
            
            # Проверяем срок давности кэша
            if 'cached_at' in data:
                cached_at = datetime.fromisoformat(data['cached_at'])
                if datetime.now() - cached_at > timedelta(days=self.max_cache_days):
                    logger.info("Кэш устарел (старше {self.max_cache_days} дней)")
                    return None
            
            logger.info(f"Загружен кэш: expires_at={data['expires_at']}")
            return data
            
        except Exception as e:
            logger.warning(f"Ошибка загрузки кэша: {e}")
            return None
    
    def _save_cache(self, expires_at: datetime) -> None:
        """
        Сохраняет данные в кэш-файл.
        
        Args:
            expires_at: Дата окончания подписки
        """
        try:
            data = {
                'expires_at': expires_at.isoformat(),
                'cached_at': datetime.now().isoformat(),
                'user_id': self.user_id
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Кэш сохранен: expires_at={expires_at}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения кэша: {e}")
    
    def _clear_cache(self) -> None:
        """Удаляет кэш-файл."""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.info("Кэш очищен")
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
    
    def is_subscription_active(self, force_server_check: bool = False) -> bool:
        """
        Проверяет, активна ли подписка.
        
        Алгоритм:
        1. Если force_server_check=True → запрос к серверу
        2. Иначе проверяет кэш
        3. Если кэш есть и доверенное время < expires_at → True
        4. Иначе запрос к серверу
        
        Args:
            force_server_check: Принудительно проверить на сервере
            
        Returns:
            True если подписка активна, False в противном случае
        """
        # Принудительная проверка на сервере
        if force_server_check:
            logger.info("Принудительная проверка на сервере")
            access, expires_at, reason = self._verify_with_server()
            
            if access and expires_at:
                self._save_cache(expires_at)
                return True
            else:
                self._clear_cache()
                if reason:
                    logger.info(f"Доступ запрещен: {reason}")
                return False
        
        # Проверяем кэш
        cached = self._load_cache()
        if not cached:
            logger.info("Кэш не найден")
            return self.is_subscription_active(force_server_check=True)
        
        expires_at = cached['expires_at']
        
        # Получаем доверенное время
        trusted_now = self.get_trusted_time()
        if not trusted_now:
            logger.warning("Не удалось получить доверенное время, считаем подписку неактивной")
            return self.is_subscription_active(force_server_check=True)
        
        # Сравниваем с доверенным временем
        if trusted_now < expires_at:
            logger.info(f"Подписка активна по кэшу до {expires_at}")
            return True
        else:
            logger.info("Срок подписки истек по данным NTP")
            return self.is_subscription_active(force_server_check=True)
    
    def get_subscription_info(self) -> Dict[str, Any]:
        """
        Получает полную информацию о подписке.
        
        Returns:
            Словарь с информацией о подписке
        """
        # Пробуем получить с сервера
        access, expires_at, reason = self._verify_with_server()
        
        if access and expires_at:
            self._save_cache(expires_at)
            return {
                'active': True,
                'expires_at': expires_at.isoformat(),
                'source': 'server'
            }
        
        # Если сервер недоступен, смотрим кэш
        cached = self._load_cache()
        if cached:
            trusted_now = self.get_trusted_time()
            is_active = trusted_now and trusted_now < cached['expires_at']
            
            return {
                'active': is_active,
                'expires_at': cached['expires_at'].isoformat(),
                'source': 'cache',
                'note': 'Данные из кэша, может быть неактуально'
            }
        
        return {
            'active': False,
            'expires_at': None,
            'source': 'none',
            'reason': reason or 'no_subscription'
        }
    
    def run_application(self) -> None:
        """
        Запускает приложение с проверкой подписки.
        Если подписка неактивна, выводит сообщение и завершает работу.
        """
        if self.is_subscription_active():
            logger.info("=" * 50)
            logger.info("ПОДПИСКА АКТИВНА. ЗАПУСК ПРИЛОЖЕНИЯ.")
            logger.info("=" * 50)
            # Здесь будет вызов основного кода приложения
            # main_app_function()
        else:
            info = self.get_subscription_info()
            reason = info.get('reason', 'subscription_inactive')
            
            print("\n" + "=" * 60)
            print("   ДОСТУП ЗАПРЕЩЕН")
            print("=" * 60)
            
            if reason == "subscription_expired":
                print("   Срок действия подписки истек.")
            elif reason == "user_not_found":
                print("   Подписка не найдена. Оформите подписку.")
            elif reason in ["timeout", "connection_error"]:
                print("   Не удалось проверить подписку. Проверьте интернет.")
            else:
                print("   Для доступа к программе оформите подписку.")
            
            print("\n   Как оплатить:")
            print("   1. Переведите 500₽ на карту 1234 5678 9012 3456")
            print("   2. Отправьте квитанцию в Telegram @support")
            print("   3. После подтверждения перезапустите программу")
            print("=" * 60)
            
            sys.exit(1)


# Пример использования
if __name__ == "__main__":
    import sys
    
    # Конфигурация
    SERVER_URL = "https://your-server.ru"  # Замени на свой URL
    USER_ID = "test_user_123"  # Здесь должен быть реальный ID пользователя
    
    # Создаем валидатор
    validator = SubscriptionValidator(
        server_url=SERVER_URL,
        user_id=USER_ID,
        cache_file="subscription.cache",
        ntp_server="pool.ntp.org"  # Можно заменить на ru.pool.ntp.org для России
    )
    
    # Запускаем приложение с проверкой
    validator.run_application()
    
    # Если дошли сюда - подписка активна
    print("\nЗапуск основного функционала...")
    # Здесь твой основной код