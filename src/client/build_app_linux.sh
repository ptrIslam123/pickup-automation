#!/bin/bash

echo "🔨 Starting build process for GNU/Linux..."

# Path to Playwright browsers
PLAYWRIGHT_PATH=$(python -c "import playwright; print(playwright.__path__[0])" 2>/dev/null)
BROWSERS_PATH="$HOME/.cache/ms-playwright"

# Check if browsers exist
if [ ! -d "$BROWSERS_PATH" ]; then
    echo "⚠️ Playwright browsers not found. Installing..."
    playwright install chromium
fi

# Create build directory
mkdir -p ./dist

echo "📦 Compiling to single executable..."

# Compilation with Nuitka
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

# Verify compilation result
if [ ! -f "./dist/main.bin" ]; then
    echo "❌ Compilation failed: main.bin not created"
    exit 1
fi

echo "✅ Compilation completed successfully!"

# Create launcher script
cat > ./dist/run.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set browser path for Playwright
export PLAYWRIGHT_BROWSERS_PATH="$SCRIPT_DIR/ms-playwright"

# Launch the application
exec "$SCRIPT_DIR/main.bin" "$@"
EOF

# Make launcher executable
chmod +x ./dist/run.sh

echo "📁 Creating distribution archive..."
cd ./dist
tar -czf ../myapp_complete.tar.gz .
cd ..

echo ""
echo "✅ ========== BUILD SUCCESSFUL =========="
echo "   📦 Executable:     ./dist/main.bin"
echo "   🚀 Launcher script: ./dist/run.sh"
echo "   📚 Archive:        ./myapp_complete.tar.gz"
echo "   📏 File size:       $(du -h ./dist/main.bin | cut -f1)"
echo ""
echo "🚀 To run the application:"
echo "   cd dist && ./run.sh"
echo ""
echo "📦 To distribute:"
echo "   Send myapp_complete.tar.gz to users"
echo "   They just need to extract and run ./run.sh"
echo "=========================================="