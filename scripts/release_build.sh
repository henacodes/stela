#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-linux}"

# Ensure Flutter scripts using `#!/usr/bin/env bash` can resolve bash.
export SHELL="${SHELL:-/usr/bin/bash}"
case ":${PATH}:" in
  *:/usr/bin:*) ;;
  *) PATH="/usr/bin:${PATH}" ;;
esac
case ":${PATH}:" in
  *:/bin:*) ;;
  *) PATH="/bin:${PATH}" ;;
esac
export PATH

log() {
  printf "\n[stela-release] %s\n" "$1"
}

build_linux() {
  log "Building Linux package with Flet"
  (cd "$ROOT_DIR" && flet build linux -v)
  log "Linux build complete"
  log "Debian maintainer scripts are in packaging/linux/debian/ and should be included by your packaging pipeline"
}

install_linux_user() {
  local app_dir="${HOME}/.local/opt/stela"
  local bin_dir="${HOME}/.local/bin"
  local desktop_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

  if [[ ! -f "$ROOT_DIR/build/linux/stela" ]]; then
    log "Linux build output not found, building first"
    build_linux
  fi

  log "Installing Stela to user directories"
  mkdir -p "$app_dir" "$bin_dir" "$desktop_dir"
  rm -rf "$app_dir"/*
  cp -r "$ROOT_DIR/build/linux"/* "$app_dir"/
  ln -sf "$app_dir/stela" "$bin_dir/stela"

  cp "$ROOT_DIR/packaging/linux/stela.desktop" "$desktop_dir/stela.desktop"
  sed -i "s|^Exec=.*|Exec=${app_dir}/stela %F|" "$desktop_dir/stela.desktop"

  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$desktop_dir" || true
  fi
  if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default stela.desktop application/pdf || true
    xdg-mime default stela.desktop application/epub+zip || true
  fi

  log "Install complete"
  log "Run app with: stela"
}

find_windows_bundle_dir() {
  local candidates=(
    "$ROOT_DIR/dist/windows"
    "$ROOT_DIR/build/windows"
    "$ROOT_DIR/.flet/build/windows"
  )
  for d in "${candidates[@]}"; do
    if [[ -d "$d" ]]; then
      printf "%s" "$d"
      return 0
    fi
  done
  return 1
}

build_windows() {
  log "Building Windows app bundle with Flet"
  (cd "$ROOT_DIR" && flet build windows -v)

  if ! command -v iscc >/dev/null 2>&1; then
    log "Inno Setup compiler (iscc) not found. Skipping installer generation."
    log "Install Inno Setup and run: iscc packaging/windows/stela.iss"
    return 0
  fi

  local bundle_dir
  if bundle_dir="$(find_windows_bundle_dir)"; then
    log "Building Windows installer from bundle: $bundle_dir"
    (cd "$ROOT_DIR" && iscc "/DAppSourceDir=$bundle_dir" packaging/windows/stela.iss)
    log "Windows installer build complete"
  else
    log "Could not find Windows bundle directory after build; skipping installer generation"
  fi
}

case "$TARGET" in
  linux)
    build_linux
    ;;
  linux-install)
    install_linux_user
    ;;
  linux-quick)
    build_linux
    install_linux_user
    ;;
  windows)
    build_windows
    ;;
  all)
    build_linux
    build_windows
    ;;
  *)
    echo "Usage: $0 [linux|linux-install|linux-quick|windows|all]"
    exit 2
    ;;
esac
