#!/usr/bin/env bash
set -euo pipefail

APP_NAME="stela"
PRODUCT_NAME="Stela"

# You can override these:
#   REPO=owner/repo TAG=latest ./scripts/install.sh
REPO="${REPO:-henacodes/stela}"
TAG="${TAG:-latest}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/opt/$APP_NAME}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
GH_TOKEN="${GH_TOKEN:-}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

infer_repo_from_git() {
  if ! command -v git >/dev/null 2>&1; then
    return 1
  fi

  local origin
  origin="$(git config --get remote.origin.url 2>/dev/null || true)"
  [[ -n "$origin" ]] || return 1

  # Supports:
  #   git@github.com:owner/repo.git
  #   https://github.com/owner/repo.git
  origin="${origin%.git}"
  origin="${origin#git@github.com:}"
  origin="${origin#https://github.com/}"
  origin="${origin#http://github.com/}"

  if [[ "$origin" == */* ]]; then
    printf "%s" "$origin"
    return 0
  fi

  return 1
}

log() {
  printf "\n[stela-install] %s\n" "$1"
}

need_cmd curl
need_cmd python3
need_cmd tar

if [[ -z "$REPO" ]]; then
  REPO="$(infer_repo_from_git || true)"
fi

if [[ -z "$REPO" ]]; then
  echo "Could not determine GitHub repository."
  echo "Run with: REPO=owner/repo ./scripts/install.sh"
  exit 2
fi

ARCH_RAW="$(uname -m)"
OS_RAW="$(uname -s | tr '[:upper:]' '[:lower:]')"

case "$ARCH_RAW" in
  x86_64|amd64) ARCH="x64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $ARCH_RAW"
    exit 2
    ;;
esac

if [[ "$OS_RAW" != "linux" ]]; then
  echo "This installer currently supports Linux only."
  exit 2
fi

AUTH_HEADER=()
if [[ -n "$GH_TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $GH_TOKEN")
fi

if [[ "$TAG" == "latest" ]]; then
  API_URL="https://api.github.com/repos/$REPO/releases/latest"
else
  API_URL="https://api.github.com/repos/$REPO/releases/tags/$TAG"
fi

log "Fetching release metadata from $API_URL"
RELEASE_JSON="$(curl -fsSL "${AUTH_HEADER[@]}" "$API_URL")"

ASSET_INFO="$(python3 - <<'PY' "$RELEASE_JSON" "$ARCH" "$APP_NAME"
import json
import re
import sys

release = json.loads(sys.argv[1])
arch = sys.argv[2]
app = sys.argv[3]
assets = release.get("assets", [])
if not assets:
    sys.exit(10)

def score(name: str) -> int:
    n = name.lower()
    s = 0
    if app in n:
        s += 6
    if "linux" in n:
        s += 8
    if arch in n:
        s += 8
    if arch == "x64" and ("x86_64" in n or "amd64" in n):
        s += 6
    if arch == "arm64" and ("aarch64" in n):
        s += 6
    if n.endswith(".tar.gz") or n.endswith(".tgz"):
        s += 5
    elif n.endswith(".zip"):
        s += 3
    elif re.search(rf"(^|[_.-]){re.escape(app)}([_.-]|$)", n):
        s += 2
    return s

best = None
for a in assets:
    name = a.get("name", "")
    url = a.get("browser_download_url", "")
    if not name or not url:
        continue
    sc = score(name)
    if best is None or sc > best[0]:
        best = (sc, name, url)

if best is None or best[0] <= 0:
    sys.exit(11)

print(best[1])
print(best[2])
PY
)" || {
  echo "Failed to select release asset for Linux/$ARCH."
  echo "Check your release artifacts naming in repo: $REPO"
  exit 3
}

ASSET_NAME="$(printf '%s\n' "$ASSET_INFO" | sed -n '1p')"
ASSET_URL="$(printf '%s\n' "$ASSET_INFO" | sed -n '2p')"

log "Selected asset: $ASSET_NAME"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ASSET_FILE="$TMP_DIR/$ASSET_NAME"

log "Downloading release asset"
curl -fL "${AUTH_HEADER[@]}" -o "$ASSET_FILE" "$ASSET_URL"

EXTRACT_DIR="$TMP_DIR/extract"
mkdir -p "$EXTRACT_DIR"

if [[ "$ASSET_NAME" == *.tar.gz || "$ASSET_NAME" == *.tgz ]]; then
  tar -xzf "$ASSET_FILE" -C "$EXTRACT_DIR"
elif [[ "$ASSET_NAME" == *.zip ]]; then
  need_cmd unzip
  unzip -q "$ASSET_FILE" -d "$EXTRACT_DIR"
else
  # raw executable fallback
  mkdir -p "$EXTRACT_DIR/raw"
  cp "$ASSET_FILE" "$EXTRACT_DIR/raw/$APP_NAME"
  chmod +x "$EXTRACT_DIR/raw/$APP_NAME"
fi

BIN_PATH="$(find "$EXTRACT_DIR" -type f -name "$APP_NAME" | head -n1 || true)"
if [[ -z "$BIN_PATH" ]]; then
  echo "Could not find '$APP_NAME' binary in downloaded asset."
  exit 4
fi
BUNDLE_DIR="$(dirname "$BIN_PATH")"

log "Installing to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"
rm -rf "$INSTALL_DIR"/*
cp -r "$BUNDLE_DIR"/* "$INSTALL_DIR"/
chmod +x "$INSTALL_DIR/$APP_NAME" || true
ln -sf "$INSTALL_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"

ICON_PATH="stela"
if [[ -f "$INSTALL_DIR/data/flutter_assets/assets/icon.png" ]]; then
  ICON_PATH="$INSTALL_DIR/data/flutter_assets/assets/icon.png"
elif [[ -f "$INSTALL_DIR/assets/icon.png" ]]; then
  ICON_PATH="$INSTALL_DIR/assets/icon.png"
fi

DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$PRODUCT_NAME
Comment=Read PDF and EPUB books
Exec=$INSTALL_DIR/$APP_NAME %F
Icon=$ICON_PATH
Terminal=false
Categories=Office;Viewer;
MimeType=application/pdf;application/epub+zip;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" || true
fi

if command -v xdg-mime >/dev/null 2>&1; then
  xdg-mime default "$APP_NAME.desktop" application/pdf || true
  xdg-mime default "$APP_NAME.desktop" application/epub+zip || true
fi

log "Install complete"
echo "Run: $APP_NAME"
echo "If command is not found, add $BIN_DIR to PATH"
