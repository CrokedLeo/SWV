# Deployment Guide

## Security Hardening

### HTTPS/TLS Enforcement

#### Let's Encrypt (Free SSL Certificate)

1. **Install Certbot on Ubuntu/EC2**
   ```bash
   sudo apt-get update
   sudo apt-get install -y certbot python3-certbot-nginx
   ```

2. **Obtain Certificate**
   ```bash
   sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com
   ```

3. **Configure Nginx with SSL**
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com www.your-domain.com;

       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
       
       # SSL security settings
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
       ssl_prefer_server_ciphers on;
       ssl_session_cache shared:SSL:10m;
       ssl_session_timeout 10m;
       
       # HSTS header (tell browsers to always use HTTPS)
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }

   # Redirect HTTP to HTTPS
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

4. **Setup Auto-Renewal**
   ```bash
   sudo systemctl enable certbot.timer
   sudo systemctl start certbot.timer
   ```

### Environment Configuration

Set the following in `.env` for production:

```bash
# Environment: development, staging, or production
ENVIRONMENT=production

# Enable HTTPS enforcement (requires valid SSL certificate)
HTTPS_ENABLED=true

# CORS Configuration - Only allow your app domains
CORS_ORIGINS=https://app.example.com,https://www.example.com,https://android-app.example.com

# Security: Change API key
API_KEY=your-very-secure-random-key-here
```

### CORS Configuration for Android App

For Android apps, add the app's origin to CORS_ORIGINS. If using a custom scheme (e.g., `app://`), configure your backend proxy or reverse proxy to forward requests properly.

**Example Android configuration:**

```bash
# If using HTTP on localhost for development
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# If using a specific app domain
CORS_ORIGINS=https://api.example.com,https://android-api.example.com
```

### Security Headers Explanation

The application automatically adds security headers to all responses:

| Header | Purpose | Value |
|--------|---------|-------|
| X-Content-Type-Options | Prevent MIME type sniffing | `nosniff` |
| X-Frame-Options | Prevent clickjacking attacks | `DENY` |
| X-XSS-Protection | Enable browser XSS filter | `1; mode=block` |
| Strict-Transport-Security (HSTS) | Force HTTPS (production only) | `max-age=31536000; includeSubDomains; preload` |
| Content-Security-Policy (CSP) | Prevent injection attacks | `default-src 'self'` |
| Referrer-Policy | Control referrer information | `strict-origin-when-cross-origin` |
| Permissions-Policy | Control browser features | Disables geolocation, microphone, camera |

## Production Deployment Options

### 1. Docker + AWS EC2

#### Prerequisites
- AWS account
- Docker installed locally

#### Steps

1. **Create EC2 Instance**
   ```bash
   # AWS CLI or Console
   # - Use Ubuntu 22.04 LTS
   # - Allow ports 80, 443, 8000
   # - Create security group
   ```

2. **Install Docker on EC2**
   ```bash
   ssh ubuntu@your-ec2-ip
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

3. **Deploy Application**
   ```bash
   git clone <your-repo>
   cd SWV
   docker-compose up -d
   ```

4. **Setup Nginx Reverse Proxy**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### 2. Heroku Deployment

```bash
heroku login
heroku create swv-api
git push heroku main
heroku config:set API_KEY=your-secret-key
```

### 3. Google Cloud Run

```bash
gcloud auth login
gcloud builds submit --tag gcr.io/PROJECT_ID/swv-api
gcloud run deploy swv-api \
  --image gcr.io/PROJECT_ID/swv-api \
  --platform managed \
  --region us-central1 \
  --set-env-vars API_KEY=your-secret-key
```

### 4. Azure Container Instances

```bash
az acr build --registry myregistry --image swv-api:latest .
az container create \
  --resource-group mygroup \
  --name swv-api \
  --image myregistry.azurecr.io/swv-api:latest \
  --ports 8000 \
  --environment-variables API_KEY=your-secret-key
```

## Production Checklist

### Security
- [ ] Set `ENVIRONMENT=production`
- [ ] Change `API_KEY` to a strong random value
- [ ] Enable `HTTPS_ENABLED=true`
- [ ] Obtain SSL/TLS certificate (Let's Encrypt recommended)
- [ ] Configure `CORS_ORIGINS` to only allow your app domains
- [ ] Verify all security headers are present in responses
- [ ] Test HTTPS redirect (HTTP → HTTPS)
- [ ] Enable and test HSTS header
- [ ] Configure firewall rules (allow only 80, 443)
- [ ] Disable debug mode (`DEBUG=false`)
- [ ] Setup security event logging
- [ ] Regular security audits

### Application
- [ ] Use production YOLO model (yolov8s or larger)
- [ ] Setup monitoring and logging
- [ ] Configure database backups
- [ ] Rate limiting enabled
- [ ] Use strong database passwords
- [ ] Regular security updates
- [ ] Setup health checks
- [ ] Configure auto-scaling if needed

## Scaling Tips

1. **Use Load Balancer** for multiple instances
2. **Cache results** to reduce processing
3. **Use GPU instances** for faster detection
4. **Implement queue system** for batch processing
5. **Monitor performance** with tools like Prometheus

## Monitoring

### Logs
```bash
# Docker
docker-compose logs -f api

# View specific errors
docker-compose logs api | grep ERROR
```

### Health Checks
```bash
curl http://your-domain/api/v1/health
```

### Metrics
- Response time
- Detection accuracy
- API usage
- Error rates
