# 🐳 Multi-stage Dockerfile for Budget Bot
FROM python:3.11-slim as base

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Установка рабочей директории
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Установка только runtime зависимостей
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Создание директории приложения
WORKDIR /app

# Копирование Python зависимостей из базового образа
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Создание директории для данных
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Копирование исходного кода
COPY --chown=appuser:appuser . .

# Установка прав на выполнение скриптов
RUN chmod +x scripts/*.py

# Переключение на пользователя без root прав
USER appuser

# Переменные окружения для Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DATABASE_URL=sqlite:////app/data/budget_bot.db

# Создание базы данных при запуске
RUN python -c "from database import create_tables; create_tables()"

# Healthcheck для контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('/app/data/budget_bot.db').execute('SELECT 1')" || exit 1

# Expose порт (хотя Telegram bot не использует HTTP)
EXPOSE 8080

# Запуск бота
CMD ["python", "bot.py"]