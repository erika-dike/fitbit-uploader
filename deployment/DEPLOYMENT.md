# Fitbit Uploader — Deployment Guide

Deploys to a DigitalOcean droplet behind nginx + Cloudflare.

- **Domain**: your subdomain (e.g. `fitbit.yourdomain.com`) via Cloudflare DNS
- **VPS path**: `/opt/fitbit-uploader`
- **Port**: `8585` (behind nginx)
- **Systemd service**: `fitbit-uploader`

## Prerequisites

- SSH access to your VPS (`root@YOUR_VPS_IP`)
- Python 3 installed on the droplet
- nginx and Certbot already set up
- A subdomain pointing to the droplet IP in Cloudflare

## First-Time Setup (on VPS)

### 1. Create app directory and upload files

From your **local machine** (project root):

```bash
DEPLOY_SERVER=YOUR_VPS_IP SSH_KEY=~/.ssh/your_key ./deployment/scripts/deploy.sh
```

This rsyncs the project, creates a venv, and installs dependencies.

### 2. Copy secret files to the VPS

These files are gitignored and must be copied manually:

```bash
# .env (API keys, Fitbit creds, Google Sheet ID)
scp .env root@YOUR_VPS_IP:/opt/fitbit-uploader/.env

# Google service account key
scp your-service-account.json root@YOUR_VPS_IP:/opt/fitbit-uploader/

# Fitbit OAuth tokens (run `python main.py auth` locally first)
scp tokens.json root@YOUR_VPS_IP:/opt/fitbit-uploader/tokens.json
```

### 3. Set up nginx

```bash
ssh root@YOUR_VPS_IP

# Copy config (edit deployment/nginx/fitbit.conf with your domain first)
cp /opt/fitbit-uploader/deployment/nginx/fitbit.conf /etc/nginx/sites-available/fitbit.conf
ln -s /etc/nginx/sites-available/fitbit.conf /etc/nginx/sites-enabled/

# Test and reload
nginx -t && systemctl reload nginx
```

### 4. Set up SSL with Certbot

```bash
certbot --nginx -d fitbit.yourdomain.com
```

### 5. Cloudflare SSL setting

Since the domain goes through Cloudflare, set the SSL/TLS mode to **Full (strict)** in the Cloudflare dashboard. This ensures Cloudflare talks HTTPS to your origin server (which has a real Let's Encrypt cert).

If you get a 502 Bad Gateway from Cloudflare, this is the most likely cause — Cloudflare is trying HTTP to your origin but nginx is redirecting to HTTPS.

### 6. Install and start the systemd service

```bash
cp /opt/fitbit-uploader/deployment/systemd/fitbit-uploader.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable fitbit-uploader
systemctl start fitbit-uploader
```

### 7. Verify

```bash
# Check service is running
systemctl status fitbit-uploader

# Test locally on VPS
curl http://127.0.0.1:8585/fetch?key=YOUR_API_KEY

# Test from anywhere
curl https://fitbit.yourdomain.com/fetch?key=YOUR_API_KEY
```

## Subsequent Deployments

After making code changes locally:

```bash
DEPLOY_SERVER=YOUR_VPS_IP SSH_KEY=~/.ssh/your_key ./deployment/scripts/deploy.sh
```

The script rsyncs files (skipping `.env`, `tokens.json`, and credential files), reinstalls dependencies, and restarts the service.

## Refreshing Fitbit OAuth Token

The Fitbit OAuth token expires periodically. When it does, all fetchers will fail with `missing_token`. To refresh:

```bash
# Run auth flow locally (requires browser)
python main.py auth

# Copy new token to VPS
scp tokens.json root@YOUR_VPS_IP:/opt/fitbit-uploader/tokens.json

# Restart service to pick up new token
ssh root@YOUR_VPS_IP "systemctl restart fitbit-uploader"
```

## Usage

From any browser or phone:

```
https://fitbit.yourdomain.com/fetch?key=YOUR_API_KEY
```

Fetch a specific date:

```
https://fitbit.yourdomain.com/fetch?key=YOUR_API_KEY&date=2026-02-20
```

## Monitoring

```bash
# Service status
ssh root@YOUR_VPS_IP "systemctl status fitbit-uploader"

# Live logs
ssh root@YOUR_VPS_IP "journalctl -u fitbit-uploader -f"

# Last 50 log lines
ssh root@YOUR_VPS_IP "journalctl -u fitbit-uploader -n 50"

# Nginx logs
ssh root@YOUR_VPS_IP "tail -f /var/log/nginx/fitbit.access.log"
ssh root@YOUR_VPS_IP "tail -f /var/log/nginx/fitbit.error.log"
```

## Troubleshooting

### 502 Bad Gateway from Cloudflare
1. Check the service is running: `systemctl status fitbit-uploader`
2. Check Cloudflare SSL mode is **Full (strict)**
3. Test locally on VPS: `curl http://127.0.0.1:8585/fetch?key=YOUR_KEY`

### All fetchers fail with `missing_token`
Fitbit OAuth token expired. See "Refreshing Fitbit OAuth Token" above.

### Service won't start
```bash
journalctl -u fitbit-uploader -n 50
# Common: missing .env, missing tokens.json, missing service account JSON
```

## File Layout on VPS

```
/opt/fitbit-uploader/
├── .env                          # secrets (manual copy)
├── tokens.json                   # Fitbit OAuth token (manual copy)
├── service_account.json          # Google service account key (manual copy)
├── config.py
├── fitbit_auth.py
├── fitbit_client.py
├── main.py
├── server.py
├── sheets_writer.py
├── requirements.txt
├── deployment/
│   ├── nginx/fitbit.conf
│   ├── systemd/fitbit-uploader.service
│   └── scripts/deploy.sh
└── venv/

/etc/nginx/sites-enabled/fitbit.conf  → symlink
/etc/systemd/system/fitbit-uploader.service → copy
```
