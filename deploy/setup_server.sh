#!/bin/bash
# ICS31 Quiz Generator - Server Setup Script
# Run this on your EC2 instance after SSH'ing in

set -e  # Exit on any error

echo "=========================================="
echo "ICS31 Quiz Generator - Server Setup"
echo "=========================================="

# Update system
echo "[1/8] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "[2/8] Installing Python..."
sudo apt install -y python3 python3-pip python3-venv

# Install Node.js (for building React frontend)
echo "[3/8] Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install FFmpeg (required for MoviePy)
echo "[4/8] Installing FFmpeg..."
sudo apt install -y ffmpeg

# Install ImageMagick (required for text rendering)
echo "[5/8] Installing ImageMagick..."
sudo apt install -y imagemagick

# Fix ImageMagick policy to allow text operations
echo "[6/8] Configuring ImageMagick policy..."
# Ubuntu 24.04 ships ImageMagick 6; newer releases ship ImageMagick 7.
POLICY_FILES=$(ls /etc/ImageMagick-*/policy.xml 2>/dev/null || true)
if [ -z "$POLICY_FILES" ]; then
    echo "ERROR: no ImageMagick policy.xml found; captions would not render" >&2
    exit 1
fi
for f in $POLICY_FILES; do
    sudo sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' "$f"
done

# Create swap file for memory management (important for t3.small)
echo "[7/8] Creating swap file (2GB)..."
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "Swap file created and enabled"
else
    echo "Swap file already exists"
fi

# Install Nginx for reverse proxy
echo "[8/8] Installing Nginx..."
sudo apt install -y nginx

echo ""
echo "=========================================="
echo "System setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Upload your project files to ~/ics31-quiz"
echo "2. Run: cd ~/ics31-quiz && ./deploy/install_app.sh"
