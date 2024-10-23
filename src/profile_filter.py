from profile_parser import Profile
import requests
import json
import re
from typing import Optional, List, Dict, Any

class AIProfileFilter:
    def __init__(self, model: str, host: str, port: str):
        self.__url = f"http://{host}:{port}/api/generate"
        self.__model = model
        

    def __qwen(self, prompt: str) -> List[Dict[str, Any]]:
        """Выполняет запрос к модели и возвращает ответ"""
        payload = {
            "model": self.__model,
            "prompt": prompt,
            "stream": False,
        }
        response = list()
        try:
            with requests.post(self.__url, json=payload, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        data = json.loads(line)
                        response.append(data)
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к модели: {e}")
            raise
        return response

    def __parse_rating(self, response: List[Dict[str, Any]]) -> Optional[int]:
        """Парсит числовой рейтинг из ответа модели"""
        if not response:
            return None
            
        # Собираем весь текст из ответа
        full_text = ""
        for item in response:
            if 'response' in item:
                full_text += item['response']
        
        # Ищем числовые значения от 0 до 10 в тексте
        # Вариант 1: Ищем явные упоминания рейтинга
        patterns = [
            r'рейтинг[:\s]*(\d{1,2})/10',
            r'оценка[:\s]*(\d{1,2})/10',
            r'оцениваю[:\s]*(\d{1,2})/10',
            r'rating[:\s]*(\d{1,2})/10',
            r'score[:\s]*(\d{1,2})/10',
            r'(\d{1,2})/10',
            r'(\d{1,2})\s*балл',
            r'(\d{1,2})\s*очк',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, full_text.lower())
            if match:
                rating = int(match.group(1))
                if 0 <= rating <= 10:
                    return rating
        
        # Вариант 2: Ищем просто числа от 0 до 10 в контексте
        # Это менее точный метод, но может сработать
        numbers = re.findall(r'\b(\d{1,2})\b', full_text)
        for num in numbers:
            rating = int(num)
            if 0 <= rating <= 10:
                # Проверяем контекст вокруг числа
                idx = full_text.find(num)
                context = full_text[max(0, idx-20):min(len(full_text), idx+20)].lower()
                if any(word in context for word in ['оценка', 'рейтинг', 'балл', 'score', 'rating']):
                    return rating
        
        return None

    def filter(self, profile: Profile, threshold: int = 7) -> bool:
        """Фильтрует профиль на основе рейтинга от AI
        
        Args:
            profile: Профиль для оценки
            threshold: Пороговое значение рейтинга (по умолчанию 7/10)
        
        Returns:
            bool: True если профиль проходит фильтр, иначе False
        """
        assert profile.get_description() != str(), "Описание профиля не должно быть пустым"
        
        prompt = f"""
        I'm a 25-year-old guy, athletic, working, with a college degree, 
        from a good family, and looking for a kind and caring woman. 
        Below is a description of a woman's profile from a dating site. 
        
        Please provide a rating from 0 to 10 based on how well she fits my profile.
        Your response MUST include the rating in format: "Rating: X/10" where X is the number.
        Also provide a brief explanation for your rating.
        
        Profile description: '{profile.get_description()}'
        
        Please respond in English.
        """
        
        try:
            response = self.__qwen(prompt=prompt)
            rating = self.__parse_rating(response)
            
            if rating is None:
                print("Не удалось распознать рейтинг из ответа модели")
                return False
            
            print(f"AI рейтинг: {rating}/10 профиля: {profile.get_description()}")
            print("-----------------------------------------------------------------------------------------")
            
            return rating < threshold
            
        except Exception as e:
            print(f"Ошибка при фильтрации профиля: {e}")
            return False

    def get_detailed_rating(self, profile: Profile) -> Dict[str, Any]:
        """Получает детальный рейтинг с объяснением"""
        assert profile.get_description() != str(), "Описание профиля не должно быть пустым"
        
        prompt = f"""
        I'm a 25-year-old guy, athletic, working, with a college degree, 
        from a good family, and looking for a kind and caring woman. 
        
        Analyze this profile and provide:
        1. Rating from 0 to 10 (format: "Rating: X/10")
        2. Brief explanation
        3. Key compatibility factors
        
        Profile description: '{profile.get_description()}'
        
        Please respond in English.
        """
        
        try:
            response = self.__qwen(prompt=prompt)
            full_text = "".join([item.get('response', '') for item in response])
            
            rating = self.__parse_rating(response)
            
            return {
                "rating": rating,
                "full_response": full_text,
                "profile_id": getattr(profile, 'id', None),
                "success": rating is not None
            }
            
        except Exception as e:
            print(f"Ошибка при получении детального рейтинга: {e}")
            return {
                "rating": None,
                "full_response": str(e),
                "profile_id": getattr(profile, 'id', None),
                "success": False
            }