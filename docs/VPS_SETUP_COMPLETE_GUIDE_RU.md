# 🖥️ Полная инструкция по настройке VPS для Budget Bot

## 📋 Оглавление
1. [Выбор и покупка VPS](#выбор-и-покупка-vps)
2. [Первое подключение](#первое-подключение)
3. [Базовая настройка безопасности](#базовая-настройка-безопасности)
4. [Автоматическая установка Budget Bot](#автоматическая-установка-budget-bot)
5. [Настройка конфигурации](#настройка-конфигурации)
6. [Запуск и проверка](#запуск-и-проверка)
7. [Обслуживание и мониторинг](#обслуживание-и-мониторинг)

---

## 🌐 Выбор и покупка VPS

### Рекомендуемые провайдеры

**🔥 Лучшие варианты:**

1. **DigitalOcean** (простой и надежный)
   - Сайт: https://www.digitalocean.com
   - Минимум: $5/месяц (1GB RAM, 25GB SSD)
   - Плюсы: простой интерфейс, хорошая документация
   - Минусы: дороже некоторых конкурентов

2. **Vultr** (хорошее соотношение цена/качество)
   - Сайт: https://www.vultr.com
   - Минимум: $3.50/месяц (512MB RAM, 10GB SSD)
   - Плюсы: дешево, много локаций
   - Минусы: интерфейс менее дружелюбный

3. **Linode** (для опытных пользователей)
   - Сайт: https://www.linode.com
   - Минимум: $5/месяц (1GB RAM, 25GB SSD)
   - Плюсы: отличная производительность
   - Минусы: более сложный для новичков

4. **Hetzner** (европейский, дешевый)
   - Сайт: https://www.hetzner.com
   - Минимум: €3.29/месяц (1GB RAM, 20GB SSD)
   - Плюсы: очень дешево, GDPR совместимый
   - Минусы: только европейские сервера

### Минимальные требования для Budget Bot

**Рекомендуемая конфигурация:**
- **RAM**: 1GB (минимум 512MB)
- **CPU**: 1 vCPU
- **Диск**: 20GB SSD
- **Трафик**: 1TB/месяц
- **ОС**: Ubuntu 20.04/22.04 LTS (рекомендуется)

### Пошаговая покупка (на примере DigitalOcean)

1. **Регистрация**
   - Перейдите на https://www.digitalocean.com
   - Нажмите "Sign Up"
   - Зарегистрируйтесь через email или GitHub

2. **Создание Droplet**
   - Нажмите "Create" → "Droplets"
   - Выберите образ: **Ubuntu 22.04 (LTS) x64**
   - Выберите план: **Basic** ($5/месяц)
   - Выберите регион ближе к вам
   - Добавьте SSH ключ (рекомендуется) или используйте пароль

3. **SSH ключ (рекомендуется)**
   ```bash
   # На вашем компьютере создайте SSH ключ
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   
   # Скопируйте публичный ключ
   cat ~/.ssh/id_rsa.pub
   ```
   - Вставьте содержимое в поле SSH Key

4. **Завершение**
   - Дайте серверу имя (например "budget-bot-server")
   - Нажмите "Create Droplet"
   - Через 1-2 минуты получите IP адрес

---

## 🔐 Первое подключение

### Получение IP адреса

После создания VPS вы получите:
- **IP адрес** (например: 203.0.113.15)
- **Пароль root** (если не использовали SSH ключ)

### Подключение к серверу

**Если используете SSH ключ:**
```bash
ssh root@YOUR_VPS_IP
```

**Если используете пароль:**
```bash
ssh root@YOUR_VPS_IP
# Введите пароль, который был отправлен на email
```

**На Windows:**
- Используйте PuTTY или Windows Terminal
- Или установите WSL и используйте команды выше

### Первичная настройка

После подключения выполните:

```bash
# Обновление системы
apt update && apt upgrade -y

# Создание пользователя (замените 'username' на ваше имя)
adduser budget
usermod -aG sudo budget

# Копирование SSH ключа для нового пользователя
mkdir -p /home/budget/.ssh
cp ~/.ssh/authorized_keys /home/budget/.ssh/
chown -R budget:budget /home/budget/.ssh
chmod 700 /home/budget/.ssh
chmod 600 /home/budget/.ssh/authorized_keys

# Переключение на нового пользователя
su - budget
```

---

## 🛡️ Базовая настройка безопасности

### Настройка SSH

```bash
# Редактирование конфигурации SSH
sudo nano /etc/ssh/sshd_config
```

**Найдите и измените эти строки:**
```
Port 22                    # Можете изменить на другой порт (например 2222)
PermitRootLogin no         # Запретить вход root
PasswordAuthentication no  # Только SSH ключи (если настроили)
```

```bash
# Перезапуск SSH сервиса
sudo systemctl restart ssh
```

### Настройка файрвола

```bash
# Установка и настройка UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Установка fail2ban

```bash
# Установка fail2ban для защиты от атак
sudo apt install fail2ban -y
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

---

## 🚀 Автоматическая установка Budget Bot

### Метод 1: Через скрипт (рекомендуется)

```bash
# Скачивание и запуск скрипта автоматической установки
curl -fsSL https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/scripts/universal-vps-setup.sh | bash
```

**Что делает скрипт:**
- ✅ Автоматически определяет вашу ОС
- ✅ Устанавливает Docker и Docker Compose
- ✅ Настраивает файрвол и безопасность
- ✅ Создает пользователя и директории
- ✅ Настраивает мониторинг
- ✅ Создает автоматические бэкапы
- ✅ Настраивает автозапуск

### Метод 2: Ручная установка

Если скрипт не работает, выполните команды вручную:

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Создание директорий
sudo mkdir -p /opt/budget-bot/{data/{postgres,redis,grafana,prometheus},backups,logs}
sudo chown -R $USER:$USER /opt/budget-bot

# Выход и повторный вход для применения группы docker
exit
ssh budget@YOUR_VPS_IP
```

---

## ⚙️ Настройка конфигурации

### Загрузка файлов проекта

```bash
# Переход в рабочую директорию
cd /opt/budget-bot

# Скачивание конфигурационных файлов
wget https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/docker-compose.prod.yml
wget https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/Dockerfile

# Создание папки для скриптов
mkdir -p scripts
cd scripts
wget https://raw.githubusercontent.com/pkovarsky/budget_bot_claude/master/scripts/backup-postgres.sh
chmod +x backup-postgres.sh
cd ..
```

### Создание файла конфигурации

```bash
# Создание файла с переменными окружения
nano .env
```

**Содержимое файла .env:**
```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
POSTGRES_DB=budget_bot
POSTGRES_USER=budget_user
POSTGRES_PASSWORD=SuperSecurePassword123!

# Redis Configuration
REDIS_PASSWORD=AnotherSecurePassword456!

# Security
SECRET_KEY=YourVeryLongSecretKey789!

# Monitoring
GRAFANA_ADMIN_PASSWORD=GrafanaPassword!

# Backup Configuration
BACKUP_RETENTION_DAYS=7
BACKUP_WEBHOOK_URL=https://hooks.slack.com/your/webhook/url
```

### Получение токенов

**1. Telegram Bot Token:**
1. Напишите @BotFather в Telegram
2. Отправьте `/newbot`
3. Дайте боту имя и username
4. Сохраните полученный токен

**2. OpenAI API Key:**
1. Зайдите на https://platform.openai.com
2. Создайте аккаунт или войдите
3. Перейдите в API Keys
4. Создайте новый ключ
5. Сохраните ключ (он показывается только один раз!)

---

## 🚀 Запуск и проверка

### Запуск Budget Bot

```bash
# Переход в директорию проекта
cd /opt/budget-bot

# Запуск всех сервисов
docker-compose -f docker-compose.prod.yml up -d

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps
```

**Ожидаемый вывод:**
```
      Name                     Command               State                    Ports
------------------------------------------------------------------------------------------------
budget-bot_budget-bot_1    python bot.py                Up      
budget-bot_postgres_1      docker-entrypoint.sh postgres   Up      5432/tcp
budget-bot_redis_1         docker-entrypoint.sh redis ... Up      6379/tcp
budget-bot_grafana_1       /run.sh                      Up      0.0.0.0:3000->3000/tcp
```

### Проверка логов

```bash
# Просмотр логов всех сервисов
docker-compose -f docker-compose.prod.yml logs -f

# Просмотр логов только бота
docker-compose -f docker-compose.prod.yml logs -f budget-bot

# Просмотр логов базы данных
docker-compose -f docker-compose.prod.yml logs -f postgres
```

### Тестирование бота

1. Найдите вашего бота в Telegram по username
2. Отправьте `/start`
3. Попробуйте добавить транзакцию: `25 EUR продукты`

### Настройка автозапуска

```bash
# Создание systemd сервиса
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

# Включение автозапуска
sudo systemctl daemon-reload
sudo systemctl enable budget-bot
sudo systemctl start budget-bot
```

---

## 📊 Обслуживание и мониторинг

### Полезные команды

```bash
# Статус сервисов
docker-compose -f /opt/budget-bot/docker-compose.prod.yml ps

# Просмотр логов
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs -f budget-bot

# Перезапуск бота
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart budget-bot

# Обновление бота
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Подключение к базе данных
docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot
```

### Мониторинг Grafana

1. Откройте в браузере: `http://YOUR_VPS_IP:3000`
2. Войдите: admin / пароль из .env файла
3. Настройте дашборды для мониторинга

### Автоматические бэкапы

Бэкапы создаются автоматически каждый день в 2:00
```bash
# Ручное создание бэкапа
docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec postgres /backup.sh

# Просмотр бэкапов
ls -la /opt/budget-bot/backups/

# Восстановление из бэкапа
gunzip -c /opt/budget-bot/backups/budget_bot_backup_20241215.sql.gz | \
docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot
```

---

## 🔧 Troubleshooting

### Проблема: Бот не отвечает

```bash
# Проверка статуса
docker-compose -f /opt/budget-bot/docker-compose.prod.yml ps

# Проверка логов
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs budget-bot

# Перезапуск бота
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart budget-bot
```

### Проблема: База данных не работает

```bash
# Проверка логов PostgreSQL
docker-compose -f /opt/budget-bot/docker-compose.prod.yml logs postgres

# Проверка свободного места
df -h

# Перезапуск базы данных
docker-compose -f /opt/budget-bot/docker-compose.prod.yml restart postgres
```

### Проблема: Нет места на диске

```bash
# Проверка использования диска
df -h

# Очистка старых Docker образов
docker system prune -a

# Очистка старых бэкапов
find /opt/budget-bot/backups/ -name "*.sql.gz" -mtime +30 -delete
```

### Проблема: Высокая нагрузка

```bash
# Проверка использования ресурсов
htop

# Проверка использования Docker контейнерами
docker stats

# Просмотр активных процессов
ps aux | head -10
```

---

## 📚 Дополнительные ресурсы

### Полезные ссылки
- [Docker документация](https://docs.docker.com/)
- [Docker Compose документация](https://docs.docker.com/compose/)
- [PostgreSQL документация](https://www.postgresql.org/docs/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

### Файлы конфигурации
- `docker-compose.prod.yml` - Конфигурация Docker Compose
- `.env` - Переменные окружения
- `Dockerfile` - Описание Docker образа

---

## ✅ Checklist успешной установки

- [ ] VPS куплен и настроен
- [ ] SSH ключи настроены
- [ ] Файрвол настроен
- [ ] Docker и Docker Compose установлены
- [ ] Файлы проекта загружены
- [ ] Файл .env настроен с правильными токенами
- [ ] Бот запущен и отвечает в Telegram
- [ ] Автозапуск настроен
- [ ] Мониторинг работает
- [ ] Бэкапы настроены

🎉 **Поздравляем! Ваш Budget Bot успешно развернут на VPS!**