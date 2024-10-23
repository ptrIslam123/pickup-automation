import re
import time
import sqlite3

from fuzzywuzzy import fuzz
from playwright.sync_api import Playwright, sync_playwright

from profile_filter import AIProfileFilter
from profile_parser import Profile
from profile_db import ProfilesDB
from leo_bot import LeoBot
from ai import ask
from global_config import *

def login(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://web.telegram.org/k/")
    # page.get_by_role("button", name="Log in by phone Number").click()
    #
    # while True:
    #     phone_input = page.locator('div.input-field-input[contenteditable="true"]')
    #     if phone_input:
    #         phone_input.nth(0) .fill(phone_nummer)
    #         break
    #     else:
    #         continue
    #
    # #page.locator("div").filter(has_text=re.compile(r"^Phone Number$")).locator("div").first.fill(phone_nummer)
    # page.get_by_role("button", name="Next").click()
    # pin_code = input("ENTER TELEGRAM PIN CODE:\n")
    # page.get_by_role("textbox").fill(pin_code)


    context.storage_state(path=BROWSER_CONTEXT_PATH)
    # ---------------------
    context.close()
    browser.close()



def main(playwright: Playwright):
    wait_timeout = 30
    
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
            # parse
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
    #login(playwright)


