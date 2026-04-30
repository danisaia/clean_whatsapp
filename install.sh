#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/danisaia/clean_whatsapp.git"
TARGET_DIR="${HOME}/clean_whatsapp"

say() {
  printf '%s\n' "$1"
}

say "Clean WhatsApp installer"
say "========================"

if command -v pkg >/dev/null 2>&1; then
  say "Installing required Termux packages..."
  pkg update -y
  pkg install -y python git
else
  if ! command -v python3 >/dev/null 2>&1; then
    say "python3 was not found. Please install Python 3.10 or newer."
    exit 1
  fi
  if ! command -v git >/dev/null 2>&1; then
    say "git was not found. Please install Git."
    exit 1
  fi
fi

if [ -d "$TARGET_DIR/.git" ]; then
  say "Updating existing Clean WhatsApp folder..."
  git -C "$TARGET_DIR" pull origin main
else
  if [ -e "$TARGET_DIR" ]; then
    say "The target path already exists and is not a Git repository:"
    say "  $TARGET_DIR"
    say "Move or remove it, then run this installer again."
    exit 1
  fi
  say "Cloning Clean WhatsApp..."
  git clone "$REPO_URL" "$TARGET_DIR"
fi

say "Installing clean-whatsapp shortcut..."
bash "$TARGET_DIR/install-shortcut.sh"

say
say "Done. Open Clean WhatsApp with:"
say
say "  clean-whatsapp"
