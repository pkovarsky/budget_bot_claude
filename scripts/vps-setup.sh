#!/bin/bash
# 🖥️ VPS Setup Script for Budget Bot
# Run this script on your VPS to prepare it for deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root. Use sudo when needed."
   exit 1
fi

print_status "🚀 Setting up VPS for Budget Bot deployment..."

# Update system
print_status "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "🔧 Installing required packages..."
sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    htop \
    tree \
    jq \
    fail2ban \
    ufw \
    certbot \
    python3-certbot-nginx

# Install Docker
print_status "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_success "Docker installed successfully!"
else
    print_warning "Docker is already installed"
fi

# Install Docker Compose
print_status "🐳 Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    print_success "Docker Compose installed successfully!"
else
    print_warning "Docker Compose is already installed"
fi

# Setup directory structure
print_status "📁 Creating directory structure..."
sudo mkdir -p /opt/budget-bot/{data/{postgres,redis,grafana,prometheus,exports,charts},logs/nginx,backups,nginx,monitoring}
sudo chown -R $USER:$USER /opt/budget-bot
print_success "Directory structure created!"

# Setup firewall
print_status "🔒 Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 3000/tcp  # Grafana (optional)
sudo ufw allow 9090/tcp  # Prometheus (optional)
echo "y" | sudo ufw enable
print_success "Firewall configured!"

# Setup fail2ban
print_status "🛡️ Configuring fail2ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
print_success "Fail2ban configured!"

# Create nginx config
print_status "🌐 Creating nginx configuration..."
mkdir -p /opt/budget-bot/nginx
cat > /opt/budget-bot/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream budget_bot {
        server budget-bot:8080;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        listen 80;
        server_name _;
        
        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
        
        # Redirect to HTTPS (if SSL is configured)
        # return 301 https://$server_name$request_uri;
        
        # For now, proxy directly
        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://budget_bot;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    
    # HTTPS configuration (uncomment when SSL is set up)
    # server {
    #     listen 443 ssl http2;
    #     server_name your-domain.com;
    #     
    #     ssl_certificate /etc/nginx/ssl/cert.pem;
    #     ssl_certificate_key /etc/nginx/ssl/key.pem;
    #     
    #     location / {
    #         limit_req zone=api burst=20 nodelay;
    #         proxy_pass http://budget_bot;
    #         proxy_set_header Host $host;
    #         proxy_set_header X-Real-IP $remote_addr;
    #         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #         proxy_set_header X-Forwarded-Proto $scheme;
    #     }
    # }
}
EOF
print_success "Nginx configuration created!"

# Create monitoring configuration
print_status "📊 Creating monitoring configuration..."
mkdir -p /opt/budget-bot/monitoring
cat > /opt/budget-bot/monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  external_labels:
    monitor: 'budget-bot'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  
  - job_name: 'budget-bot'
    static_configs:
      - targets: ['budget-bot:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF
print_success "Monitoring configuration created!"

# Create backup script
print_status "💾 Creating backup script..."
cat > /opt/budget-bot/scripts/backup-postgres.sh << 'EOF'
#!/bin/bash
# PostgreSQL backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Create backup
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB > $BACKUP_DIR/backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/backup_$DATE.sql

# Remove old backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: backup_$DATE.sql.gz"
EOF
chmod +x /opt/budget-bot/scripts/backup-postgres.sh
print_success "Backup script created!"

# Create maintenance script
print_status "🔧 Creating maintenance script..."
cat > /opt/budget-bot/scripts/maintenance.sh << 'EOF'
#!/bin/bash
# Maintenance script for Budget Bot

cd /opt/budget-bot

echo "🧹 Running maintenance tasks..."

# Clean up old Docker images
echo "🐳 Cleaning Docker..."
docker system prune -f

# Backup database
echo "💾 Creating database backup..."
docker-compose -f docker-compose.prod.yml exec -T postgres /backup.sh

# Check disk space
echo "💾 Disk usage:"
df -h

# Check container health
echo "🏥 Container health:"
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
echo "📝 Recent errors in logs:"
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error || echo "No errors found"

echo "✅ Maintenance completed!"
EOF
chmod +x /opt/budget-bot/scripts/maintenance.sh
print_success "Maintenance script created!"

# Setup cron jobs
print_status "⏰ Setting up cron jobs..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/budget-bot/scripts/maintenance.sh >> /opt/budget-bot/logs/maintenance.log 2>&1") | crontab -
print_success "Cron jobs configured!"

# Setup log rotation
print_status "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/budget-bot > /dev/null << 'EOF'
/opt/budget-bot/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 0644 $(whoami) $(whoami)
}
EOF
print_success "Log rotation configured!"

# Create systemd service for auto-start
print_status "🔄 Creating systemd service..."
sudo tee /etc/systemd/system/budget-bot.service > /dev/null << EOF
[Unit]
Description=Budget Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/budget-bot
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
User=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable budget-bot
print_success "Systemd service created!"

# Generate SSH key for GitHub Actions (if not exists)
if [ ! -f ~/.ssh/id_rsa ]; then
    print_status "🔑 Generating SSH key for GitHub Actions..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
    print_success "SSH key generated!"
    print_warning "Add this public key to your server's authorized_keys:"
    cat ~/.ssh/id_rsa.pub
else
    print_warning "SSH key already exists"
fi

# Show next steps
print_success "🎉 VPS setup completed!"
print_status "📋 Next steps:"
echo "1. Add secrets to GitHub repository:"
echo "   - VPS_HOST: $(curl -s ifconfig.me)"
echo "   - VPS_USER: $USER"
echo "   - VPS_SSH_KEY: (copy from ~/.ssh/id_rsa)"
echo "   - TELEGRAM_BOT_TOKEN: your_bot_token"
echo "   - OPENAI_API_KEY: your_openai_key"
echo "   - POSTGRES_PASSWORD: secure_password"
echo "   - REDIS_PASSWORD: secure_password"
echo "   - GRAFANA_PASSWORD: secure_password"
echo ""
echo "2. Update your domain DNS to point to: $(curl -s ifconfig.me)"
echo ""
echo "3. Setup SSL certificate (optional):"
echo "   sudo certbot --nginx -d your-domain.com"
echo ""
echo "4. Push to GitHub to trigger deployment!"
echo ""
print_warning "Please logout and login again to use Docker without sudo"
print_status "VPS is ready for Budget Bot deployment! 🚀"