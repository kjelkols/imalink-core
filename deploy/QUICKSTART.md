# Quick Deployment Commands for core.trollfjell.com

## Initial Setup

```bash
# 1. Klon repository
cd ~
git clone https://github.com/kjelkols/imalink-core.git
cd imalink-core

# 2. Installer dependencies
uv sync

# 3. Test at det fungerer
uv run uvicorn service.main:app --host 127.0.0.1 --port 8765
# Ctrl+C for å stoppe

# 4. Rediger systemd service (endre User, Group, WorkingDirectory)
sudo nano /tmp/imalink-core.service
# Kopier fra deploy/imalink-core.service og oppdater:
# User=dinbruker
# Group=dinbruker
# WorkingDirectory=/home/dinbruker/imalink-core

# 5. Installer systemd service
sudo cp /tmp/imalink-core.service /etc/systemd/system/imalink-core.service
sudo systemctl daemon-reload
sudo systemctl enable imalink-core
sudo systemctl start imalink-core
sudo systemctl status imalink-core

# 6. Installer Nginx config
sudo cp deploy/nginx-core.trollfjell.com.conf /etc/nginx/sites-available/core.trollfjell.com
sudo ln -s /etc/nginx/sites-available/core.trollfjell.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 7. SSL-sertifikat
sudo certbot --nginx -d core.trollfjell.com

# 8. Test
curl https://core.trollfjell.com/
```

## Oppdatering (etter git pull)

```bash
cd ~/imalink-core
git pull
uv sync
sudo systemctl restart imalink-core
sudo systemctl status imalink-core
```

## Nyttige kommandoer

```bash
# Se logs
sudo journalctl -u imalink-core -f

# Restart service
sudo systemctl restart imalink-core

# Stopp service
sudo systemctl stop imalink-core

# Se status
sudo systemctl status imalink-core
```
