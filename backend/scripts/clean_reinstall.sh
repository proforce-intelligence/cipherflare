#!/bin/bash
# Force clean reinstall of dependencies, fixing elasticsearch header issues

set -e

echo "[*] Removing old virtual environment..."
rm -rf venv/

echo "[*] Creating fresh virtual environment..."
python3.11 -m venv venv

echo "[*] Activating venv..."
source venv/bin/activate

echo "[*] Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "[*] Installing requirements with force-reinstall..."
pip install --force-reinstall --no-cache-dir -r requirements.txt

echo "[*] Verifying elasticsearch version..."
pip show elasticsearch | grep Version

echo "[✓] Clean reinstall complete!"
