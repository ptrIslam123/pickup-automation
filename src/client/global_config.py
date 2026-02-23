import os
import logging

ROOT_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/../.."
BROWSER_CONTEXT_PATH="/home/islam/py/pickup-automation/.local/browser_context" # f"{ROOT_PATH}/.local/browser_context"
LOG_FILE_PATH="/home/islam/py/pickup-automation/log/log.txt" #f"{ROOT_PATH}/log/log.txt"

LIKE = "1" #"❤️"
DISLIKE = "3" #"👎"

logging.basicConfig(
    filename=LOG_FILE_PATH,
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)