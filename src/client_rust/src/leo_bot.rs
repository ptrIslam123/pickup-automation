use std::path::Path;
use std::time::Duration;
use std::fs;

use anyhow::{Result, anyhow};
use playwright::Playwright;
use playwright::api::{Browser, BrowserContext, Page};
use playwright::api::frame::{FrameState};
use scraper::{Html, Selector};
use tracing::{info, warn, error};
use tokio::time::sleep;
use fuzzywuzzy::fuzz;

use crate::config::CONFIG;
use leo_bot::utils::levenshtein_cmp;

pub struct LeoBot {
    playwright: Playwright,
    browser: Option<Browser>,
    context: Option<BrowserContext>,
    page: Option<Page>,
}

impl LeoBot {
    pub fn new(playwright: Playwright) -> Self {
        LeoBot {
            playwright: playwright,
            browser: None,
            context: None,
            page: None,
        }
    }
    
    pub async fn is_spam(&self, _text: &str) -> bool {
        false
    }
    
    pub async fn is_menu(&self, text: &str) -> bool {
        let examples = [
            r#"
            1. Смотреть анкеты.
            2. Заполнить анкету заново.
            3. Изменить фото/видео.
            4. Изменить текст анкеты.
            "#,
            r#"
            Несколько девушек из хотят познакомиться с тобой прямо сейчас
            1. Посмотреть.
            2. Не интересно.
            "#,
        ];
        
        for example in examples.iter() {
            if levenshtein_cmp(example, text, 0.6) {
                return true;
            }
        }
        
        false
    }
    
    pub async fn is_stop(&self, text: &str) -> bool {
        let example = r#"
        Слишком много за сегодня.
        Пригласи друзей и получи больше !
        Перешли друзьям или размести в своих соцсетях.
        Вот твоя личная ссылка
        Бот знакомств Дайвинчик в Telegram! Найдет друзей или даже половинку 
        https://t.me/leomatchbot?start= 
        Любые попытки купить или накрутить рефералов приводят к незамедлительной блокировке аккаунта.
        Кто-то тобой заинтересовался! Заканчивай с вопросом выше и посмотрим кто там
        "#;
        
        levenshtein_cmp(example, text, 0.6)
    }
    
    pub async fn is_match(&self, text: &str) -> bool {
        let examples = [
            r#"Нашли кое-кого для тебя ;) Заканчивай с вопросом выше и увидишь кто это"#,
            r#"
            Ты понравился 1 девушке, показать её?
            1. Показать.
            2. Не хочу больше никого смотреть.
            "#,
        ];
        
        for example in examples.iter() {
            if levenshtein_cmp(example, text, 0.6) {
                return true;
            }
        }
        
        false
    }

    pub async fn extract_web_content(&self) -> Result<(Vec<String>, Vec<String>)> {
        let page = self.page.as_ref().ok_or_else(|| anyhow!("Page not initialized"))?;
        
        let content = page.content().await?;
        let document = Html::parse_document(&content);
        
        let chat_selector = Selector::parse("div.chat").unwrap();
        let message_selector = Selector::parse("div[data-mid]").unwrap();
        let text_selector = Selector::parse("span.translatable-message").unwrap();
        let img_selector = Selector::parse("img.media-photo").unwrap();
        
        let mut texts = Vec::new();
        let mut images = Vec::new();
        
        if let Some(chat_container) = document.select(&chat_selector).next() {
            for element in chat_container.select(&message_selector) {
                if let Some(text_elem) = element.select(&text_selector).next() {
                    let text = text_elem.text().collect::<String>().trim().to_string();
                    if !text.is_empty() {
                        texts.push(text);
                    }
                }
                
                for img in element.select(&img_selector) {
                    if let Some(src) = img.value().attr("src") {
                        if src.starts_with("blob:") {
                            images.push(src.to_string());
                        }
                    }
                }
            }
        }
        
        Ok((texts, images))
    }

    pub async fn enter(&self, message: &str) -> Result<()> {
        let page = self.page.as_ref().ok_or_else(|| anyhow!("Page not initialized"))?;
        
        // Ищем поле ввода
        if let Ok(Some(input)) = page.query_selector(".input-message-input").await {
            input.click_builder().click().await?;
            input.fill_builder(message).fill().await?;
            
            // Ищем кнопку отправки
            let send_selectors = [
                "[data-qa='send-button']",
                "[data-test='send-btn']",
                ".send-button",
                ".btn-send",
                ".input-button",
                "button[type='submit']",
                ".chat-footer button:last-child",
            ];
            
            for selector in send_selectors.iter() {
                if let Ok(Some(button)) = page.query_selector(selector).await {
                    button.click_builder().click().await?;
                    return Ok(());
                }
            }
            
            input.press_builder("Enter")
                .press()
                .await?;
            
            return Ok(());
        }
        
        warn!("Поле ввода не найдено");
        Ok(())
    }

    pub async fn login(&mut self) -> Result<()> {
        let browser_context_path = CONFIG.get_browser_context_path().to_path_buf();
        let browser_path = CONFIG.get_chromium_path()
            .ok_or_else(|| anyhow!("Chromium not found in config"))?;

        let browser = self.playwright.chromium()
            .launcher()
            .headless(false)
            .executable(browser_path)
            .launch()
            .await?;

        if !browser_context_path.exists() {
            // Первый вход - требуется авторизация
            self.first_time_login(&browser, &browser_context_path).await?;
        } else {
            // Используем сохраненную сессию
            self.restore_session(&browser, &browser_context_path).await?;
        }

        info!("🔍 Поиск leomatchbot...");
        
        let page = self.page.as_ref().ok_or_else(|| anyhow!("Page not initialized"))?;
        
        // Ищем поле поиска и вводим текст
        let search_input = page.query_selector("[placeholder=\" \"]").await?
            .ok_or_else(|| anyhow!("Search input not found"))?;
        
        search_input.click_builder()
            .click()
            .await?;
        
        search_input.fill_builder("@leomatchbot")
            .fill()
            .await?;
        
        // Ждем появления бота - ИСПРАВЛЕНО
        page.wait_for_selector_builder("text=leomatchbot")
            .timeout(5000.0)
            .wait_for_selector()
            .await?;
        
        // Ищем бота и кликаем
        let bot_element = page.query_selector("text=leomatchbot").await?
            .ok_or_else(|| anyhow!("Bot element not found"))?;
        
        bot_element.click_builder()
            .click()
            .await?;
        
        info!("✅ Успешно перешли в чат с leomatchbot");

        self.browser = std::option::Option::Some(browser);
        Ok(())
    }

    async fn first_time_login(&mut self, browser: &Browser, context_path: &Path) -> Result<()> {
        info!("🔄 Первый запуск. Выполняется авторизация в Telegram Web...");
        
        // Создаем новый контекст
        let context = browser.context_builder().build().await?;
        let page = context.new_page().await?;
        
        page.goto_builder("https://web.telegram.org/k/")
            .goto()
            .await?;
        
        self.context = Some(context);
        self.page = Some(page.clone());
        
        // Ждем ручной авторизации пользователя
        self.wait_for_telegram_auth(&page).await?;
        
        // Сохраняем состояние сессии
        let storage_state = self.context.as_ref().unwrap().storage_state().await?;
        let json = serde_json::to_string_pretty(&storage_state)?;
        fs::write(context_path, json)?;
        
        info!("✅ Сессия сохранена");
        
        Ok(())
    }

    async fn restore_session(&mut self, browser: &Browser, context_path: &Path) -> Result<()> {
        info!("🔄 Восстановление сохраненной сессии...");
        
        // Читаем сохраненную сессию
        let json = fs::read_to_string(context_path)?;
        let storage_state = serde_json::from_str(&json)?;
        
        // Создаем контекст с восстановленной сессией
        let context = browser.context_builder()
            .storage_state(storage_state)
            .build()
            .await?;
            
        let page = context.new_page().await?;
        
        page.goto_builder("https://web.telegram.org/k/")
            .goto()
            .await?;
        
        self.context = Some(context);
        self.page = Some(page);
        
        info!("✅ Сессия восстановлена");
        
        Ok(())
    }

    async fn wait_for_telegram_auth(&self, page: &Page) -> Result<()> {
        info!("⏳ Ожидание авторизации в Telegram Web...");
        info!("   Пожалуйста, войдите в свой аккаунт в открывшемся окне браузера");
        
        loop {
            // Пробуем найти поле поиска
            if let Ok(Some(search_input)) = page.query_selector("[placeholder=\" \"]").await {
                // ИСПРАВЛЕНО: используем builder паттерн
                if let Err(e) = search_input.click_builder().click().await {
                    warn!("Ошибка при клике: {}", e);
                    continue;
                }
                
                if let Err(e) = search_input.fill_builder("@leomatchbot").fill().await {
                    warn!("Ошибка при вводе текста: {}", e);
                    continue;
                }
                
                // ИСПРАВЛЕНО: используем wait_for() метод
                match page.wait_for_selector_builder("text=leomatchbot")
                    .timeout(5000.0)
                    .wait_for_selector()
                    .await 
                {
                    Ok(_) => {
                        info!("✅ Бот найден, авторизация завершена");
                        return Ok(());
                    }
                    Err(e) => {
                        info!("Бот еще не появился, продолжаем ожидание... (ошибка: {})", e);
                        continue;
                    }
                }
            }
        }
        
        Ok(())
    }

    pub async fn download_image(&self, image_url: &str) -> Result<Vec<u8>> {
        let page = self.page.as_ref()
            .ok_or_else(|| anyhow!("Page not initialized"))?;
        
        let js_code = r#"
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
        "#;
        
        let result: Option<String> = page.evaluate(js_code, Some(serde_json::json!([image_url]))).await?;
        
        match result {
            Some(data_url) if data_url.starts_with("data:") => {
                if let Some(comma_idx) = data_url.find(',') {
                    let encoded = &data_url[comma_idx + 1..];
                    let decoded = BASE64.decode(encoded)?;
                    Ok(decoded)
                } else {
                    Err(anyhow!("Invalid data URL format"))
                }
            }
            Some(_) => {
                error!("❌ Failed to download image: {}...", &image_url.chars().take(50).collect::<String>());
                Err(anyhow!("Failed to download image: invalid response"))
            }
            None => {
                error!("❌ Failed to download image: {}...", &image_url.chars().take(50).collect::<String>());
                Err(anyhow!("Failed to download image: no data"))
            }
        }
    }
}