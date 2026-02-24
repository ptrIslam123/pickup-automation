import os
import time
import Levenshtein

from bs4 import BeautifulSoup
from playwright.sync_api import Playwright
from global_config import config
from ai import ask

class LeoBot:
    def __init__(self):
        self.__playwright = None
        self.__browser = None
        self.__context = None
        self.__page = None
        
    def login(self, playwright: Playwright):
        """
        Выполняет вход в Telegram Web и авторизацию в leomatchbot.
        
        Args:
            playwright: Экземпляр Playwright для управления браузером
        """
        self.__playwright = playwright
        browser_context_path = config.get_browser_context_path()
        
        # Запускаем браузер (один раз для всего метода)
        self.__browser = self.__playwright.chromium.launch(headless=False)
        
        if not os.path.exists(browser_context_path):
            # Первый вход - требуется авторизация
            self._first_time_login(browser_context_path)
        else:
            # Используем сохраненную сессию
            self._restore_session(browser_context_path)
        
        """
        Переходит к leomatchbot через поиск.
        """
        print("🔍 Поиск leomatchbot...")
        
        # Кликаем на поле поиска и вводим имя бота
        self.__page.get_by_placeholder(" ").click()
        self.__page.get_by_placeholder(" ").fill("@leomatchbot")
        
        # Ожидаем появления бота в результатах поиска
        self.__page.wait_for_selector("text=leomatchbot", timeout=5000)
        
        # Переходим в чат с ботом
        self.__page.locator("text=leomatchbot").first.click()
        print("✅ Успешно перешли в чат с leomatchbot")

    def _first_time_login(self, context_path: str):
        """
        Выполняет первый вход с сохранением сессии.
        
        Args:
            context_path: Путь для сохранения контекста браузера
        """
        print("🔄 Первый запуск. Выполняется авторизация в Telegram Web...")
        
        # Создаем новый контекст
        self.__context = self.__browser.new_context()
        self.__page = self.__context.new_page()
        self.__page.goto("https://web.telegram.org/k/")
        
        # Ждем ручной авторизации пользователя
        self._wait_for_telegram_auth(self.__page)
        
        # Сохраняем состояние сессии
        self.__context.storage_state(path=context_path)
        print("✅ Сессия сохранена")

    def _restore_session(self, context_path: str):
        """
        Восстанавливает сессию из сохраненного контекста.
        
        Args:
            context_path: Путь к файлу с сохраненной сессией
        """
        print("🔄 Восстановление сохраненной сессии...")
        self.__context = self.__browser.new_context(storage_state=context_path)
        self.__page = self.__context.new_page()
        self.__page.goto("https://web.telegram.org/k/")

    def _wait_for_telegram_auth(self, page):
        """
        Ожидает ручной авторизации пользователя в Telegram Web.
        
        Args:
            page: Страница браузера с открытым Telegram Web
        """
        print("⏳ Ожидание авторизации в Telegram Web...")
        print("   Пожалуйста, войдите в свой аккаунт в открывшемся окне браузера")
        
        while True:
            try:
                time.sleep(1)
                page.get_by_placeholder(" ").click()
                page.get_by_placeholder(" ").fill("@leomatchbot")
                page.wait_for_selector("text=leomatchbot", timeout=5000)
                break
            except Exception as _:
                print("Не загрузился еще!")
                continue
    
    def get_page(self):
        return self.__page
    
    def get_content(self):
        return self.__page.content()

    def enter(self, message):
        """Умный поиск кнопки отправки"""
        
        # Попробовать разные стратегии по порядку
        selectors = [
            # 1. По data-атрибутам (если есть)
            "[data-qa='send-button']",
            "[data-test='send-btn']",
            "[aria-label*='send' i]",
            "[title*='send' i]",
            
            # 2. По классам
            ".send-button",
            ".btn-send",
            ".input-button",
            "button[type='submit']",
            
            # 3. По позиции относительно input
            ".input-message-input ~ button",
            ".input-message-input + button",
            
            # 4. По частичному тексту (если символы меняются)
            'button:has-text("")',  # стабильный символ
            'button:has-text("")',
            
            # 5. По XPath с contains
            'xpath=//button[contains(text(), "")]',
            
            # 6. Последняя кнопка в контейнере
            ".chat-footer button:last-child",
        ]
        
        for selector in selectors:
            button = self.__page.locator(selector).first
            if button.count() > 0:
                self.__page.locator(".input-message-input").first.click()
                self.__page.locator(".input-message-input").first.fill(message)
                button.click()
                return True
        
        # Если ничего не нашли - фоллбэк на координаты (нежелательно)
        self.__page.mouse.click(x=100, y=200)
        return False        
        
        
    def is_spam(self, text: str) -> bool:
        """
        Определяет, является ли текст спамом
        """
        req = f"""Ты - классификатор спама. Определи, является ли следующий текст спамом.
        
        Правила:
        1. Верни ТОЛЬКО одно слово: True или False
        2. True - если текст является спамом
        3. False - если текст не является спамом
        4. НЕ добавляй никаких пояснений, знаков препинания или дополнительного текста
        5. НЕ используй кавычки

        Текст для анализа: "{text}"

        Твой ответ (только True или False):
        """

        result = ask(req)
        
        # Очищаем результат от возможного мусора
        result = result.strip().lower()
        
        # Извлекаем True/False из ответа (на случай, если нейронка добавила лишнее)
        if 'true' in result:
            return True
        elif 'false' in result:
            return False
        else:
            # Если формат не распознан, логируем и возвращаем False по умолчанию
            print(f"Неожиданный формат ответа: {result}")
            return False
                
    
    def is_menu(self, text: str) -> bool:
        """
        1. Смотреть анкеты.\n2. Заполнить анкету заново.\n3. Изменить фото/видео.\n4. Изменить текст анкеты.
        
        
        Нашел 12053 девушек рядом с тобой. Показать?
        
        
        Ты понравился 1 девушке, показать её?
        
        1. Показать.
        2. Не хочу больше никого смотреть.
        """
        examples = [
            """
            1. Смотреть анкеты.
            2. Заполнить анкету заново.
            3. Изменить фото/видео.
            4. Изменить текст анкеты.
            """,
            """
            Несколько девушек из  хотят познакомиться с тобой прямо сейчас
            1. Посмотреть.
            2. Не интересно.
            """
        ]
        for example in examples:
            if self.__levenshtein_cmp(example, text, 0.6):
                return True
        return False
    
    def is_stop(self, text: str):
        """
        Слишком много ❤️ за сегодня.

        Пригласи друзей и получи больше ❤️!

        Перешли друзьям или размести в своих соцсетях.
        Вот твоя личная ссылка 👇
        """
        example = """
        Слишком много  за сегодня.
        Пригласи друзей и получи больше !
        Перешли друзьям или размести в своих соцсетях.
        Вот твоя личная ссылка\nБот знакомств Дайвинчик в Telegram! Найдет друзей или даже половинку 
        https://t.me/leomatchbot?start=
        Любые попытки купить или накрутить рефералов приводят к незамедлительной блокировке аккаунта.
        Кто-то тобой заинтересовался! Заканчивай с вопросом выше и посмотрим кто там'
        """
        return self.__levenshtein_cmp(example, text, 0.6)
    
    def is_match(self, text: str) -> bool:
        """
        Нашли кое-кого для тебя ;) Заканчивай с вопросом выше и увидишь кто это
        
        
        Ты понравился 1 девушке, показать её?

        1. Показать.
        2. Не хочу больше никого смотреть.
        
        """
        exampels = [
            """Нашли кое-кого для тебя ;) Заканчивай с вопросом выше и увидишь кто это""",
            """
            Ты понравился 1 девушке, показать её?
            1. Показать.
            2. Не хочу больше никого смотреть.
            """
        ]
        for example in exampels:
            if self.__levenshtein_cmp(example, text, 0.6) == True:
                return True
        return False


    def is_profile_url(self, text: str) -> bool:
        """
        Отлично! Надеюсь хорошо проведете время 🙌

        Начинай общаться 👉 Bunny
        """
        return False

    def download_image(self, image_url: str) -> bytes:
        """
        Скачивает одно изображение по blob URL и возвращает его как bytes без сохранения на диск
        """
        import base64
        
        try:
            # Используем существующую страницу для скачивания blob
            result = self.__page.evaluate("""
                (blobUrl) => {
                    return fetch(blobUrl)
                        .then(response => response.blob())
                        .then(blob => {
                            return new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                        })
                        .catch((error) => {
                            console.error('Fetch error:', error);
                            return null;
                        });
                }
            """, image_url)
            
            if result and result.startswith('data:'):
                # Извлекаем base64 данные
                header, encoded = result.split(',', 1)
                image_data = base64.b64decode(encoded)
                return image_data
            else:
                print(f"❌ Failed to download image: {image_url[:50]}...")
                return None
                
        except Exception as e:
            print(f"❌ Error downloading image: {e}")
            return None

    def extract_web_content(self) -> tuple[list, list]:
        soup = BeautifulSoup(self.__page.content(), 'html.parser')
        
        # 1. Находим контейнер с чатом
        chat_container = soup.find('div', class_='chat')
        if not chat_container:
            return None
        
        # 2. Ищем все сообщения в хронологическом порядке
        data = chat_container.find_all('div', attrs={'data-mid': True})
        
        text = []
        images = []
        for i, element in enumerate(data):
            text_elem = element.find('span', class_='translatable-message')
            if text_elem:
                text.append(text_elem.get_text().strip())
            
            media_imgs = element.find_all('img', class_='media-photo')
            for img in media_imgs:
                src = img.get('src')
                if src and src.startswith('blob:'):
                    images.append(src)
        
        return (text, images)

    def __levenshtein_cmp(self, text1: str, text2: str, threshold: float) -> bool:
            # Нормализуем тексты
        t1 = ' '.join(text1.lower().split())
        t2 = ' '.join(text2.lower().split())
        
        # Считаем расстояние
        distance = Levenshtein.distance(t1, t2)
        max_len = max(len(t1), len(t2))
        
        # Нормализованное сходство (1 - нормализованное расстояние)
        similarity = 1 - (distance / max_len) if max_len > 0 else 0
        
        return similarity >= threshold