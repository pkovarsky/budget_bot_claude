# 🐳 Multi-stage Dockerfile for Budget Bot
FROM python:3.11-slim AS base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Production stage ----
FROM python:3.11-slim AS production

# Установка минимального окружения
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Рабочая директория
WORKDIR /app

# Копирование Python зависимостей и бинарников
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Копирование кода приложения
COPY . .

# Создание и настройка директорий
RUN mkdir -p /app/data && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /app /home/appuser && \
    chmod -R 755 /app/data /home/appuser

# Установка прав на скрипты
RUN chmod +x scripts/*.py || true

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DATABASE_URL=sqlite:////app/data/budget_bot.db \
    MPLCONFIGDIR=/tmp/matplotlib

# Переключение на пользователя без root-доступа
USER appuser

# Healthcheck: проверка подключения к SQLite
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/budget_bot.db').execute('SELECT 1')" || exit 1

EXPOSE 8080

# Запуск бота
CMD ["python", "bot.py"]
