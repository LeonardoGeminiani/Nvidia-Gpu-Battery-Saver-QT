#!/bin/bash
# Removes a system-installed GpuBatterySaver.
# Usage: sudo bash uninstall.sh [--prefix /usr/local]
set -e

PREFIX="/usr/local"
if [[ "$1" == "--prefix" && -n "$2" ]]; then
    PREFIX="$2"
fi

if [ "$EUID" -ne 0 ]; then
    echo "Run with sudo: sudo bash uninstall.sh"
    exit 1
fi

echo ">>> Removing GpuBatterySaver from $PREFIX..."

rm -rf  "$PREFIX/lib/gpubatterysaver"
rm -f   "$PREFIX/bin/gpubatterysaver"
rm -f   "$PREFIX/share/applications/gpubatterysaver.desktop"
rm -f   "$PREFIX/share/icons/hicolor/scalable/apps/gpubatterysaver.svg"

if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -qf "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo "Done."
