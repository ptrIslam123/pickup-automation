import os
import sys
import subprocess
import logging

class Config:
    def __init__(self):
        self.__init_workdir()
        self.__init_logger()
        self.__init_playwright()
    
    def get_browser_context_path(self) -> str:
        return self.__browser_context_path
    
    def get_logger_path(self) -> str:
        return self.__logger_path
    
    def get_workdir(self) -> str:
        return self.__workdir
    
    def __init_workdir(self):
        self.__workdir = f"{os.path.dirname(os.path.abspath(__file__))}"
        self.__logger_path = f"{self.__workdir}/log"
        self.__browser_context_path = f"{self.__workdir}/browser_context"
    
    def __init_logger(self):
        logging.basicConfig(
            filename=self.__logger_path,
            filemode='w',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        )
    
    def __init_playwright(self):
        """
        Проверяет наличие браузера и устанавливает его при необходимости.
        Возвращает путь к исполняемому файлу браузера.
        """
        try:
            from playwright._impl._driver import compute_driver_executable
        except ImportError:
            logging.warning("❌ Playwright не установлен. Устанавливаю...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'playwright'])
            import playwright
        
        # Определяем путь к браузерам
        if getattr(sys, 'frozen', False):
            # Для скомпилированного приложения
            self.__browsers_path = os.path.join(os.path.dirname(sys.executable), 'ms-playwright')
        else:
            # Для разработки
            self.__browsers_path = os.path.expanduser('~/.cache/ms-playwright')
        
        # Создаем папку, если её нет
        os.makedirs(self.__browsers_path, exist_ok=True)
        
        # Устанавливаем переменную окружения
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = self.__browsers_path
        
        # Проверяем наличие Chromium
        chromium_path = None
        possible_patterns = [
            os.path.join(self.__browsers_path, 'chromium-*', 'chrome-linux64', 'chrome'),
            os.path.join(self.__browsers_path, 'chromium-*', 'chrome-win', 'chrome.exe'),  # для Windows
            os.path.join(self.__browsers_path, 'chromium-*', 'chrome-mac', 'Chromium.app', 'Contents', 'MacOS', 'Chromium'),  # для Mac
        ]
        
        import glob
        for pattern in possible_patterns:
            matches = glob.glob(pattern)
            if matches:
                chromium_path = matches[0]
                break
        
        if not chromium_path:
            logging.warning("⚠️ Браузер Chromium не найден. Устанавливаю...")
            try:
                # Способ 1: через playwright CLI
                subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
                
                # После установки ищем снова
                for pattern in possible_patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        chromium_path = matches[0]
                        break
            except:
                # Способ 2: ручная установка через API
                try:
                    from playwright._impl._driver import compute_driver_executable
                    driver_executable = compute_driver_executable()
                    
                    # Запускаем playwright install через subprocess
                    result = subprocess.run(
                        [driver_executable, 'install', 'chromium'], 
                        capture_output=True, 
                        text=True
                    )
                    print(result.stdout)
                    
                    # Снова ищем
                    for pattern in possible_patterns:
                        matches = glob.glob(pattern)
                        if matches:
                            chromium_path = matches[0]
                            break
                except Exception as e:
                    logging.error(f"❌ Ошибка установки браузера: {e}")
        
        if chromium_path:
            logging.info(f"✅ Браузер найден: {chromium_path}")
            return chromium_path
        else:
            logging.error("❌ Не удалось установить или найти браузер")
            return None

LIKE = "1" #"❤️"
DISLIKE = "3" #"👎"

config = Config()