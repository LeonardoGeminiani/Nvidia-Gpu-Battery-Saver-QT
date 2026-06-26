#!/bin/bash
# Installs GpuBatterySaver to the user's local directory (no sudo needed).
# Usage: bash install.sh [--prefix ~/.local]
set -e

PREFIX="${HOME}/.local"
if [[ "$1" == "--prefix" && -n "$2" ]]; then
    PREFIX="$2"
fi
INSTALL_DIR="$PREFIX/lib/gpubatterysaver"

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
mkdir -p "$PREFIX/bin"
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

# Refresh icon/desktop caches (user-level, no root needed)
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qf "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo ""
echo "Done. Run: gpubatterysaver"
echo ""
echo "Make sure ~/.local/bin is on your PATH. If not, add this to ~/.bashrc or ~/.profile:"
echo '  export PATH="$HOME/.local/bin:$PATH"'
