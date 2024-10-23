import os
import logging

ROOT_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/.."
BROWSER_CONTEXT_PATH=f"{ROOT_PATH}/.local/browser_context"
LOG_FILE_PATH=f"{ROOT_PATH}/log/log.txt"
PROFILES_DB_PATH=f"{ROOT_PATH}/database/profiles.db"

LIKE = "1" #"❤️"
DISLIKE = "3" #"👎"

QWEN_MODEL = "qwen3:4b"
QWEN_HOST = "localhost"
QWEN_PORT = "11434"

logging.basicConfig(
    filename=LOG_FILE_PATH,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)