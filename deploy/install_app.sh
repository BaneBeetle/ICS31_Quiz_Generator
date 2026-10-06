#!/bin/bash
# ICS31 Quiz Generator - Application Installation Script
# Run this after setup_server.sh and uploading project files

set -e

APP_DIR=~/ics31-quiz
cd $APP_DIR

echo "=========================================="
echo "Installing ICS31 Quiz Generator"
echo "=========================================="

# Create Python virtual environment
echo "[1/6] Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "[2/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install font
echo "[3/6] Installing font..."
python install_font.py

# Build React frontend
echo "[4/6] Building React frontend..."
cd frontend
npm install
npm run build
cd ..

# Copy build to static folder for FastAPI to serve
echo "[5/6] Setting up static files..."
rm -rf static
cp -r frontend/build static

# Create directories
echo "[6/6] Creating required directories..."
mkdir -p videos temp logs

echo ""
echo "=========================================="
echo "Application installed successfully!"
echo "=========================================="
echo ""
echo "To start the server manually:"
echo "  cd ~/ics31-quiz && source venv/bin/activate && python server.py"
echo ""
echo "To set up as a service, run:"
echo "  sudo ./deploy/setup_service.sh"
