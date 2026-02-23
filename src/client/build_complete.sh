#!/bin/bash

echo "🔨 Начинаем сборку приложения..."

# Путь к браузерам Playwright
PLAYWRIGHT_PATH=$(python -c "import playwright; print(playwright.__path__[0])" 2>/dev/null)
BROWSERS_PATH="$HOME/.cache/ms-playwright"

# Проверяем наличие браузеров
if [ ! -d "$BROWSERS_PATH" ]; then
    echo "⚠️ Браузеры Playwright не найдены. Устанавливаю..."
    playwright install chromium
fi

# Создаем папку для сборки
mkdir -p ./dist

echo "📦 Компиляция в один файл..."

# Компиляция (без --setenv)
python -m nuitka \
    --onefile \
    --follow-imports \
    --include-package=requests \
    --include-package=ntplib \
    --include-package=bs4 \
    --include-package=Levenshtein \
    --include-package=fuzzywuzzy \
    --plugin-enable=playwright \
    --lto=yes \
    --remove-output \
    --output-dir=./dist \
    --include-data-dir=$BROWSERS_PATH=ms-playwright \
    main.py

# Проверяем результат компиляции
if [ ! -f "./dist/main.bin" ]; then
    echo "❌ Ошибка компиляции: файл main.bin не создан"
    exit 1
fi

echo "✅ Компиляция завершена"

# Создаем скрипт запуска
cat > ./dist/run.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Устанавливаем путь к браузерам
export PLAYWRIGHT_BROWSERS_PATH="$SCRIPT_DIR/ms-playwright"

# Запускаем приложение
exec "$SCRIPT_DIR/main.bin" "$@"
EOF

# Делаем скрипт исполняемым
chmod +x ./dist/run.sh

echo "📁 Создаю архив для распространения..."
cd ./dist
tar -czf ../myapp_complete.tar.gz .
cd ..

echo ""
echo "✅ ГОТОВО!"
echo "   Исполняемый файл: ./dist/main.bin"
echo "   Скрипт запуска:   ./dist/run.sh"
echo "   Архив:            ./myapp_complete.tar.gz"
echo ""
echo "🚀 Для запуска:"
echo "   cd dist && ./run.sh"

# cd ~/py/pickup-automation/src/client/dist
# ln -s /home/islam/.cache/ms-playwright ./ms-playwright
# ./run.sh