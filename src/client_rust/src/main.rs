mod config;
mod leo_bot;

use config::{CONFIG, LIKE, DISLIKE};
use leo_bot::LeoBot;
use tracing_subscriber;
use tracing::{info, error};
use std::time::Duration;
use tokio::time::sleep;
use playwright::Playwright;

const WAIT_TIMEOUT: Duration = Duration::from_secs(5);

#[tokio::main]
async fn main() -> Result<(), anyhow::Error> {
    // Инициализируем логирование
    tracing_subscriber::fmt::init();
    
    let playwright = Playwright::initialize().await?;
    // Config инициализируется автоматически через lazy_static
    info!("Рабочая директория: {:?}", CONFIG.get_workdir());
    info!("Путь к логам: {:?}", CONFIG.get_logger_path());
    info!("Путь к контексту браузера: {:?}", CONFIG.get_browser_context_path());
    info!("Путь к браузерам: {:?}", CONFIG.get_browsers_path());
    
    if let Some(chromium_path) = CONFIG.get_chromium_path() {
        info!("Chromium найден: {:?}", chromium_path);
    } else {
        info!("Chromium не найден, будет установлен при первом запуске");
    }
    
    let mut bot = LeoBot::new(playwright);
    match bot.login().await {
        Ok(_) => info!("✅ Успешный вход в систему"),
        Err(e) => {
            error!("❌ Ошибка входа: {}", e);
            return Err(e);
        }
    }

        info!("🔄 Запуск основного цикла...");
    
    // Основной цикл
    loop {
        sleep(WAIT_TIMEOUT).await;

        // Извлекаем контент
        let (text, images) = match bot.extract_web_content().await {
            Ok(content) => content,
            Err(e) => {
                error!("Ошибка при извлечении контента: {}", e);
                continue;
            }
        };
        
        // Проверяем последние 4 сообщения на условие остановки
        let last_3_text = text.iter()
            .rev()
            .take(4)
            .map(|s| s.as_str())
            .collect::<Vec<_>>()
            .join("\n");
            
        if bot.is_stop(&last_3_text).await {
            info!("⏹️ Получен сигнал остановки, завершаем работу");
            break;
        }
        
        // Обрабатываем последнее сообщение
        if let Some(last_text) = text.last() {
            // Проверка на спам (пока отключена)
            // if bot.is_spam(last_text).await {
            //     if let Err(e) = bot.enter("1").await {
            //         error!("Ошибка при ответе на спам: {}", e);
            //     }
            //     continue;
            // }
            
            // Проверка на match
            if bot.is_match(last_text).await {
                info!("❤️ Обнаружен match, отправляем лайк");
                if let Err(e) = bot.enter("1").await {
                    error!("Ошибка при отправке лайка: {}", e);
                }
                continue;
            }
            
            // Проверка на меню
            if bot.is_menu(last_text).await {
                info!("📋 Обнаружено меню, выбираем пункт 1");
                if let Err(e) = bot.enter("1").await {
                    error!("Ошибка при выборе пункта меню: {}", e);
                }
                continue;
            }
            
            // По умолчанию отправляем лайк
            info!("💬 Отправляем лайк по умолчанию");
            if let Err(e) = bot.enter(LIKE).await {
                error!("Ошибка при отправке сообщения: {}", e);
            }
        }
    }
    
    info!("👋 Завершение работы");
    
    Ok(())
}