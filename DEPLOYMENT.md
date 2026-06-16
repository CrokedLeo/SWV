# Deployment Guide

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

- [ ] Change API_KEY in .env
- [ ] Set DEBUG=false
- [ ] Use production YOLO model (yolov8s or larger)
- [ ] Enable HTTPS/SSL
- [ ] Setup monitoring and logging
- [ ] Configure database backups
- [ ] Setup rate limiting
- [ ] Enable CORS only for your domain
- [ ] Use strong database passwords
- [ ] Regular security updates

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
