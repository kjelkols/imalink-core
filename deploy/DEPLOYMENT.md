# ImaLink Core - DigitalOcean Deployment Guide

Deployment til **core.trollfjell.com** på DigitalOcean server.

## Forutsetninger

- SSH-tilgang til DigitalOcean-serveren
- DNS A-record for `core.trollfjell.com` peker til serverens IP
- Nginx og Certbot installert på serveren
- uv package manager installert

## Deployment-steg

### 1. Koble til serveren

```bash
ssh <bruker>@<server-ip>
# eller: ssh root@<server-ip>
```

### 2. Klon repository

```bash
# Klon til din hjemmekatalog (anbefalt for personlig server)
cd ~
git clone https://github.com/kjelkols/imalink-core.git
cd imalink-core

# Alternativt til /opt (krever root):
# cd /opt
# sudo git clone https://github.com/kjelkols/imalink-core.git
# cd imalink-core
```

### 3. Installer avhengigheter

```bash
# Installer uv hvis ikke allerede installert
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env  # eller logg ut og inn igjen

# Installer Python-avhengigheter
uv sync
```

### 4. Test at servicen fungerer

```bash
# Test lokalt først
uv run uvicorn service.main:app --host 127.0.0.1 --port 8765

# I en annen terminal (på serveren):
curl http://127.0.0.1:8765/
# Forventet output: {"service": "ImaLink Core API", "version": "1.0.0", "status": "healthy"}

# Ctrl+C for å stoppe test
```

### 5. Installer systemd service

```bash
# Kopier service-fil
sudo cp deploy/imalink-core.service /etc/systemd/system/

# VIKTIG: Oppdater User, Group og WorkingDirectory i service-filen
# Erstatt www-data med din bruker og /opt/imalink-core med din sti
sudo nano /etc/systemd/system/imalink-core.service

# Eksempel endringer:
# User=dinbruker
# Group=dinbruker  
# WorkingDirectory=/home/dinbruker/imalink-core

# Reload systemd og start service
sudo systemctl daemon-reload
sudo systemctl enable imalink-core
sudo systemctl start imalink-core

# Sjekk status
sudo systemctl status imalink-core
```

### 6. Konfigurer Nginx reverse proxy

```bash
# Kopier Nginx-config
sudo cp deploy/nginx-core.trollfjell.com.conf /etc/nginx/sites-available/core.trollfjell.com

# Aktiver site
sudo ln -s /etc/nginx/sites-available/core.trollfjell.com /etc/nginx/sites-enabled/

# Test Nginx-config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 7. Sett opp SSL med Let's Encrypt

```bash
# Installer SSL-sertifikat
sudo certbot --nginx -d core.trollfjell.com

# Certbot vil automatisk oppdatere Nginx-config
# Velg alternativ 2: Redirect HTTP til HTTPS
```

### 8. Verifiser deployment

```bash
# Test API lokalt
curl https://core.trollfjell.com/

# Test file upload (fra lokal maskin)
curl -X POST https://core.trollfjell.com/v1/process \
  -F "file=@testbilde.jpg" \
  -F "coldpreview_size=2560"
```

## Vedlikehold

### Sjekk logs

```bash
# Service logs
sudo journalctl -u imalink-core -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart service

```bash
sudo systemctl restart imalink-core
```

### Oppdater kode

```bash
cd ~/imalink-core  # eller din installasjonsti
git pull
uv sync  # Hvis nye dependencies
sudo systemctl restart imalink-core
```

### Sjekk service status

```bash
sudo systemctl status imalink-core
```

## Feilsøking

### Service starter ikke

```bash
# Sjekk logs
sudo journalctl -u imalink-core -n 50

# Sjekk at uv er tilgjengelig
which uv

# Sjekk at stien i service-filen er riktig
sudo nano /etc/systemd/system/imalink-core.service

# Test manuelt
cd ~/imalink-core  # eller din installasjonsti
uv run uvicorn service.main:app --host 127.0.0.1 --port 8765
```

### Nginx feil

```bash
# Test config
sudo nginx -t

# Sjekk logs
sudo tail -f /var/log/nginx/error.log
```

### Port allerede i bruk

```bash
# Finn hva som bruker port 8765
sudo lsof -i :8765
```

## Sikkerhet

- Servicen kjører kun på localhost (127.0.0.1:8765)
- All ekstern trafikk går gjennom Nginx reverse proxy
- HTTPS påkrevd (HTTP redirects til HTTPS)
- Max upload size: 50MB (kan justeres i Nginx-config)

## Tilpasninger

### Endre port

1. Endre port i `/etc/systemd/system/imalink-core.service` (linje med `--port`)
2. Endre port i `/etc/nginx/sites-available/core.trollfjell.com` (linje med `proxy_pass`)
3. Restart begge:
   ```bash
   sudo systemctl restart imalink-core
   sudo systemctl reload nginx
   ```

### Endre bruker

Standard bruker er `www-data`. For å bruke samme bruker som backend:

```bash
sudo nano /etc/systemd/system/imalink-core.service
# Endre User= og Group= til riktig bruker
sudo systemctl daemon-reload
sudo systemctl restart imalink-core
```

## Monitorering

### Healthcheck endpoint

```bash
curl https://core.trollfjell.com/health
```

### Automatisk restart ved feil

Systemd-servicen er konfigurert til automatisk restart ved feil:
- `Restart=always`
- `RestartSec=10` (venter 10 sekunder før restart)
