#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

apt-get update && apt-get install -y wget libnss3 libatk-bridge2.0-0 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libgtk-3-0 libxext6 libxfixes3 libxrender1
