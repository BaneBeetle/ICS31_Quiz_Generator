# AWS EC2 Deployment Guide

This guide walks you through deploying the ICS31 Quiz Generator to AWS EC2.

## Prerequisites

- AWS Account
- OpenAI API Key

## Step 1: Launch EC2 Instance

1. Go to AWS Console > EC2 > Launch Instance
2. Choose settings:
   - **Name**: `quiz-generator`
   - **AMI**: Amazon Linux 2023 or Ubuntu 22.04 LTS
   - **Instance Type**: `t3.medium` (minimum recommended for video processing)
   - **Key pair**: Create or select existing
   - **Storage**: 30 GB gp3

3. Configure Security Group (allow inbound):
   | Type | Port | Source |
   |------|------|--------|
   | SSH | 22 | Your IP |
   | HTTP | 80 | 0.0.0.0/0 |
   | Custom TCP | 8000 | 0.0.0.0/0 |

4. Launch the instance

## Step 2: Connect to EC2

```bash
ssh -i your-key.pem ec2-user@<public-ip>
# or for Ubuntu:
ssh -i your-key.pem ubuntu@<public-ip>
```

## Step 3: Run Setup Script

```bash
# Download and run setup script
curl -O https://raw.githubusercontent.com/YOUR_USERNAME/ICS31_QuizGenerator/main/deploy/ec2-setup.sh
chmod +x ec2-setup.sh
./ec2-setup.sh

# Log out and back in for docker permissions
exit
# Reconnect via SSH
```

## Step 4: Clone and Configure

```bash
cd /opt/quiz-generator

# Clone repository
git clone https://github.com/YOUR_USERNAME/ICS31_QuizGenerator.git .

# Create environment file
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env

# Add your media (not in the repo or the image); docker-compose.yml mounts
# these folders into the container read-only
mkdir -p audio minecraft
#   audio/clock.mp3, optional audio/wii_shop.mp3, minecraft/minecraft1.mp4
#   e.g. from your machine: scp -i your-key.pem -r audio minecraft <user>@<public-ip>:/opt/quiz-generator/
```

## Step 5: Deploy

```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Step 6: Access Application

Open in browser: `http://<ec2-public-ip>:8000`

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Update and redeploy
git pull origin main
docker-compose up -d --build
```

## Optional: Set Up Domain with SSL

### Using Nginx as Reverse Proxy

1. Install Nginx:
```bash
sudo apt install nginx  # Ubuntu
sudo yum install nginx  # Amazon Linux
```

2. Create Nginx config `/etc/nginx/sites-available/quiz-generator`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

3. Enable and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/quiz-generator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. Install SSL with Certbot:
```bash
sudo apt install certbot python3-certbot-nginx  # Ubuntu
sudo certbot --nginx -d your-domain.com
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs quiz-generator
```

### Out of memory
- Upgrade to larger instance type (t3.large)
- Check video files aren't accumulating: `ls -la videos/`

### API key issues
- Verify .env file exists and has correct key
- Restart container: `docker-compose restart`

## Cost Estimation

- t3.medium: ~$30/month
- Storage (30GB): ~$2.40/month
- Data transfer: Variable

For lower costs, consider:
- Using t3.micro/small for testing
- Stopping instance when not in use
- Setting up auto-shutdown schedules
