#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-linux}"

log() {
  printf "\n[stela-release] %s\n" "$1"
}

build_linux() {
  log "Building Linux package with Flet"
  (cd "$ROOT_DIR" && flet build linux -v)
  log "Linux build complete"
  log "Debian maintainer scripts are in packaging/linux/debian/ and should be included by your packaging pipeline"
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
  windows)
    build_windows
    ;;
  all)
    build_linux
    build_windows
    ;;
  *)
    echo "Usage: $0 [linux|windows|all]"
    exit 2
    ;;
esac
