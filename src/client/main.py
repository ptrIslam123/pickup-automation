import re
import time
import sqlite3

from fuzzywuzzy import fuzz
from playwright.sync_api import Playwright, sync_playwright

from leo_bot import LeoBot
from global_config import Config, LIKE

def check_subscription(userid: str, host: str, port: int) -> bool:
    import requests
    """
    Отправляет запрос на проверку подписки и возвращает ответ.
    
    Args:
        userid: ID пользователя для проверки
        endpoint_url: URL эндпоинта проверки подписки
    
    Returns:
        Словарь с полями: access, expires_at, reason
    """
    # Подготавливаем данные для отправки
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
        
        response.raise_for_status()
        
        response = response.json()
        
        access = response['access']
        if access:
            print("checking success")
            return True
        else:
            print("checking failed")
        
        reason = response['reason']
        if reason is not None:
            print(f"Reason={reason}")
        else:
            print("Unknown reason")
                
        expires_at = response['expires_at'] 
        if expires_at is not None:
            print(f"Expires at={expires_at}")
        else:
            print("Unknow expiration time")
        
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
        return {
            "access": False,
            "expires_at": None,
            "reason": f"error: {str(e)}"
        }

def main(playwright: Playwright):
    wait_timeout = 10
    
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


