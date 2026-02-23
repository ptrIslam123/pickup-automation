import re

from typing import Optional
from bs4 import BeautifulSoup
import hashlib
from playwright.sync_api import Playwright

class Profile:
    def __init__(self):
        self.__hash = int()
        self.__name = str()
        self.__age = str()
        self.__location = str()
        self.__description = str()
        self.__images = list()

    def get_hash(self) -> int:
        return self.__hash
    
    def get_name(self) -> str:
        return self.__name
    
    def get_age(self) -> int:
        return self.__age
    
    def get_location(self) -> int:
        return self.__location
    
    def get_description(self) -> str:
        return self.__description
    
    def get_images(self) -> list:
        return self.__images
    
    def __repr__(self):
        return (f"Profile(\n"
                f"\thash={self.get_hash()}"
                f"\tname={self.get_name()},\n"
                f"\tage={self.get_age()},\n"
                f"\tdescriptions={self.get_description()}\n)")

    @staticmethod
    def download_image_as_bytes(page, image_url: str) -> bytes:
        """
        Скачивает одно изображение по blob URL и возвращает его как bytes без сохранения на диск
        """
        import base64
        
        try:
            # Используем существующую страницу для скачивания blob
            result = page.evaluate("""
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

    @staticmethod
    def extract_web_content(page_content: str) -> tuple[list, list]:
        soup = BeautifulSoup(page_content, 'html.parser')
        
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


    @staticmethod
    def __gen_hash(name: str, age: int, location: str, description: str) -> str:
        combined_string = f"{name}{str(age)}{location}{description}"

        # Encode the string to bytes (required for hashing)
        combined_bytes = combined_string.encode('utf-8')

        # Create a SHA-256 hash object
        hash_object = hashlib.sha256()

        # Update the hash object with the combined bytes
        hash_object.update(combined_bytes)

        # Get the hexadecimal representation of the hash
        hash_hex = hash_object.hexdigest()
        return hash_hex
