#!/bin/bash

# ICS31 Quiz Generator - EC2 Setup Script
# Run this script on a fresh Amazon Linux 2023 or Ubuntu 22.04 EC2 instance

set -e

echo "==================================="
echo "ICS31 Quiz Generator - EC2 Setup"
echo "==================================="

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
fi

echo "Detected OS: $OS"

# Update system
echo "Updating system packages..."
if [ "$OS" == "amzn" ] || [ "$OS" == "rhel" ]; then
    sudo yum update -y
elif [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    sudo apt-get update && sudo apt-get upgrade -y
fi

# Install Docker
echo "Installing Docker..."
if [ "$OS" == "amzn" ]; then
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
elif [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
echo "Installing Git..."
if [ "$OS" == "amzn" ] || [ "$OS" == "rhel" ]; then
    sudo yum install -y git
elif [ "$OS" == "ubuntu" ] || [ "$OS" == "debian" ]; then
    sudo apt-get install -y git
fi

# Create app directory
echo "Setting up application directory..."
APP_DIR="/opt/quiz-generator"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "1. Log out and log back in (for docker group to take effect)"
echo "2. Clone your repository to $APP_DIR"
echo "3. Create .env file with your OPENAI_API_KEY"
echo "4. Run: cd $APP_DIR && docker-compose up -d"
echo ""
echo "Make sure your EC2 security group allows:"
echo "  - Port 22 (SSH)"
echo "  - Port 80 (HTTP)"
echo "  - Port 443 (HTTPS, optional)"
echo "  - Port 8000 (API, for testing)"
