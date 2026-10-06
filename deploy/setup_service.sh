#!/bin/bash
# ICS31 Quiz Generator - Systemd Service Setup
# This makes the app start automatically on boot

set -e

APP_DIR=/home/ubuntu/ics31-quiz
ENV_FILE=$APP_DIR/.env

echo "Setting up systemd service..."

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "ERROR: .env file not found at $ENV_FILE"
    echo ""
    echo "Please create it with your OpenAI API key:"
    echo "  cp $APP_DIR/.env.example $APP_DIR/.env"
    echo "  nano $APP_DIR/.env"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Verify OPENAI_API_KEY is set in .env
if ! grep -q "^OPENAI_API_KEY=sk-" "$ENV_FILE"; then
    echo ""
    echo "WARNING: OPENAI_API_KEY doesn't appear to be set in .env"
    echo "Make sure to add your API key to $ENV_FILE"
    echo ""
fi

# Create systemd service file with environment file support
sudo tee /etc/systemd/system/ics31-quiz.service > /dev/null <<EOF
[Unit]
Description=ICS31 Quiz Generator
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ics31-quiz
# Load environment variables from .env file (secure - not in service file)
EnvironmentFile=/home/ubuntu/ics31-quiz/.env
Environment=PATH=/home/ubuntu/ics31-quiz/venv/bin:/usr/bin
ExecStart=/home/ubuntu/ics31-quiz/venv/bin/python server.py
Restart=always
RestartSec=10

# Security hardening. The app directory is read-only except for what the
# app writes: generated videos, temp files (TTS clips and MoviePy's
# temporary soundtrack) and logs/audit.log.
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/ubuntu/ics31-quiz/videos /home/ubuntu/ics31-quiz/temp /home/ubuntu/ics31-quiz/logs
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Secure the .env file permissions (only owner can read)
chmod 600 "$ENV_FILE"
echo "Secured .env file permissions (chmod 600)"

# The writable directories must exist before the service starts: systemd
# refuses to start a unit whose ReadWritePaths are missing, and the app
# can't create them inside its read-only directory.
sudo install -d -o ubuntu -g ubuntu "$APP_DIR/videos" "$APP_DIR/temp" "$APP_DIR/logs"

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable ics31-quiz
sudo systemctl start ics31-quiz

echo ""
echo "Service installed and started!"
echo ""
echo "IMPORTANT: Your API key is loaded from $ENV_FILE"
echo "To update it: edit the file and run 'sudo systemctl restart ics31-quiz'"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status ics31-quiz   # Check status"
echo "  sudo systemctl restart ics31-quiz  # Restart"
echo "  sudo journalctl -u ics31-quiz -f   # View logs"
