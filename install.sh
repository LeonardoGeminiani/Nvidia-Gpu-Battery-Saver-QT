#!/bin/bash
# Installs GpuBatterySaver to the system.
# Usage: sudo bash install.sh [--prefix /usr/local]
set -e

PREFIX="/usr/local"
if [[ "$1" == "--prefix" && -n "$2" ]]; then
    PREFIX="$2"
fi
INSTALL_DIR="$PREFIX/lib/gpubatterysaver"

if [ "$EUID" -ne 0 ]; then
    echo "Run with sudo: sudo bash install.sh"
    exit 1
fi

echo ">>> Installing to $PREFIX..."

# Copy app files
mkdir -p "$INSTALL_DIR"
cp core.py gui.py "$INSTALL_DIR/"
cp -r assets "$INSTALL_DIR/"

# Create local venv with deps
echo ">>> Installing Python dependencies..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r requirements.txt

# Launcher script
cat > "$PREFIX/bin/gpubatterysaver" <<EOF
#!/bin/bash
exec "$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/gui.py" "\$@"
EOF
chmod +x "$PREFIX/bin/gpubatterysaver"

# Desktop entry
install -Dm644 gpubatterysaver.desktop \
    "$PREFIX/share/applications/gpubatterysaver.desktop"

# Update Exec= path to absolute in the installed copy
sed -i "s|^Exec=.*|Exec=$PREFIX/bin/gpubatterysaver|" \
    "$PREFIX/share/applications/gpubatterysaver.desktop"

# Icon
install -Dm644 assets/icon.svg \
    "$PREFIX/share/icons/hicolor/scalable/apps/gpubatterysaver.svg"

# Refresh icon cache
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qf "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo ""
echo "Done. Run: gpubatterysaver"
