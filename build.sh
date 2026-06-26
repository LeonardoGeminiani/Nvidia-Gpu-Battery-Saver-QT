#!/bin/bash
# Builds GpuBatterySaver-x86_64.AppImage
# Requires: appimagetool on PATH (download from AppImageKit GitHub releases)
set -e

APP="GpuBatterySaver"
APPDIR="build/AppDir"

if ! command -v appimagetool &>/dev/null; then
    echo "Error: appimagetool not found in PATH."
    echo "Download appimagetool from the AppImageKit GitHub releases page and place it in your PATH."
    exit 1
fi

echo ">>> Setting up local venv..."
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements-build.txt

echo ">>> Bundling with PyInstaller..."
.venv/bin/pyinstaller \
    --noconfirm \
    --onedir \
    --name "$APP" \
    --collect-all PyQt6 \
    --distpath build/dist \
    --workpath build/work \
    gui.py

echo ">>> Assembling AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -r "build/dist/$APP" "$APPDIR/"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "$HERE/GpuBatterySaver/GpuBatterySaver" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cp gpubatterysaver.desktop "$APPDIR/$APP.desktop"
cp assets/icon.svg "$APPDIR/$APP.svg"

echo ">>> Building AppImage..."
ARCH=x86_64 appimagetool "$APPDIR" "${APP}-x86_64.AppImage"

echo ""
echo "Done: ${APP}-x86_64.AppImage"
