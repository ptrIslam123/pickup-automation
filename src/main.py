import re
import time
import sqlite3

from fuzzywuzzy import fuzz
from playwright.sync_api import Playwright, sync_playwright
from profile_filter import *
from profile import Profile
from parser import parse_info
from global_config import BROWSER_CONTEXT_PATH, PROFILES_DB_PATH, DISLIKE, LIKE

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

def notify_about_problem():
    print("ERROR!!!")

def is_spam(profile_text: str) -> bool:
    spams = [
        """'подпишись на мой канал @Leomatchglobal'""",
        """Новости МОСКВЫ прямо сейчас!!Оперативные, экстренные события в нашем канале!"""
        """Мошенники могут действовать хитро, поэтому важно быть осторожным. Остерегайся мошеннических схем: просьбы о помощи, жалобные истории или предложения быстрого заработка — это частые уловки. Если кто-то настаивает на встрече или оказывает давление, не бойся завершить общение — безопасность важнее. Также осторожно относись к фотографиям: поддельные фото — частый инструмент мошенников, используй видео-звонки для общения.Всегда доверяй своей интуиции: если что-то кажется не так — сообщай о пользователе через кнопку жалобы.Это поможет сделать Дайвинчик безопаснее для всех."""
        """Нет такого варианта ответа"""
    ]

    threshold = 80
    for spam in spams:
        similarity = fuzz.ratio(profile_text.lower(), spam.lower())
        if similarity >= threshold:
            return False
    return True

def like_girls(playwright: Playwright):
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state=BROWSER_CONTEXT_PATH)
    page = context.new_page()
    page.goto("https://web.telegram.org/k/")

    page.get_by_placeholder(" ").click()
    page.get_by_placeholder(" ").fill("Leo ")
    page.get_by_text("@leomatchbotLeo – match and").click()

    conn = sqlite3.connect(PROFILES_DB_PATH)
    cursor = conn.cursor()

    while True:
        time.sleep(3)
        #TODO: determine current bot state!!!

        status = None
        profile_info = parse_info(page.content())
        if profile_info:
            image_list, profile_text = profile_info
            if is_spam(profile_text) is False:
                page.locator("div").filter(has_text=re.compile(r"^Message$")).locator("div").first.click()
                page.locator("div").filter(has_text=re.compile(r"^Message$")).locator("div").first.fill("1")
                page.get_by_role("button", name="    ").click()
                continue

            profile = Profile(image_list, profile_text)

            if Profile.find_profile_with_hash(cursor, conn, profile.get_hash()):
                continue # skip this profile because we have already liked this profile!

            if filter(profile):
                status = DISLIKE
            else:
                status = LIKE

            page.locator("div").filter(has_text=re.compile(r"^Message$")).locator("div").first.click()
            page.locator("div").filter(has_text=re.compile(r"^Message$")).locator("div").first.fill(status)
            page.get_by_role("button", name="    ").click()

            if status == LIKE:
                if profile.save_to_db(cursor, conn) is False:
                    notify_about_problem()
                    break
            else:
                notify_about_problem()
                break
        else:
            notify_about_problem()
            break

    context.close()
    browser.close()

with sync_playwright() as playwright:
    like_girls(playwright)