import requests
import json

def ask(request: str) -> str:
    # Твой ключ
    API_KEY = "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"

    # Отправляем запрос
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # можно любой сайт
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": request}],
        }
    )

    # Проверяем и выводим
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        print(f"Ошибка {response.status_code}: {response.text}")
        
    return str()