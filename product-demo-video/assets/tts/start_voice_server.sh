#!/usr/bin/env sh
# Thin Linux/macOS wrapper around the cross-platform launcher.
cd "$(dirname "$0")" || exit 1
PYL=$(command -v python3 || command -v python) || { echo "Python 3 not found. Install Python 3.12 first."; exit 1; }
exec "$PYL" start_voice_server.py
