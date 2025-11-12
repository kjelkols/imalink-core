#!/bin/bash
# Quick deployment script for imalink-core on DigitalOcean
# Run on server: bash deploy.sh

set -e  # Exit on error

echo "🚀 Deploying ImaLink Core to core.trollfjell.com..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Please run as root (sudo bash deploy.sh)"
    exit 1
fi

# Variables
REPO_URL="https://github.com/kjelkols/imalink-core.git"
INSTALL_DIR="/opt/imalink-core"
SERVICE_NAME="imalink-core"
DOMAIN="core.trollfjell.com"

# Step 1: Clone or update repository
echo "📦 Cloning/updating repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Step 2: Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "📥 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Step 3: Install dependencies
echo "📚 Installing Python dependencies..."
uv sync

# Step 4: Install systemd service
echo "⚙️  Installing systemd service..."
cp deploy/imalink-core.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# Step 5: Install Nginx config
echo "🌐 Installing Nginx configuration..."
cp deploy/nginx-core.trollfjell.com.conf /etc/nginx/sites-available/"$DOMAIN"
ln -sf /etc/nginx/sites-available/"$DOMAIN" /etc/nginx/sites-enabled/

# Test Nginx config
echo "✅ Testing Nginx configuration..."
nginx -t

# Step 6: Start/restart services
echo "🔄 Starting services..."
systemctl restart "$SERVICE_NAME"
systemctl reload nginx

# Step 7: Check status
echo "📊 Service status:"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Run: sudo certbot --nginx -d $DOMAIN"
echo "2. Test: curl https://$DOMAIN/"
echo "3. Check logs: sudo journalctl -u $SERVICE_NAME -f"
