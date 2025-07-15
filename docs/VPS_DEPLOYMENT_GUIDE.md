# 🖥️ VPS Deployment Guide - Пошаговая инструкция

## 📋 Обзор

Полное руководство по настройке автоматического деплоя Budget Bot на VPS через GitHub Actions с persistent volumes для базы данных.

## 🎯 Что получим в итоге

- ✅ **Автоматический деплой** при каждом push в main
- ✅ **Persistent база данных** с backup'ами
- ✅ **Мониторинг** через Grafana/Prometheus
- ✅ **SSL сертификаты** и nginx reverse proxy
- ✅ **Автоматические обновления** и rollback
- ✅ **Безопасность** с firewall и fail2ban

---

## 📚 ЧАСТЬ 1: Подготовка VPS

### 1.1 Выбор VPS провайдера

**Рекомендуемые:**
- **DigitalOcean** - $6/мес (1GB RAM, 25GB SSD)
- **Vultr** - $6/мес (1GB RAM, 25GB SSD)
- **Linode** - $5/мес (1GB RAM, 25GB SSD)
- **Hetzner** - €4.5/мес (4GB RAM, 40GB SSD) - лучшая цена

**Минимальные требования:**
- 1GB RAM
- 20GB SSD
- Ubuntu 20.04/22.04 LTS

### 1.2 Создание VPS

1. **Создайте сервер** с Ubuntu 22.04 LTS
2. **Запомните IP адрес** сервера
3. **Добавьте SSH ключ** или используйте пароль

### 1.3 Первоначальная настройка

```bash
# Подключитесь к серверу
ssh root@YOUR_VPS_IP

# Создайте пользователя (не используйте root!)
adduser budget
usermod -aG sudo budget

# Переключитесь на нового пользователя
su - budget
```

### 1.4 Автоматическая настройка VPS

```bash
# Скачайте и запустите скрипт настройки
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/budget_bot_claude/main/scripts/vps-setup.sh -o vps-setup.sh
chmod +x vps-setup.sh
./vps-setup.sh
```

**Что делает скрипт:**
- ✅ Устанавливает Docker и Docker Compose
- ✅ Создает структуру директорий
- ✅ Настраивает firewall (UFW)
- ✅ Устанавливает fail2ban
- ✅ Создает nginx конфигурацию
- ✅ Настраивает мониторинг
- ✅ Создает backup скрипты
- ✅ Настраивает cron задачи
- ✅ Генерирует SSH ключи

---

## 📚 ЧАСТЬ 2: Настройка GitHub Repository

### 2.1 Подготовка репозитория

```bash
# Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/budget_bot_claude.git
cd budget_bot_claude

# Убедитесь что все файлы на месте
ls -la docker-compose.prod.yml
ls -la .github/workflows/vps-deploy.yml
ls -la scripts/vps-setup.sh
```

### 2.2 Настройка GitHub Secrets

Перейдите в **GitHub → Settings → Secrets and variables → Actions**

**Обязательные secrets:**

```bash
# 🖥️ VPS Connection
VPS_HOST=YOUR_VPS_IP_ADDRESS
VPS_USER=budget
VPS_SSH_KEY=<содержимое файла ~/.ssh/id_rsa с VPS>

# 🤖 Bot Configuration  
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key

# 🔐 Database Passwords
POSTGRES_PASSWORD=super_secure_postgres_password_123
REDIS_PASSWORD=super_secure_redis_password_123
GRAFANA_PASSWORD=super_secure_grafana_password_123

# 🔔 Notifications (опционально)
WEBHOOK_URL=https://discord.com/api/webhooks/... # для уведомлений
```

**Как получить VPS_SSH_KEY:**

```bash
# На VPS выполните:
cat ~/.ssh/id_rsa

# Скопируйте ВЕСЬ вывод (включая -----BEGIN/END-----)
```

### 2.3 Настройка Environment Variables

В **GitHub → Settings → Environments** создайте environment **production**:

```bash
# Variables
TZ=Europe/Amsterdam
APP_URL=http://YOUR_VPS_IP
```

---

## 📚 ЧАСТЬ 3: Настройка домена и SSL (опционально)

### 3.1 Настройка домена

Если у вас есть домен:

```bash
# DNS записи (в вашем DNS провайдере)
A record: @ → YOUR_VPS_IP
A record: www → YOUR_VPS_IP
```

### 3.2 SSL сертификат

```bash
# На VPS выполните:
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Обновите nginx конфигурацию для HTTPS
sudo nano /opt/budget-bot/nginx/nginx.conf
```

**Nginx конфигурация с SSL:**

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://budget-bot:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📚 ЧАСТЬ 4: Первый деплой

### 4.1 Проверка настроек

```bash
# Проверьте что все secrets добавлены
# GitHub → Settings → Secrets → Actions

# Проверьте VPS
ssh budget@YOUR_VPS_IP "docker --version && docker-compose --version"
```

### 4.2 Запуск деплоя

```bash
# Создайте коммит и запушьте
git add .
git commit -m "Setup VPS deployment"
git push origin main

# Или запустите деплой вручную
# GitHub → Actions → Deploy to VPS → Run workflow
```

### 4.3 Мониторинг деплоя

1. **Перейдите в GitHub Actions**
2. **Откройте workflow "Deploy to VPS"**
3. **Следите за процессом:**
   - ✅ Tests
   - ✅ Build & Push Image
   - ✅ Deploy to VPS
   - ✅ Verify deployment

---

## 📚 ЧАСТЬ 5: Доступ к базе данных и volumes

### 5.1 Структура данных на VPS

```bash
/opt/budget-bot/
├── data/
│   ├── postgres/          # 🗄️ База данных PostgreSQL
│   ├── redis/             # 🟥 Redis кеш
│   ├── grafana/           # 📊 Grafana настройки
│   ├── prometheus/        # 📈 Prometheus метрики
│   ├── exports/           # 📤 Excel экспорты
│   └── charts/            # 📊 Сгенерированные графики
├── logs/                  # 📝 Логи приложений
├── backups/               # 💾 Backup'ы базы данных
└── docker-compose.prod.yml
```

### 5.2 Подключение к базе данных

**Через Docker:**
```bash
# Подключение к контейнеру PostgreSQL
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot

# Просмотр таблиц
\dt

# Выход
\q
```

**Через psql клиент:**
```bash
# На VPS откройте порт 5432 временно
sudo ufw allow 5432/tcp

# С локального компьютера
psql -h YOUR_VPS_IP -U budget_user -d budget_bot
```

### 5.3 Backup и восстановление

**Создание backup'а:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Ручной backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U budget_user budget_bot > backup_$(date +%Y%m%d).sql

# Автоматический backup (через cron)
./scripts/maintenance.sh
```

**Восстановление:**
```bash
# Копирование backup'а на VPS
scp backup_20241215.sql budget@YOUR_VPS_IP:/opt/budget-bot/backups/

# Восстановление
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot < backups/backup_20241215.sql
```

### 5.4 Доступ к volume'ам

**Копирование данных с VPS:**
```bash
# Скачать всю базу данных
scp -r budget@YOUR_VPS_IP:/opt/budget-bot/data/postgres/ ./local_backup/

# Скачать backup'ы
scp budget@YOUR_VPS_IP:/opt/budget-bot/backups/*.sql.gz ./backups/

# Скачать экспорты Excel
scp budget@YOUR_VPS_IP:/opt/budget-bot/data/exports/*.xlsx ./exports/
```

**Мониторинг размера:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Размер всех volume'ов
sudo du -sh data/*

# Мониторинг места на диске
df -h

# Список backup'ов
ls -lah backups/
```

---

## 📚 ЧАСТЬ 6: Мониторинг и управление

### 6.1 Доступ к мониторингу

**Grafana Dashboard:**
```bash
# Откройте в браузере
http://YOUR_VPS_IP:3000

# Логин: admin
# Пароль: ваш GRAFANA_PASSWORD
```

**Prometheus Metrics:**
```bash
http://YOUR_VPS_IP:9090
```

### 6.2 Управление сервисами

**Основные команды:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Статус сервисов
docker-compose -f docker-compose.prod.yml ps

# Логи
docker-compose -f docker-compose.prod.yml logs -f budget-bot

# Перезапуск
docker-compose -f docker-compose.prod.yml restart budget-bot

# Остановка
docker-compose -f docker-compose.prod.yml down

# Запуск с мониторингом
docker-compose -f docker-compose.prod.yml --profile monitoring up -d
```

### 6.3 Обновления

**Автоматические обновления:**
- При каждом push в main запускается деплой
- Watchtower автоматически обновляет контейнеры

**Ручное обновление:**
```bash
# GitHub Actions → Deploy to VPS → Run workflow
```

---

## 📚 ЧАСТЬ 7: Troubleshooting

### 7.1 Частые проблемы

**Деплой не запускается:**
```bash
# Проверьте secrets в GitHub
# Проверьте SSH доступ
ssh budget@YOUR_VPS_IP "echo 'SSH works'"
```

**Контейнеры не запускаются:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml logs

# Проверка места на диске
df -h
```

**База данных недоступна:**
```bash
# Проверка контейнера PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U budget_user

# Проверка volume'а
sudo ls -la /opt/budget-bot/data/postgres/
```

### 7.2 Восстановление после сбоя

**Полное восстановление:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Остановка всех сервисов
docker-compose -f docker-compose.prod.yml down

# Очистка и перезапуск
docker system prune -f
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

**Rollback к предыдущей версии:**
```bash
# Запустится автоматически если деплой упал
# Или вручную через GitHub Actions
```

---

## 📚 ЧАСТЬ 8: Безопасность и оптимизация

### 8.1 Безопасность

**Регулярные обновления:**
```bash
# Автоматические обновления Ubuntu
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

**Мониторинг логов:**
```bash
# Мониторинг попыток входа
sudo tail -f /var/log/auth.log

# Статистика fail2ban
sudo fail2ban-client status sshd
```

### 8.2 Оптимизация производительности

**Настройка PostgreSQL:**
```bash
# Увеличение shared_buffers для лучшей производительности
# В docker-compose.prod.yml добавьте:
environment:
  - POSTGRES_INITDB_ARGS=--auth-host=md5
command: postgres -c shared_buffers=256MB -c max_connections=200
```

**Мониторинг ресурсов:**
```bash
# Использование CPU/RAM
htop

# Статистика Docker
docker stats

# Размер логов
sudo du -sh /var/lib/docker/containers/*/*-json.log
```

---

## 🎯 Заключение

После выполнения всех шагов у вас будет:

✅ **Полностью автоматизированный деплой** через GitHub Actions  
✅ **Persistent база данных** с автоматическими backup'ами  
✅ **Мониторинг** через Grafana и Prometheus  
✅ **Безопасность** с firewall и fail2ban  
✅ **SSL сертификаты** для HTTPS  
✅ **Автоматические обновления** и rollback  

**Следующие шаги:**
1. Настройте домен и SSL сертификат
2. Включите мониторинг профиль: `--profile monitoring`
3. Настройте уведомления в Discord/Slack
4. Добавьте дополнительные backup'ы в облако

**Полезные ссылки:**
- Grafana: `http://YOUR_VPS_IP:3000`
- Prometheus: `http://YOUR_VPS_IP:9090`
- GitHub Actions: Repository → Actions
- VPS мониторинг: `ssh budget@YOUR_VPS_IP htop`

🚀 **Ваш Budget Bot готов к работе в продакшене!**