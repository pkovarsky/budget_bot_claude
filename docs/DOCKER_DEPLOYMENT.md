# 🐳 Docker Deployment Guide

## 📋 Обзор

Budget Bot полностью поддерживает Docker для удобного развертывания и масштабирования.

## 🚀 Быстрый старт

### 1. Настройка переменных окружения
```bash
cp .env.example .env
# Отредактируйте .env файл со своими токенами
```

### 2. Запуск в production
```bash
# Простой запуск
docker-compose up -d

# Или используйте удобный скрипт
./scripts/docker-commands.sh run
```

### 3. Проверка работы
```bash
./scripts/docker-commands.sh health
./scripts/docker-commands.sh logs
```

## 🛠️ Конфигурации

### Production (docker-compose.yml)
- **Budget Bot** - основное приложение
- **PostgreSQL** - база данных (опционально)
- **Redis** - кеширование (опционально)
- **Grafana + Prometheus** - мониторинг (profile: monitoring)
- **Nginx** - reverse proxy (profile: proxy)

### Development (docker-compose.dev.yml)
- **Hot reload** - изменения кода сразу применяются
- **Debug режим** - с pdb поддержкой
- **Test runner** - автоматические тесты
- **MailHog** - тестирование email уведомлений

## 📦 Dockerfile

### Multi-stage сборка
- **Base stage** - установка зависимостей
- **Production stage** - оптимизированный runtime

### Особенности
- **Non-root пользователь** для безопасности
- **Health checks** для мониторинга
- **Persistent volumes** для данных
- **Кэширование** для быстрой сборки

## 🔧 Управление через скрипт

### Основные команды
```bash
# Сборка
./scripts/docker-commands.sh build
./scripts/docker-commands.sh build_dev

# Запуск
./scripts/docker-commands.sh run                    # Production
./scripts/docker-commands.sh run_dev               # Development  
./scripts/docker-commands.sh run_with_monitoring   # С мониторингом

# Управление
./scripts/docker-commands.sh stop
./scripts/docker-commands.sh restart
./scripts/docker-commands.sh status
```

### Мониторинг
```bash
./scripts/docker-commands.sh logs      # Логи
./scripts/docker-commands.sh health    # Проверка здоровья
./scripts/docker-commands.sh stats     # Ресурсы
```

### Тестирование
```bash
./scripts/docker-commands.sh test         # Все тесты
./scripts/docker-commands.sh test_memory  # Система памяти
```

### База данных
```bash
./scripts/docker-commands.sh migrate                # Миграции
./scripts/docker-commands.sh backup_db              # Бэкап
./scripts/docker-commands.sh restore_db backup.db   # Восстановление
```

### Отладка
```bash
./scripts/docker-commands.sh shell    # Shell в контейнере
./scripts/docker-commands.sh debug    # Debug режим
```

## 🌍 GitHub Actions

### Workflows
1. **test.yml** - Тестирование на multiple OS/Python versions
2. **deploy.yml** - Автоматический деплой с тестами и security scan

### Функции
- ✅ **Multi-platform тесты** (Ubuntu, Windows, macOS)
- ✅ **Multi-version Python** (3.9, 3.10, 3.11, 3.12)
- ✅ **Security scanning** с Trivy
- ✅ **Code quality** checks (Black, flake8, mypy)
- ✅ **Integration тесты** с PostgreSQL
- ✅ **Docker build и push** в GitHub Container Registry
- ✅ **Automatic deployment** в Railway/другие платформы

### Настройка secrets
```bash
# В GitHub repository settings > Secrets:
TELEGRAM_BOT_TOKEN=your_token
OPENAI_API_KEY=your_key
RAILWAY_TOKEN=your_railway_token  # опционально
DEPLOY_HOST=your_server           # опционально
```

## 🚀 Деплой на различные платформы

### Railway (рекомендуется)
```bash
# Автоматический деплой через GitHub Actions
git push origin main

# Или вручную
railway login
railway deploy
```

### Digital Ocean / AWS / GCP
```bash
# Деплой Docker Compose
scp docker-compose.yml user@server:/app/
ssh user@server "cd /app && docker-compose up -d"

# Или используйте GitHub Actions с DEPLOY_HOST
```

### Heroku
```bash
# Используйте heroku.yml (создайте файл):
echo "build:
  docker:
    worker: Dockerfile" > heroku.yml

git add heroku.yml
git commit -m "Add Heroku config"
git push heroku main
```

## 📊 Мониторинг

### Grafana Dashboard
```bash
# Запуск с мониторингом
./scripts/docker-commands.sh run_with_monitoring

# Доступ: http://localhost:3000
# Логин: admin / пароль из .env
```

### Prometheus Метрики
- Доступ: http://localhost:9090
- Метрики контейнеров
- Health checks
- Custom application metrics

### Логирование
```bash
# Все логи
docker-compose logs -f

# Только Budget Bot
docker-compose logs -f budget-bot

# С ротацией
docker-compose logs --tail=100 -f budget-bot
```

## 🔒 Безопасность

### Best Practices
- ✅ **Non-root контейнер** - запуск под appuser
- ✅ **Secrets в .env** - не в Dockerfile
- ✅ **Multi-stage сборка** - минимальный размер
- ✅ **Health checks** - автоматическая проверка
- ✅ **Security scanning** - Trivy в CI/CD
- ✅ **Read-only filesystem** - где возможно

### Обновления
```bash
# Автоматические обновления через GitHub Actions
git push origin main

# Ручные обновления
./scripts/docker-commands.sh deploy
```

## 🔧 Troubleshooting

### Частые проблемы

**Контейнер не запускается:**
```bash
./scripts/docker-commands.sh logs
./scripts/docker-commands.sh health
```

**База данных не доступна:**
```bash
# Проверить volume
docker volume ls | grep budget
docker volume inspect budget_bot_data

# Пересоздать
./scripts/docker-commands.sh clean
./scripts/docker-commands.sh run
```

**Нет места на диске:**
```bash
# Очистка
./scripts/docker-commands.sh clean
docker system prune -a -f
```

**Проблемы с памятью:**
```bash
# Ограничить ресурсы в docker-compose.yml
services:
  budget-bot:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

## 📈 Масштабирование

### Горизонтальное масштабирование
```yaml
# В docker-compose.yml
services:
  budget-bot:
    deploy:
      replicas: 3
    
  nginx:
    # Load balancer config
```

### Вертикальное масштабирование
```yaml
services:
  budget-bot:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

## 🎯 Рекомендации

### Для production
1. Используйте PostgreSQL вместо SQLite
2. Настройте reverse proxy (Nginx)
3. Включите мониторинг
4. Настройте автоматические бэкапы
5. Используйте Docker Swarm или Kubernetes для масштабирования

### Для development
1. Используйте docker-compose.dev.yml
2. Монтируйте код для hot reload
3. Включите debug режим
4. Используйте MailHog для тестирования

### Performance tuning
1. Оптимизируйте Docker образ
2. Используйте .dockerignore
3. Multi-stage builds
4. Кэширование слоев
5. Health checks для быстрого восстановления