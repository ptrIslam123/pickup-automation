import re
import time
from typing import Optional
from fuzzywuzzy import fuzz
from playwright.sync_api import Playwright, sync_playwright

from leo_bot import LeoBot
from global_config import Config, LIKE

def check_subscription(userid: str, host: str, port: int) -> bool:
    import requests
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
    endpoint_url = f"http://{host}:{port}/check"
    payload = {
        "user_id": userid
    }
    
    try:
        # Отправляем POST запрос
        response = requests.post(
            endpoint_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5  # Таймаут 5 секунд
        )
        
        # Проверяем статус ответа
        response.raise_for_status()
        
        # Возвращаем распарсенный JSON
        response = response.json()
        access: bool = response['access']
        if access:
            print("checking success")
            return True
        else:
            print("checking unsuccess")
        
        reason: Optional[str] = response['reason']
        if reason is not None:
            print(f"Reason: {reason}")
        else:
            print("Unknwon reason")
            
        expires_at: Optional[str] = response['expires_at']
        if expires_at is not None:
            print(f"Expires At: {expires_at}")
        else:
            print("Unknwon expiration time")
        return False
        
    except requests.exceptions.ConnectionError:
        return {
            "access": False,
            "expires_at": None,
            "reason": "connection_error"
        }
    except requests.exceptions.Timeout:
        return {
            "access": False,
            "expires_at": None,
            "reason": "timeout"
        }
    except requests.exceptions.HTTPError as e:
        return {
            "access": False,
            "expires_at": None,
            "reason": f"http_error_{response.status_code}"
        }
    except Exception as e:
        print(f"{str(e)}")
        return {
            "access": False,
            "expires_at": None,
            "reason": f"error: {str(e)}"
        }


def main(playwright: Playwright):
    host = "0.0.0.0"
    port = 8000
    userid = "test_user"
    if not check_subscription(userid, host, port):
        return
    
    wait_timeout = 5
    
    bot = LeoBot()
    bot.login(playwright=playwright)
    
    while True:
        time.sleep(wait_timeout)
        (text, images) = bot.extract_web_content()
        
        last_3_text = '\n'.join(text[-4:])
        if bot.is_stop(last_3_text):
            break
        
        last_text = text[-1]
        # if bot.is_spam(last_text):
        #     bot.enter("1")
        #     continue
        
        if bot.is_match(last_text):
            bot.enter("1")
            continue
        
        # if bot.is_profile_url(last_text):
        #     #
        #     continue
        
        if bot.is_menu(last_text):
            bot.enter("1")
            continue
        
        # TODO: by filter
        bot.enter(message=LIKE)


with sync_playwright() as playwright:
    main(playwright)


