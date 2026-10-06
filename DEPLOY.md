# ICS31 Quiz Generator - Deployment Guide

## Server Info (replace the placeholders with your own)
- **IP**: `<EC2_PUBLIC_IP>`
- **Instance**: t3.small (Ubuntu 24.04)
- **Key**: `path\to\your-key.pem`

## Quick Deploy (Windows PowerShell)

### Step 1: Connect to your server
```powershell
ssh -i "path\to\your-key.pem" ubuntu@<EC2_PUBLIC_IP>
```

### Step 2: On the server - Initial setup
```bash
# Create app directory
mkdir -p ~/ics31-quiz
exit
```

### Step 3: Upload project files (from your Windows machine)
```powershell
# From the project directory
cd "path\to\ICS31_Quiz_Generator"

# Upload everything using SCP
scp -i "path\to\your-key.pem" -r `
  main.py server.py gpt_api.py tiktokvoice.py moviepy_config.py `
  install_font.py requirements.txt OpenSans-ExtraBold.ttf .env.example `
  frontend audio minecraft deploy `
  ubuntu@<EC2_PUBLIC_IP>:~/ics31-quiz/
```

### Step 4: SSH back in and run setup scripts
```bash
ssh -i "path\to\your-key.pem" ubuntu@<EC2_PUBLIC_IP>

# Run system setup (installs Python, Node, FFmpeg, ImageMagick, etc.)
cd ~/ics31-quiz
chmod +x deploy/*.sh
./deploy/setup_server.sh

# Install the application
./deploy/install_app.sh

# Set your OpenAI API key (the service reads it from .env)
cp .env.example .env
nano .env        # set OPENAI_API_KEY=sk-...

# Set up as a system service (auto-start on boot)
sudo ./deploy/setup_service.sh

# Set up Nginx (serve on port 80)
sudo ./deploy/setup_nginx.sh
```

### Step 5: Change the API key later
```bash
# Edit .env, then restart the service
nano ~/ics31-quiz/.env
sudo systemctl restart ics31-quiz
```

## Access Your App
- **HTTP**: http://<EC2_PUBLIC_IP>

## Useful Commands

```bash
# Check if app is running
sudo systemctl status ics31-quiz

# View live logs
sudo journalctl -u ics31-quiz -f

# Restart the app
sudo systemctl restart ics31-quiz

# Check disk space
df -h

# Check memory usage
free -h
```

## Troubleshooting

### App not loading?
```bash
# Check if service is running
sudo systemctl status ics31-quiz

# Check logs for errors
sudo journalctl -u ics31-quiz --no-pager -n 50
```

### Out of memory during video generation?
```bash
# Check swap is enabled
free -h

# If no swap, run:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Port 80 not responding?
```bash
# Check Nginx status
sudo systemctl status nginx

# Check if port 80 is open in AWS Security Group
# (You should have HTTP enabled from your EC2 setup)
```
