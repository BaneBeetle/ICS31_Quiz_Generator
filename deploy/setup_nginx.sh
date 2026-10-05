#!/bin/bash
# ICS31 Quiz Generator - Nginx Reverse Proxy Setup
# Security-hardened configuration with rate limiting and size limits

set -e

echo "Setting up Nginx reverse proxy with security hardening..."

# Create Nginx config with security best practices
sudo tee /etc/nginx/sites-available/ics31-quiz > /dev/null <<'EOF'
# =============================================================================
# SECURITY: Rate limiting zones (STRIDE: DoS protection)
# =============================================================================
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=generate_limit:10m rate=1r/m;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

server {
    listen 80;
    server_name _;

    # ==========================================================================
    # SECURITY: Request size limits (STRIDE: DoS protection)
    # ==========================================================================
    # Small limit for API requests (topic is max 100 chars)
    client_max_body_size 1K;

    # Limit request line and headers
    large_client_header_buffers 4 8k;

    # Connection limits per IP
    limit_conn conn_limit 10;

    # ==========================================================================
    # SECURITY: Timeouts (STRIDE: DoS - Slowloris protection)
    # ==========================================================================
    client_body_timeout 10s;
    client_header_timeout 10s;
    send_timeout 10s;

    # Keep-alive settings
    keepalive_timeout 30s;
    keepalive_requests 100;

    # ==========================================================================
    # SECURITY: Hide server version
    # ==========================================================================
    server_tokens off;

    # ==========================================================================
    # SECURITY: Headers
    # ==========================================================================
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # ==========================================================================
    # API: Video generation endpoint (strict rate limit)
    # ==========================================================================
    location /api/generate {
        # Rate limit: 1 request per minute burst 2
        limit_req zone=generate_limit burst=2 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Longer timeout for generation start
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # ==========================================================================
    # API: Video streaming/download (larger size, longer timeout)
    # ==========================================================================
    location ~ ^/api/video/[a-f0-9-]+(/stream)?$ {
        limit_req zone=api_limit burst=5 nodelay;

        # Allow larger responses for video files
        proxy_max_temp_file_size 0;
        proxy_buffering off;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Longer timeout for video streaming
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # ==========================================================================
    # API: All other endpoints
    # ==========================================================================
    location /api/ {
        limit_req zone=api_limit burst=10 nodelay;
        limit_req_status 429;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # ==========================================================================
    # Static files and frontend
    # ==========================================================================
    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # ==========================================================================
    # SECURITY: Block common attack paths
    # ==========================================================================
    location ~ /\. {
        deny all;
        return 404;
    }

    location ~* \.(git|env|htaccess|htpasswd|ini|log|sh|sql|conf|bak)$ {
        deny all;
        return 404;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/ics31-quiz /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
echo "Testing Nginx configuration..."
sudo nginx -t

sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "Nginx configured with security hardening!"
echo "=========================================="
echo ""
echo "Security features enabled:"
echo "  - Request body size limit: 1KB (API)"
echo "  - Rate limiting: 10 req/s general, 1 req/min for generate"
echo "  - Connection limit: 10 per IP"
echo "  - Slowloris protection: 10s timeouts"
echo "  - Security headers: X-Frame-Options, X-Content-Type-Options, etc."
echo "  - Server version hidden"
echo ""
echo "Your app is now accessible at: http://$(curl -s ifconfig.me)"
