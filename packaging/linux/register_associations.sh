#!/usr/bin/env bash
set -euo pipefail

APP_NAME="stela"
DESKTOP_FILE="${APP_NAME}.desktop"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$TARGET_DIR"
install -m 644 "$SRC_DIR/$DESKTOP_FILE" "$TARGET_DIR/$DESKTOP_FILE"
update-desktop-database "$TARGET_DIR" || true

xdg-mime default "$DESKTOP_FILE" application/pdf
xdg-mime default "$DESKTOP_FILE" application/epub+zip

echo "Registered Open With associations for PDF and EPUB with $DESKTOP_FILE"
