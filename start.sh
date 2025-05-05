#!/bin/bash

# Exit immediately on error
set -o errexit

echo "Checking for Playwright Chromium..."
if [ ! -f ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome ]; then
  echo "Chromium not found — installing via Playwright..."
  python -m playwright install chromium
else
  echo "Chromium already installed — skipping install."
fi

echo "Starting app..."
python app.py  # Replace with your actual entry point if different
