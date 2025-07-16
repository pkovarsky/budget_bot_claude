# 🖥️ Complete VPS Setup Guide for Budget Bot

## 📋 Table of Contents
1. [VPS Purchase (DigitalOcean)](#vps-purchase-digitalocean)
2. [Initial Server Setup](#initial-server-setup)
3. [Security Configuration](#security-configuration)
4. [Budget Bot Installation](#budget-bot-installation)
5. [Configuration](#configuration)
6. [Launch and Testing](#launch-and-testing)
7. [Maintenance](#maintenance)

---

## 🌐 VPS Purchase (DigitalOcean)

### Step 1: Create DigitalOcean Account

1. **Go to DigitalOcean**
   - Visit: https://www.digitalocean.com
   - Click "Sign Up"
   - Register with email or GitHub

2. **Account Verification**
   - Verify your email
   - Add payment method (credit card or PayPal)
   - You may get $100-200 credit for new accounts

### Step 2: Create a Droplet

1. **Start Creation**
   - Click "Create" → "Droplets"

2. **Choose Image**
   - Select **Ubuntu 22.04 (LTS) x64**

3. **Choose Plan**
   - Select **Basic**
   - Choose **$6/month** (1GB RAM, 1 vCPU, 25GB SSD)

4. **Choose Region**
   - Select region closest to you or your users
   - Recommended: **Amsterdam**, **Frankfurt**, or **London**

5. **Authentication**
   - **Option A: SSH Key (Recommended)**
     ```bash
     # On your computer, create SSH key
     ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
     
     # Copy public key
     cat ~/.ssh/id_rsa.pub
     ```
     - Paste the content in "SSH Keys" field
   
   - **Option B: Password**
     - Use strong password (will be emailed to you)

6. **Finalize**
   - Give your droplet a name: `budget-bot-server`
   - Click "Create Droplet"
   - Wait 1-2 minutes for creation

7. **Note Your IP Address**
   - Copy the IP address (e.g., `203.0.113.15`)
   - You'll need this for SSH connection

---

## 🔐 Initial Server Setup

### Step 1: Connect to Server

**If using SSH key:**
```bash
ssh root@YOUR_VPS_IP
```

**If using password:**
```bash
ssh root@YOUR_VPS_IP
# Enter password when prompted
```

### Step 2: System Update

```bash
# Update package list and upgrade system
apt update && apt upgrade -y

# Install essential packages
apt install -y curl wget git unzip htop tree nano fail2ban ufw
```

### Step 3: Create User

```bash
# Create new user (replace 'budget' with your preferred username)
adduser budget
usermod -aG sudo budget

# Copy SSH key to new user (if you used SSH key)
mkdir -p /home/budget/.ssh
cp ~/.ssh/authorized_keys /home/budget/.ssh/
chown -R budget:budget /home/budget/.ssh
chmod 700 /home/budget/.ssh
chmod 600 /home/budget/.ssh/authorized_keys

# Switch to new user
su - budget
```

---

## 🛡️ Security Configuration

### Step 1: Configure Firewall

```bash
# Enable UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Step 2: Configure SSH Security

```bash
# Edit SSH configuration
sudo nano /etc/ssh/sshd_config
```

**Find and modify these lines:**
```
Port 22                    # You can change to different port (e.g., 2222)
PermitRootLogin no         # Disable root login
PasswordAuthentication no  # Only SSH keys (if you set up keys)
```

**Restart SSH service:**
```bash
sudo systemctl restart ssh
```

### Step 3: Configure Fail2Ban

```bash
# Start and enable fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Create custom configuration
sudo tee /etc/fail2ban/jail.local > /dev/null <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

sudo systemctl restart fail2ban
```

---

## 🚀 Budget Bot Installation

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Step 2: Install Docker Compose

```bash
# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create symlink
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Verify installation
docker-compose --version
```

### Step 3: Create Directory Structure

```bash
# Create application directory
sudo mkdir -p /opt/budget-bot/{data/postgres,backups,logs}
sudo chown -R budget:budget /opt/budget-bot
cd /opt/budget-bot
```

### Step 4: Download Application Files

```bash
# Download Docker Compose configuration
wget https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/docker-compose.prod.yml

# Download Dockerfile
wget https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/Dockerfile

# Create backup script directory
mkdir -p scripts
wget -O scripts/backup-postgres.sh https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/scripts/backup-postgres.sh
chmod +x scripts/backup-postgres.sh
```

### Step 5: Log Out and Back In

```bash
# Log out to apply docker group membership
exit
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot
```

---

## ⚙️ Configuration

### Step 1: Get Required Tokens

**Telegram Bot Token:**
1. Open Telegram and message @BotFather
2. Send `/newbot`
3. Give your bot a name and username
4. Copy the token (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

**OpenAI API Key:**
1. Go to https://platform.openai.com
2. Create account or sign in
3. Navigate to API Keys section
4. Create new secret key
5. Copy the key (starts with `sk-`)

### Step 2: Create Environment File

```bash
# Create environment configuration
nano .env
```

**Paste this content (replace with your actual values):**
```env
# Telegram Bot Configuration
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
OPENAI_API_KEY=sk-your-openai-api-key-here

# Database Configuration
POSTGRES_DB=budget_bot
POSTGRES_USER=budget_user
POSTGRES_PASSWORD=SecurePassword123!

# Application Settings
SECRET_KEY=YourVeryLongSecretKey789!
TIMEZONE=Europe/Lisbon

# Backup Configuration
BACKUP_RETENTION_DAYS=7
```

**Save and exit:**
- Press `Ctrl + X`
- Press `Y`
- Press `Enter`

### Step 3: Create Simple Docker Compose File

Create a simplified version without complex monitoring:

```bash
# Create simplified docker-compose file
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./scripts/backup-postgres.sh:/backup.sh:ro
    restart: unless-stopped
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3

  budget-bot:
    build: .
    environment:
      BOT_TOKEN: ${BOT_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      TZ: ${TIMEZONE:-Europe/Lisbon}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s

volumes:
  postgres_data:
    driver: local
EOF
```

---

## 🚀 Launch and Testing

### Step 1: Start Budget Bot

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

**Expected output:**
```
NAME                    COMMAND                  SERVICE             STATUS
budget-bot-postgres-1   "docker-entrypoint.s…"   postgres            running
budget-bot-budget-bot-1 "python bot.py"          budget-bot          running
```

### Step 2: Check Logs

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs -f

# View only bot logs
docker-compose -f docker-compose.prod.yml logs -f budget-bot

# View only database logs
docker-compose -f docker-compose.prod.yml logs -f postgres
```

### Step 3: Test Your Bot

1. **Find your bot in Telegram**
   - Search for your bot's username
   - Send `/start`

2. **Test basic functionality**
   - Send: `25 EUR groceries`
   - Bot should respond with category selection

3. **Verify database connection**
   ```bash
   # Connect to database
   docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot
   
   # List tables
   \dt
   
   # Exit
   \q
   ```

### Step 4: Enable Auto-Start

```bash
# Create systemd service
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

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable budget-bot
sudo systemctl start budget-bot
```

---

## 🔧 Maintenance

### Daily Operations

**Check Status:**
```bash
# Service status
sudo systemctl status budget-bot

# Container status
docker-compose -f /opt/budget-bot/docker-compose.prod.yml ps

# View recent logs
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs --tail=50 budget-bot
```

**Restart Services:**
```bash
# Restart bot only
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart budget-bot

# Restart all services
sudo systemctl restart budget-bot
```

### Database Management

**Manual Backup:**
```bash
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml exec postgres /backup.sh
```

**View Backups:**
```bash
ls -la /opt/budget-bot/backups/
```

**Connect to Database:**
```bash
docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot
```

**Useful SQL Commands:**
```sql
-- List all tables
\dt

-- Count users
SELECT COUNT(*) FROM users;

-- Count transactions
SELECT COUNT(*) FROM transactions;

-- Database size
SELECT pg_size_pretty(pg_database_size('budget_bot'));

-- Exit
\q
```

### Updates

**Update Budget Bot:**
```bash
cd /opt/budget-bot

# Pull latest changes
docker-compose -f docker-compose.prod.yml pull

# Restart with new version
docker-compose -f docker-compose.prod.yml up -d

# Clean old images
docker image prune -f
```

**System Updates:**
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Reboot if kernel updated
sudo reboot
```

### Automatic Backups

**Setup Daily Backups:**
```bash
# Add to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * cd /opt/budget-bot && docker-compose -f docker-compose.prod.yml exec -T postgres /backup.sh") | crontab -

# Verify crontab
crontab -l
```

### Troubleshooting

**Bot Not Responding:**
```bash
# Check logs
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs budget-bot

# Restart bot
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart budget-bot
```

**Database Issues:**
```bash
# Check database logs
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs postgres

# Check disk space
df -h

# Restart database
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart postgres
```

**High Resource Usage:**
```bash
# Check system resources
htop

# Check container resources
docker stats

# Clean up Docker
docker system prune -f
```

**Out of Disk Space:**
```bash
# Clean old backups (older than 30 days)
find /opt/budget-bot/backups/ -name "*.sql.gz" -mtime +30 -delete

# Clean Docker
docker system prune -a -f

# Clean logs
sudo journalctl --vacuum-time=7d
```

---

## ✅ Success Checklist

- [ ] DigitalOcean droplet created
- [ ] SSH access configured
- [ ] Firewall and security setup
- [ ] Docker and Docker Compose installed
- [ ] Budget Bot files downloaded
- [ ] Environment variables configured
- [ ] Bot token and OpenAI API key added
- [ ] Services started successfully
- [ ] Bot responds in Telegram
- [ ] Database connection working
- [ ] Auto-start enabled
- [ ] Backups configured

---

## 🎯 Final Notes

**Your Budget Bot is now running on:**
- **IP Address:** `YOUR_VPS_IP`
- **SSH Access:** `ssh budget@YOUR_VPS_IP`
- **Bot Status:** `sudo systemctl status budget-bot`
- **Logs:** `docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs -f`

**Monthly Costs:**
- **DigitalOcean Droplet:** ~$6/month
- **Total:** ~$6/month

**Important Commands to Remember:**
```bash
# Check status
sudo systemctl status budget-bot

# View logs  
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs -f budget-bot

# Restart
sudo systemctl restart budget-bot

# Update
cd /opt/budget-bot && docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d
```

🎉 **Congratulations! Your Budget Bot is successfully deployed and running on VPS!**