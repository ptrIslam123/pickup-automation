
"""
Серверный модуль верификации подписок.
Минималистичная реализация с SQLite.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from typing import Tuple, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Создание Flask приложения
app = Flask(__name__)
CORS(app)  # Разрешаем запросы с любых доменов

# Конфигурация
DATABASE = 'subscriptions.db'


def get_db():
    """Возвращает соединение с базой данных."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создает таблицу, если её нет."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Самая минимальная таблица: id, user_id, expires_at
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL
        )
    ''')
    
    # Индекс для быстрого поиска по user_id
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON subscriptions(user_id)')
    
    conn.commit()
    conn.close()
    
    logger.info("База данных инициализирована")


def check_subscription_in_db(user_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Проверяет статус подписки в БД.
    
    Returns:
        (access, expires_at, reason)
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Ищем пользователя
    cursor.execute(
        "SELECT expires_at FROM subscriptions WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    
    # Если пользователь не найден
    if not row:
        return False, None, "user_not_found"
    
    # Получаем expires_at
    expires_at_str = row['expires_at']
    
    # Текущее время в UTC
    now = datetime.now(timezone.utc)
    
    try:
        # Пробуем распарсить дату из БД
        # Поддерживаем форматы: '2026-03-23 23:59:59' и '2026-03-23T23:59:59Z'
        expires_at = None
        
        if 'T' in expires_at_str:
            # ISO формат
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        else:
            # Простой формат 'YYYY-MM-DD HH:MM:SS'
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        # Сравниваем
        if expires_at > now:
            return True, expires_at.isoformat().replace('+00:00', 'Z'), None
        else:
            return False, None, "subscription_expired"
            
    except Exception as e:
        logger.error(f"Ошибка парсинга даты {expires_at_str}: {e}")
        return False, None, "invalid_date_format"


@app.route('/check', methods=['POST'])
def check():
    """
    Эндпоинт проверки подписки.
    
    Ожидает JSON:
    {
        "user_id": "user_123"
    }
    
    Возвращает:
    {
        "access": true/false,
        "expires_at": "2026-03-23T23:59:59Z" или null,
        "reason": "user_not_found/subscription_expired" или null
    }
    """
    # Логируем входящий запрос
    logger.info(f"Запрос от {request.remote_addr}")
    
    # Проверяем метод
    if request.method != 'POST':
        return jsonify({
            "access": False,
            "expires_at": None,
            "reason": "method_not_allowed"
        }), 405
    
    # Получаем JSON
    data = request.get_json()
    
    # Валидация
    if not data:
        return jsonify({
            "access": False,
            "expires_at": None,
            "reason": "invalid_json"
        }), 400
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({
            "access": False,
            "expires_at": None,
            "reason": "missing_user_id"
        }), 400
    
    # Проверяем в БД
    access, expires_at, reason = check_subscription_in_db(user_id)
    
    # Формируем ответ
    response = {
        "access": access,
        "expires_at": expires_at,
        "reason": reason
    }
    
    logger.info(f"Ответ для {user_id}: access={access}, reason={reason}")
    return jsonify(response)


# ========== АДМИНСКИЕ ФУНКЦИИ (для ручного управления) ==========

def add_subscription(user_id: str, days: int = 30):
    """
    Добавляет или продлевает подписку.
    Запускается из командной строки.
    
    Пример:
        python server.py add user_123 30
    """
    from datetime import timedelta
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=days)
    expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # INSERT OR REPLACE - если user_id уже есть, обновит expires_at
    cursor.execute('''
        INSERT OR REPLACE INTO subscriptions (user_id, expires_at)
        VALUES (?, ?)
    ''', (user_id, expires_at_str))
    
    conn.commit()
    conn.close()
    
    logger.info(f"Подписка для {user_id} активирована до {expires_at_str}")
    print(f"OK: {user_id} активен до {expires_at_str}")


def list_subscriptions():
    """Показывает все подписки."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, user_id, expires_at FROM subscriptions ORDER BY expires_at
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n{'ID':<5} {'USER_ID':<20} {'EXPIRES_AT (UTC)':<20}")
    print("-" * 50)
    
    for row in rows:
        print(f"{row['id']:<5} {row['user_id']:<20} {row['expires_at']:<20}")
    
    print(f"\nВсего: {len(rows)} записей")


def delete_subscription(user_id: str):
    """Удаляет подписку."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted:
        logger.info(f"Подписка {user_id} удалена")
        print(f"OK: {user_id} удален")
    else:
        print(f"Ошибка: {user_id} не найден")



def generate_user_id(length: int = 16) -> str:
    import string
    import secrets
    """
    Генерирует случайный URL-safe user_id.
    
    Args:
        length: Длина генерируемой строки (по умолчанию 16)
        
    Returns:
        Случайная строка из букв (верхний/нижний регистр) и цифр
        
    Пример:
        >>> generate_user_id()
        'xK7qP9mR2vL5nJ3f'
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# ========== ТОЧКА ВХОДА ==========

if __name__ == '__main__':
    import sys
    
    # Инициализируем БД при запуске
    init_db()
    
    # Обработка аргументов командной строки для админки
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == 'add' and len(sys.argv) >= 3:
            user_id = sys.argv[2]
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
            add_subscription(user_id, days)
            
        elif cmd == 'list':
            list_subscriptions()
            
        elif cmd == 'delete' and len(sys.argv) >= 3:
            delete_subscription(sys.argv[2])
            
        elif cmd == 'help':
            print("""
Команды:
  python server.py add USER_ID [DAYS]  - активировать подписку (по умолч. 30 дней)
  python server.py list                 - показать все подписки
  python server.py delete USER_ID       - удалить подписку
  python server.py run                   - запустить веб-сервер
            """)
            
        elif cmd == 'run':
            # Запуск веб-сервера
            app.run(host='0.0.0.0', port=8000, debug=True)
        else:
            print("Неизвестная команда. Используйте: python server.py help")
    else:
        # По умолчанию запускаем сервер
        app.run(host='0.0.0.0', port=8000, debug=True)