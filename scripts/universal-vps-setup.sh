#!/bin/bash
# 🖥️ Universal VPS Setup Script for Budget Bot
# Automatically detects Linux distribution and uses appropriate package manager
# Supports Ubuntu/Debian (apt), CentOS/RHEL/Rocky (yum/dnf), and others

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

# Detect Linux distribution
detect_distro() {
    print_status "🔍 Detecting Linux distribution..."
    
    # Method 1: Check /etc/os-release
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=${ID:-unknown}
        VERSION=${VERSION_ID:-unknown}
        print_status "Found os-release: $DISTRO $VERSION"
    
    # Method 2: Check for specific release files
    elif [ -f /etc/redhat-release ]; then
        if grep -qi "centos" /etc/redhat-release; then
            DISTRO="centos"
        elif grep -qi "red hat" /etc/redhat-release; then
            DISTRO="rhel"
        elif grep -qi "rocky" /etc/redhat-release; then
            DISTRO="rocky"
        else
            DISTRO="rhel"
        fi
        VERSION=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
        print_status "Found redhat-release: $DISTRO $VERSION"
    
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
        VERSION=$(cat /etc/debian_version)
        print_status "Found debian_version: $DISTRO $VERSION"
    
    # Method 3: Check for package managers
    elif command -v apt &> /dev/null; then
        DISTRO="debian"
        VERSION="unknown"
        print_status "Found apt package manager, assuming Debian-based"
    
    elif command -v yum &> /dev/null; then
        DISTRO="centos"
        VERSION="unknown"
        print_status "Found yum package manager, assuming Red Hat-based"
    
    elif command -v dnf &> /dev/null; then
        DISTRO="fedora"
        VERSION="unknown"
        print_status "Found dnf package manager, assuming Fedora-based"
    
    elif command -v pacman &> /dev/null; then
        DISTRO="arch"
        VERSION="unknown"
        print_status "Found pacman package manager, assuming Arch-based"
    
    elif command -v zypper &> /dev/null; then
        DISTRO="opensuse"
        VERSION="unknown"
        print_status "Found zypper package manager, assuming openSUSE-based"
    
    # Method 4: Check uname for some hints
    elif uname -a | grep -qi "ubuntu"; then
        DISTRO="ubuntu"
        VERSION="unknown"
        print_status "Found Ubuntu in uname output"
    
    elif uname -a | grep -qi "debian"; then
        DISTRO="debian"
        VERSION="unknown"
        print_status "Found Debian in uname output"
    
    else
        print_error "Cannot detect Linux distribution"
        print_status "Available files:"
        ls -la /etc/*release* /etc/*version* 2>/dev/null || echo "No release files found"
        print_status "Available package managers:"
        which apt yum dnf pacman zypper 2>/dev/null || echo "No known package managers found"
        print_status "System info:"
        uname -a
        exit 1
    fi
    
    print_success "🔍 Detected distribution: $DISTRO $VERSION"
}

# Install packages based on distribution
install_packages() {
    local packages="curl wget git unzip htop tree jq fail2ban certbot"
    
    case $DISTRO in
        ubuntu|debian)
            print_status "📦 Using APT package manager..."
            sudo apt update && sudo apt upgrade -y
            sudo apt install -y $packages ufw python3-certbot-nginx
            FIREWALL_CMD="ufw"
            ;;
        centos|rhel|rocky|almalinux|fedora)
            print_status "📦 Using YUM/DNF package manager..."
            if command -v dnf &> /dev/null; then
                PKG_MGR="dnf"
            else
                PKG_MGR="yum"
            fi
            
            sudo $PKG_MGR update -y
            
            # Enable EPEL repository for additional packages
            if [[ $DISTRO == "centos" || $DISTRO == "rhel" || $DISTRO == "rocky" || $DISTRO == "almalinux" ]]; then
                sudo $PKG_MGR install -y epel-release
            fi
            
            sudo $PKG_MGR install -y $packages firewalld python3-certbot-nginx
            FIREWALL_CMD="firewalld"
            ;;
        arch|manjaro)
            print_status "📦 Using Pacman package manager..."
            sudo pacman -Syu --noconfirm
            sudo pacman -S --noconfirm $packages ufw certbot-nginx
            FIREWALL_CMD="ufw"
            ;;
        opensuse*|sles)
            print_status "📦 Using Zypper package manager..."
            sudo zypper refresh && sudo zypper update -y
            sudo zypper install -y $packages firewalld python3-certbot-nginx
            FIREWALL_CMD="firewalld"
            ;;
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_status "Please install manually: $packages"
            exit 1
            ;;
    esac
}

# Install Docker
install_docker() {
    print_status "🐳 Installing Docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh
        
        # Start and enable Docker
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # Add current user to docker group
        sudo usermod -aG docker $USER
        
        print_success "Docker installed successfully"
    else
        print_warning "Docker is already installed"
    fi
}

# Install Docker Compose
install_docker_compose() {
    print_status "🔧 Installing Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        # Get latest version
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
        
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        # Create symlink for easier access
        sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose 2>/dev/null || true
        
        print_success "Docker Compose installed successfully"
    else
        print_warning "Docker Compose is already installed"
    fi
}

# Configure firewall
configure_firewall() {
    print_status "🔥 Configuring firewall..."
    
    case $FIREWALL_CMD in
        ufw)
            sudo ufw --force enable
            sudo ufw default deny incoming
            sudo ufw default allow outgoing
            sudo ufw allow ssh
            sudo ufw allow 80/tcp
            sudo ufw allow 443/tcp
            sudo ufw reload
            ;;
        firewalld)
            sudo systemctl start firewalld
            sudo systemctl enable firewalld
            sudo firewall-cmd --permanent --add-service=ssh
            sudo firewall-cmd --permanent --add-service=http
            sudo firewall-cmd --permanent --add-service=https
            sudo firewall-cmd --reload
            ;;
    esac
    
    print_success "Firewall configured successfully"
}

# Configure fail2ban
configure_fail2ban() {
    print_status "🛡️ Configuring fail2ban..."
    
    sudo systemctl start fail2ban
    sudo systemctl enable fail2ban
    
    # Create custom jail configuration
    sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
EOF
    
    sudo systemctl restart fail2ban
    print_success "Fail2ban configured successfully"
}

# Create budget bot user and directories
setup_budget_bot() {
    print_status "👤 Setting up Budget Bot user and directories..."
    
    # Create budget user if it doesn't exist
    if ! id "budget" &>/dev/null; then
        sudo useradd -m -s /bin/bash budget
        sudo usermod -aG docker budget
        print_success "Created budget user"
    else
        print_warning "Budget user already exists"
    fi
    
    # Create application directories
    sudo mkdir -p /opt/budget-bot/{data/{postgres,redis,grafana,prometheus,exports,charts},backups,logs/nginx}
    
    # Set permissions
    sudo chown -R budget:budget /opt/budget-bot
    sudo chmod -R 755 /opt/budget-bot
    
    print_success "Budget Bot directories created"
}

# Install monitoring tools
install_monitoring() {
    print_status "📊 Setting up monitoring tools..."
    
    # Create monitoring directories
    sudo mkdir -p /opt/budget-bot/monitoring/{prometheus,grafana}
    
    # Create Prometheus configuration
    sudo tee /opt/budget-bot/monitoring/prometheus/prometheus.yml > /dev/null <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
      
  - job_name: 'budget-bot'
    static_configs:
      - targets: ['budget-bot:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    scrape_interval: 30s
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 30s
EOF
    
    sudo chown -R budget:budget /opt/budget-bot/monitoring
    print_success "Monitoring configuration created"
}

# Create systemd service for automatic startup
create_systemd_service() {
    print_status "⚙️ Creating systemd service..."
    
    sudo tee /etc/systemd/system/budget-bot.service > /dev/null <<EOF
[Unit]
Description=Budget Bot Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/budget-bot
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
User=budget
Group=budget

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    print_success "Systemd service created"
}

# Setup automatic backups
setup_backups() {
    print_status "💾 Setting up automatic backups..."
    
    # Create backup script
    sudo tee /opt/budget-bot/scripts/backup.sh > /dev/null <<'EOF'
#!/bin/bash
cd /opt/budget-bot
/usr/local/bin/docker-compose -f docker-compose.prod.yml exec -T postgres /backup.sh
EOF
    
    sudo chmod +x /opt/budget-bot/scripts/backup.sh
    sudo chown budget:budget /opt/budget-bot/scripts/backup.sh
    
    # Add to crontab for budget user
    sudo -u budget bash -c '(crontab -l 2>/dev/null; echo "0 2 * * * /opt/budget-bot/scripts/backup.sh") | crontab -'
    
    print_success "Automatic backups configured (daily at 2 AM)"
}

# Create environment file template
create_env_template() {
    print_status "📝 Creating environment template..."
    
    sudo tee /opt/budget-bot/.env.template > /dev/null <<EOF
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
POSTGRES_DB=budget_bot
POSTGRES_USER=budget_user
POSTGRES_PASSWORD=your_secure_password_here

# Redis Configuration
REDIS_PASSWORD=your_redis_password_here

# Security
SECRET_KEY=your_secret_key_here

# Monitoring (optional)
GRAFANA_ADMIN_PASSWORD=your_grafana_password_here

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_WEBHOOK_URL=your_webhook_url_for_notifications
EOF
    
    sudo chown budget:budget /opt/budget-bot/.env.template
    
    print_warning "⚠️ Don't forget to:"
    print_warning "1. Copy .env.template to .env: cp /opt/budget-bot/.env.template /opt/budget-bot/.env"
    print_warning "2. Edit .env with your actual values: nano /opt/budget-bot/.env"
    print_warning "3. Download your docker-compose.prod.yml and other config files to /opt/budget-bot/"
}

# Main execution
main() {
    detect_distro
    install_packages
    install_docker
    install_docker_compose
    configure_firewall
    configure_fail2ban
    setup_budget_bot
    install_monitoring
    create_systemd_service
    setup_backups
    create_env_template
    
    print_success "🎉 VPS setup completed successfully!"
    print_status "📋 Next steps:"
    echo "1. Log out and log back in (or run: newgrp docker)"
    echo "2. Copy your application files to /opt/budget-bot/"
    echo "3. Configure your .env file with actual values"
    echo "4. Run: cd /opt/budget-bot && docker-compose -f docker-compose.prod.yml up -d"
    echo "5. Enable auto-start: sudo systemctl enable budget-bot"
    echo ""
    print_status "🔗 Useful commands:"
    echo "• Check status: docker-compose -f /opt/budget-bot/docker-compose.prod.yml ps"
    echo "• View logs: docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs -f"
    echo "• Restart services: sudo systemctl restart budget-bot"
    echo "• Access database: docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot"
}

# Run main function
main "$@"