# VPS Deployment Guide

This guide provides step-by-step instructions to deploy the Breaking B.A.D. FastAPI backend onto a Linux VPS (Virtual Private Server) such as Ubuntu 22.04 or 24.04.

## Is this project VPS ready?

**Yes, absolutely.** The codebase is thoroughly prepared for production environments:
- **Gunicorn Included**: `gunicorn` with `uvicorn` workers is already in `requirements.txt` (the standard for production Python ASGI servers).
- **Environment Management**: Utilizes `pydantic-settings` to securely manage secrets and configuration via a `.env` file instead of hardcoded variables.
- **Logging setup**: Has a robust structured logging module (`app/core/logging.py`) ready to stream output to system service logs.
- **Stateless backend**: The application stores state in MongoDB Atlas, meaning the backend itself is stateless and easily scalable.

*Before going live: set a strong `API_KEY` and `CLEANUP_PASSWORD`, use `LOG_FORMAT=json`, and leave `CORS_ORIGINS` empty unless a browser calls the API directly (breaking-bad-ui calls it server-side).*

---

## Deployment Steps (Ubuntu/Debian)

### 1. Prerequisites
SSH into your VPS and update your system packages:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git nginx -y
```

### 2. Clone the Repository
Create an unprivileged system user to run the service, then clone the app into `/var/www/` owned by that user:
```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin breakingbad
sudo git clone https://github.com/anfieldlad/breaking-bad-backend.git /var/www/breaking-bad-backend
sudo chown -R breakingbad:breakingbad /var/www/breaking-bad-backend
cd /var/www/breaking-bad-backend
```

### 3. Setup the Python Virtual Environment
Create an isolated environment and install the pinned dependencies:
```bash
sudo -u breakingbad python3 -m venv .venv
sudo -u breakingbad .venv/bin/pip install -r requirements.txt
```

### 4. Configure Environment Variables
You need a `.env` file for your production credentials.
```bash
sudo -u breakingbad cp .env.example .env
sudo chmod 600 .env
sudo -u breakingbad nano .env
```
Populate the `.env` file with your real `MONGO_URI`, `GEMINI_API_KEY`, and secure `API_KEY`. Be sure to update `EMBEDDING_MODEL` to `gemini-embedding-001`!

### 5. Create a Systemd Service
To ensure the backend runs continuously and restarts if the server reboots, we will create a systemctl service.

Create the service file:
```bash
sudo nano /etc/systemd/system/breakingbad.service
```
Paste the following configuration:
```ini
[Unit]
Description=Gunicorn daemon for Breaking Bad Backend
After=network.target

[Service]
User=breakingbad
Group=breakingbad
WorkingDirectory=/var/www/breaking-bad-backend
Environment="PATH=/var/www/breaking-bad-backend/.venv/bin"
ExecStart=/var/www/breaking-bad-backend/.venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --timeout 120
Restart=on-failure
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```
Start and enable the service:
```bash
sudo systemctl start breakingbad
sudo systemctl enable breakingbad
```
*(You can check if it's running smoothly via `sudo systemctl status breakingbad` and `curl http://127.0.0.1:8001/health/ready`)*

### 6. Point DNS to Your VPS (Domain Setup)
Before setting up Nginx, you must point your domain (e.g., `breaking-backend.badai.app`) to your VPS.
1. Login to your Domain Registrar (Cloudflare, Niagahoster, Namecheap, etc.)
2. Go to DNS Management.
3. Add a new **A Record**:
   - **Name/Host:** `breaking-backend` (if you want `breaking-backend.badai.app`) or `@` (for root domain).
   - **Value/Target:** `IP_PUBLIC_VPS_ANDA` (Your VPS's public IP address).
   - **TTL:** Auto / Default.
4. Wait a few moments for DNS propagation.

### 7. Setup Nginx Reverse Proxy
Nginx will handle incoming HTTP requests from the outside world and forward them to Gunicorn.

Create a new Nginx configuration:
```bash
sudo nano /etc/nginx/sites-available/breakingbad
```
Paste this configuration:
```nginx
# Per-IP rate limit for the expensive endpoints (LLM + embedding calls).
limit_req_zone $binary_remote_addr zone=bb_api:10m rate=30r/m;

server {
    listen 80;
    server_name breaking-backend.badai.app;

    # Must be >= MAX_UPLOAD_MB (Nginx defaults to 1 MB and would reject
    # larger PDFs with its own 413 before they reach the app).
    client_max_body_size 12m;

    location /api/ {
        limit_req zone=bb_api burst=10 nodelay;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for streaming SSE responses (Chat endpoint)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Required for streaming SSE responses (Chat endpoint)
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        proxy_read_timeout 86400;
    }
}
```
> **Rate limiting note:** the limit is per client IP. If the API is only called
> by the breaking-bad-ui server (its `/api` proxy), every user shares that one
> IP, so apply per-user limits in front of the UI instead and raise or remove
> the backend limit.

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/breakingbad /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Secure with SSL (Certbot / HTTPS)
Now that your DNS is pointed to the VPS and Nginx is ready, you can easily secure it with an SSL certificate to get `https://`:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d breaking-backend.badai.app
```

## 🔄 Running Multiple Python Projects on One VPS
If you have other Python applications running on the exact same VPS, you don't need to worry about conflicts if you follow two rules:

1. **Virtual Environments:** Because we set up the `.venv` directory (Step 3), the dependencies for `breaking-bad-backend` are completely isolated. It will not break or conflict with modules globally installed or in other projects' environments.
2. **Port Allocation:** By default, if your *other* Python project is using port `8000`, the new service will fail to start. 
   - Note that I have pre-configured this guide to use port `8001` (see Step 5 and Step 6). Jadi Anda tinggal Copy-Paste saja dari panduan ini dan biarkan `127.0.0.1:8001`, maka ia akan berjalan aman di port 8001 tanpa mengganggu project 8000 Anda!

Your VPS backend is now fully live and accessible from the public web!
