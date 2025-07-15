# 🗄️ База данных и Volume Access Guide

## 📋 Обзор

Подробное руководство по доступу к базе данных, backup'ам и управлению persistent volumes на VPS.

## 🗂️ Структура данных

### Основные директории
```bash
/opt/budget-bot/
├── data/                          # 💾 Persistent данные
│   ├── postgres/                  # 🗄️ PostgreSQL база данных
│   │   ├── pgdata/               # Файлы базы данных
│   │   ├── pg_log/               # Логи PostgreSQL
│   │   └── pg_wal/               # Write-Ahead Logging
│   ├── redis/                     # 🟥 Redis cache
│   ├── grafana/                   # 📊 Grafana настройки и дашборды
│   ├── prometheus/                # 📈 Prometheus метрики
│   ├── exports/                   # 📤 Excel файлы экспортов
│   └── charts/                    # 📊 Сгенерированные графики
├── backups/                       # 💾 Автоматические backup'ы
├── logs/                          # 📝 Логи приложений
│   ├── nginx/                     # Nginx access/error логи
│   └── *.log                      # Логи Budget Bot
└── docker-compose.prod.yml       # Конфигурация
```

---

## 🔌 Подключение к базе данных

### Через Docker контейнер (рекомендуется)

```bash
# Подключение к VPS
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Подключение к PostgreSQL контейнеру
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot
```

**Полезные SQL команды:**
```sql
-- Список таблиц
\dt

-- Информация о таблице
\d users

-- Размер базы данных
SELECT pg_size_pretty(pg_database_size('budget_bot'));

-- Список активных подключений
SELECT * FROM pg_stat_activity;

-- Статистика по таблицам
SELECT schemaname,tablename,n_tup_ins,n_tup_upd,n_tup_del 
FROM pg_stat_user_tables;

-- Выход
\q
```

### Прямое подключение (для разработки)

```bash
# На VPS временно откройте порт
sudo ufw allow 5432/tcp

# С локального компьютера
psql -h YOUR_VPS_IP -p 5432 -U budget_user -d budget_bot

# Закройте порт после использования
sudo ufw delete allow 5432/tcp
```

### Через SSH туннель (безопасно)

```bash
# Создайте SSH туннель
ssh -L 5432:localhost:5432 budget@YOUR_VPS_IP

# В другом терминале подключайтесь как к локальной базе
psql -h localhost -p 5432 -U budget_user -d budget_bot
```

---

## 💾 Backup и восстановление

### Автоматические backup'ы

**Настройка cron (уже настроено):**
```bash
# Backup каждую ночь в 2:00
0 2 * * * cd /opt/budget-bot && docker-compose -f docker-compose.prod.yml exec -T postgres /backup.sh
```

**Ручной backup:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Запуск backup скрипта
docker-compose -f docker-compose.prod.yml exec postgres /backup.sh

# Или напрямую через pg_dump
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U budget_user budget_bot > backup_manual_$(date +%Y%m%d).sql
```

### Скачивание backup'ов

```bash
# Список всех backup'ов
ssh budget@YOUR_VPS_IP "ls -lah /opt/budget-bot/backups/"

# Скачать конкретный backup
scp budget@YOUR_VPS_IP:/opt/budget-bot/backups/budget_bot_backup_20241215_020001.sql.gz ./

# Скачать все backup'ы
scp budget@YOUR_VPS_IP:/opt/budget-bot/backups/*.sql.gz ./backups/

# Скачать весь каталог с данными (ОСТОРОЖНО - может быть большим!)
rsync -avz budget@YOUR_VPS_IP:/opt/budget-bot/data/ ./vps_data_backup/
```

### Восстановление из backup'а

**На том же VPS:**
```bash
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot

# Остановите приложение
docker-compose -f docker-compose.prod.yml stop budget-bot

# Создайте backup текущей базы
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U budget_user budget_bot > current_backup.sql

# Восстановите из backup'а
gunzip -c backups/budget_bot_backup_20241215_020001.sql.gz | \
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot

# Запустите приложение
docker-compose -f docker-compose.prod.yml start budget-bot
```

**На новом VPS:**
```bash
# Скопируйте backup на новый сервер
scp backup_file.sql.gz new_user@NEW_VPS_IP:/opt/budget-bot/backups/

# На новом VPS
ssh new_user@NEW_VPS_IP
cd /opt/budget-bot

# Запустите только базу данных
docker-compose -f docker-compose.prod.yml up -d postgres

# Дождитесь запуска PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgres

# Восстановите данные
gunzip -c backups/backup_file.sql.gz | \
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot

# Запустите все сервисы
docker-compose -f docker-compose.prod.yml up -d
```

---

## 📊 Управление данными

### Экспорт данных пользователей

```bash
# Подключитесь к базе
ssh budget@YOUR_VPS_IP
cd /opt/budget-bot
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot

-- Экспорт всех пользователей
\copy (SELECT * FROM users) TO '/tmp/users_export.csv' WITH CSV HEADER;

-- Экспорт транзакций конкретного пользователя
\copy (SELECT t.*, c.name as category_name FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.user_id = 123) TO '/tmp/user_123_transactions.csv' WITH CSV HEADER;

-- Экспорт статистики по категориям
\copy (SELECT c.name, COUNT(t.id) as transaction_count, SUM(ABS(t.amount)) as total_amount FROM categories c LEFT JOIN transactions t ON c.id = t.category_id GROUP BY c.name) TO '/tmp/category_stats.csv' WITH CSV HEADER;
```

### Очистка старых данных

```bash
# Подключитесь к базе
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot

-- Удаление транзакций старше года
DELETE FROM transactions WHERE created_at < NOW() - INTERVAL '1 year';

-- Очистка памяти системы для неактивных пользователей
DELETE FROM category_memory 
WHERE user_id IN (
    SELECT u.id FROM users u 
    LEFT JOIN transactions t ON u.id = t.user_id 
    WHERE t.created_at < NOW() - INTERVAL '6 months'
    OR t.id IS NULL
);

-- Вакуум для освобождения места
VACUUM ANALYZE;
```

### Мониторинг размера базы данных

```bash
# Общий размер базы данных
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    pg_size_pretty(pg_database_size('budget_bot')) as database_size,
    pg_size_pretty(pg_total_relation_size('transactions')) as transactions_size,
    pg_size_pretty(pg_total_relation_size('category_memory')) as memory_size;
"

# Статистика по таблицам
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

---

## 🔧 Администрирование

### Проверка целостности данных

```bash
# Проверка состояния базы данных
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched,
    tup_inserted,
    tup_updated,
    tup_deleted
FROM pg_stat_database 
WHERE datname = 'budget_bot';
"

# Проверка индексов
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
"
```

### Оптимизация производительности

```bash
# Анализ медленных запросов (если включено логирование)
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
"

# Перестройка индексов
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
REINDEX DATABASE budget_bot;
"

# Обновление статистики планировщика
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
ANALYZE;
"
```

### Управление подключениями

```bash
# Активные подключения
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    backend_start,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'budget_bot';
"

# Закрытие зависших подключений
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'budget_bot'
  AND state = 'idle'
  AND backend_start < NOW() - INTERVAL '1 hour';
"
```

---

## 📈 Мониторинг и алерты

### Настройка мониторинга размера базы данных

**Создайте скрипт мониторинга:**
```bash
# На VPS создайте файл
cat > /opt/budget-bot/scripts/monitor-db.sh << 'EOF'
#!/bin/bash

DB_SIZE=$(docker-compose -f /opt/budget-bot/docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot -t -c "SELECT pg_database_size('budget_bot');" | tr -d ' ')
DB_SIZE_MB=$((DB_SIZE / 1024 / 1024))

echo "Database size: ${DB_SIZE_MB}MB"

# Отправка алерта если база больше 1GB
if [ $DB_SIZE_MB -gt 1024 ]; then
    echo "⚠️ Database size exceeded 1GB: ${DB_SIZE_MB}MB"
    # Отправить уведомление
    curl -X POST -H "Content-Type: application/json" \
        -d "{\"text\":\"⚠️ Budget Bot database size: ${DB_SIZE_MB}MB\"}" \
        "$WEBHOOK_URL" 2>/dev/null || true
fi
EOF

chmod +x /opt/budget-bot/scripts/monitor-db.sh

# Добавьте в cron для ежедневной проверки
(crontab -l; echo "0 12 * * * /opt/budget-bot/scripts/monitor-db.sh") | crontab -
```

### Логирование доступа к базе данных

```bash
# Включите логирование подключений в PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
ALTER SYSTEM SET log_duration = on;
SELECT pg_reload_conf();
"

# Просмотр логов PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgres | grep -E "(connection|disconnection)"
```

---

## 🚨 Troubleshooting

### Частые проблемы с базой данных

**1. База данных не запускается:**
```bash
# Проверьте логи
docker-compose -f docker-compose.prod.yml logs postgres

# Проверьте права доступа к volume
sudo ls -la /opt/budget-bot/data/postgres/

# Пересоздайте контейнер
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d postgres
```

**2. Нет места на диске:**
```bash
# Проверьте использование диска
df -h

# Очистите старые backup'ы
find /opt/budget-bot/backups/ -name "*.sql.gz" -mtime +30 -delete

# Очистите Docker
docker system prune -f
```

**3. Медленные запросы:**
```bash
# Проверьте статистику
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "
SELECT * FROM pg_stat_user_tables WHERE n_tup_ins + n_tup_upd + n_tup_del > 1000;
"

# Перестройте индексы
docker-compose -f docker-compose.prod.yml exec postgres psql -U budget_user -d budget_bot -c "REINDEX DATABASE budget_bot;"
```

**4. Потеря данных:**
```bash
# Восстановите из последнего backup'а
cd /opt/budget-bot
ls -la backups/
gunzip -c backups/budget_bot_backup_LATEST.sql.gz | \
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U budget_user -d budget_bot
```

---

## 🎯 Best Practices

### Регулярное обслуживание

1. **Ежедневно:**
   - Автоматические backup'ы
   - Мониторинг размера базы данных
   - Проверка логов на ошибки

2. **Еженедельно:**
   - Очистка старых backup'ов
   - Обновление статистики планировщика
   - Проверка производительности

3. **Ежемесячно:**
   - Полная проверка целостности данных
   - Оптимизация индексов
   - Обзор и очистка старых данных

### Безопасность

1. **Доступ к базе данных:**
   - Используйте SSH туннели для внешнего доступа
   - Регулярно меняйте пароли
   - Ограничивайте доступ по IP

2. **Backup'ы:**
   - Храните backup'ы в нескольких местах
   - Регулярно тестируйте восстановление
   - Шифруйте backup'ы перед отправкой в облако

3. **Мониторинг:**
   - Настройте алерты на размер базы данных
   - Отслеживайте необычную активность
   - Логируйте все административные действия

🗄️ **Ваша база данных Budget Bot теперь под полным контролем!**