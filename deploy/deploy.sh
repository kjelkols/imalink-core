#!/bin/bash
# Quick deployment script for imalink-core on DigitalOcean
# Run on server: bash deploy.sh

set -e  # Exit on error

echo "🚀 Deploying ImaLink Core to core.trollfjell.com..."

# Variables
REPO_URL="https://github.com/kjelkols/imalink-core.git"
INSTALL_DIR="$HOME/imalink-core"  # Installer i brukerens hjemmekatalog
SERVICE_NAME="imalink-core"
DOMAIN="core.trollfjell.com"
CURRENT_USER=$(whoami)

echo "📍 Installing to: $INSTALL_DIR"
echo "👤 Running as: $CURRENT_USER"

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

# Create temporary service file with correct paths
sed -e "s|User=www-data|User=$CURRENT_USER|g" \
    -e "s|Group=www-data|Group=$CURRENT_USER|g" \
    -e "s|WorkingDirectory=/opt/imalink-core|WorkingDirectory=$INSTALL_DIR|g" \
    deploy/imalink-core.service > /tmp/imalink-core.service

sudo cp /tmp/imalink-core.service /etc/systemd/system/
rm /tmp/imalink-core.service

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Step 5: Install Nginx config
echo "🌐 Installing Nginx configuration..."
sudo cp deploy/nginx-core.trollfjell.com.conf /etc/nginx/sites-available/"$DOMAIN"
sudo ln -sf /etc/nginx/sites-available/"$DOMAIN" /etc/nginx/sites-enabled/

# Test Nginx config
echo "✅ Testing Nginx configuration..."
sudo nginx -t

# Step 6: Start/restart services
echo "🔄 Starting services..."
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl reload nginx

# Step 7: Check status
echo "📊 Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Run: sudo certbot --nginx -d $DOMAIN"
echo "2. Test: curl https://$DOMAIN/"
echo "3. Check logs: sudo journalctl -u $SERVICE_NAME -f"
