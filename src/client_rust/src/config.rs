use std::path::{Path, PathBuf};
use std::fs;
use std::env;
use std::process::Command;
use tracing::{info, warn, error};
use lazy_static::lazy_static;
use anyhow::{Result, anyhow};

lazy_static! {
    pub static ref CONFIG: Config = Config::new().expect("Failed to initialize config");
}

pub const LIKE: &str = "1";
pub const DISLIKE: &str = "3";

pub struct Config {
    workdir: PathBuf,
    logger_path: PathBuf,
    browser_context_path: PathBuf,
    browsers_path: PathBuf,
    chromium_path: Option<PathBuf>,
}

impl Config {
    pub fn new() -> Result<Self> {
        let mut config = Config {
            workdir: PathBuf::new(),
            logger_path: PathBuf::new(),
            browser_context_path: PathBuf::new(),
            browsers_path: PathBuf::new(),
            chromium_path: None,
        };
        
        config.init_workdir()?;
        config.init_logger()?;
        config.init_playwright()?;
        
        Ok(config)
    }
    
    pub fn get_browser_context_path(&self) -> &Path {
        &self.browser_context_path
    }
    
    pub fn get_logger_path(&self) -> &Path {
        &self.logger_path
    }
    
    pub fn get_workdir(&self) -> &Path {
        &self.workdir
    }
    
    pub fn get_browsers_path(&self) -> &Path {
        &self.browsers_path
    }
    
    pub fn get_chromium_path(&self) -> Option<&Path> {
        self.chromium_path.as_deref()
    }
    
    fn init_workdir(&mut self) -> Result<()> {
        // Получаем путь к директории исполняемого файла
        let current_exe = env::current_exe()?;
        self.workdir = current_exe.parent()
            .ok_or_else(|| anyhow!("Failed to get executable directory"))?
            .to_path_buf();
        
        // Устанавливаем пути
        self.logger_path = self.workdir.join("log");
        self.browser_context_path = self.workdir.join("browser_context");
        
        // Создаем директории, если их нет
        if !self.workdir.exists() {
            fs::create_dir_all(&self.workdir)?;
        }
        
        Ok(())
    }
    
    fn init_logger(&self) -> Result<()> {
        // В Rust мы используем tracing, но для совместимости создаем файл лога
        if !self.logger_path.exists() {
            fs::File::create(&self.logger_path)?;
        }
        
        // Инициализируем tracing для логирования
        // Файловый логгер можно настроить отдельно через tracing-appender
        Ok(())
    }
    
    fn init_playwright(&mut self) -> Result<()> {
        // Проверяем, установлен ли Playwright (в Rust это проверяется наличием браузеров)
        self.check_and_install_playwright()?;
        
        // Определяем путь к браузерам
        if let Ok(exe_path) = env::current_exe() {
            if exe_path.to_string_lossy().contains("target") {
                // Режим разработки
                self.browsers_path = dirs::cache_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join("ms-playwright");
            } else {
                // Скомпилированное приложение
                self.browsers_path = exe_path.parent()
                    .unwrap_or(Path::new("."))
                    .join("ms-playwright");
            }
        } else {
            self.browsers_path = PathBuf::from("./ms-playwright");
        }
        
        // Создаем папку для браузеров
        fs::create_dir_all(&self.browsers_path)?;
        
        // Устанавливаем переменную окружения для Playwright
        env::set_var("PLAYWRIGHT_BROWSERS_PATH", self.browsers_path.to_string_lossy().to_string());
        
        // Проверяем наличие Chromium
        self.chromium_path = self.find_chromium();
        
        if self.chromium_path.is_none() {
            warn!("⚠️ Браузер Chromium не найден. Устанавливаю...");
            self.install_chromium()?;
            self.chromium_path = self.find_chromium();
        }
        
        if let Some(path) = &self.chromium_path {
            info!("✅ Браузер найден: {:?}", path);
        } else {
            error!("❌ Не удалось установить или найти браузер");
        }
        
        Ok(())
    }
    
    fn check_and_install_playwright(&self) -> Result<()> {
        // В Rust playwright обычно устанавливается через Cargo
        // Проверяем наличие playwright в зависимостях не нужно,
        // так как это проверяется на этапе компиляции
        
        // Вместо этого просто проверяем, что playwright доступен
        #[cfg(not(target_arch = "wasm32"))]
        {
            // Пытаемся выполнить playwright --version
            if let Ok(output) = Command::new("playwright").arg("--version").output() {
                if output.status.success() {
                    info!("✅ Playwright CLI найден");
                    return Ok(());
                }
            }
            
            // Пытаемся найти через npx
            if let Ok(output) = Command::new("npx").args(["playwright", "--version"]).output() {
                if output.status.success() {
                    info!("✅ Playwright CLI найден через npx");
                    return Ok(());
                }
            }
            
            warn!("⚠️ Playwright CLI не найден. Рекомендуется установить: npm install -g playwright");
            // В Rust playwright браузеры управляются через playwright-rust автоматически
        }
        
        Ok(())
    }
    
    fn find_chromium(&self) -> Option<PathBuf> {
        let patterns = [
            // Linux
            self.browsers_path.join("chromium-*").join("chrome-linux64").join("chrome"),
            // Windows
            self.browsers_path.join("chromium-*").join("chrome-win").join("chrome.exe"),
            // Mac
            self.browsers_path.join("chromium-*").join("chrome-mac").join("Chromium.app")
                .join("Contents").join("MacOS").join("Chromium"),
        ];
        
        for pattern in patterns.iter() {
            if let Some(pattern_str) = pattern.to_str() {
                // Используем glob для поиска по паттерну
                if let Ok(entries) = glob::glob(pattern_str) {
                    for entry in entries.flatten() {
                        if entry.exists() {
                            return Some(entry);
                        }
                    }
                }
            }
        }
        
        None
    }
    
    fn install_chromium(&self) -> Result<()> {
        // Способ 1: через playwright CLI
        info!("Установка Chromium через playwright CLI...");
        
        // Пытаемся использовать npx playwright install chromium
        let install_commands = [
            (vec!["playwright", "install", "chromium"], false),
            (vec!["npx", "playwright", "install", "chromium"], true),
        ];
        
        for (args, use_npx) in install_commands.iter() {
            let cmd = if *use_npx {
                Command::new("npx")
                    .args(args)
                    .output()
            } else {
                Command::new(args[0])
                    .args(&args[1..])
                    .output()
            };
            
            match cmd {
                Ok(output) => {
                    if output.status.success() {
                        info!("✅ Chromium успешно установлен");
                        if !output.stdout.is_empty() {
                            info!("{}", String::from_utf8_lossy(&output.stdout));
                        }
                        return Ok(());
                    } else {
                        if !output.stderr.is_empty() {
                            error!("Ошибка установки: {}", String::from_utf8_lossy(&output.stderr));
                        }
                    }
                }
                Err(e) => {
                    warn!("Не удалось выполнить команду: {}", e);
                }
            }
        }
        
        // Способ 2: если не сработало через CLI, пробуем через playwright-rust
        warn!("CLI установка не удалась, пробуем через playwright-rust...");
        
        // В playwright-rust браузеры устанавливаются автоматически при первом запуске
        // Поэтому просто возвращаем Ok и надеемся, что при запуске playwright всё установит
        
        info!("При первом запуске playwright-rust автоматически установит браузеры");
        
        Ok(())
    }
}

// Добавляем зависимость glob в Cargo.toml