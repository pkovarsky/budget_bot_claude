#!/bin/bash

set -e  # Остановиться при ошибке

echo "📦 Установка Docker (если нужно)..."
sudo apt update
sudo apt install -y docker.io

echo "✅ Docker установлен: $(docker --version)"

echo "📁 Создание директории ./data с нужными правами..."
mkdir -p ./data
sudo chown -R 1000:1000 ./data
chmod -R 755 ./data

echo "🛠️ Проверка .env файла..."

if [ ! -f .env ]; then
  echo "❌ Файл .env не найден. Пожалуйста, создайте его в корне проекта."
  exit 1
fi

# Функция для проверки переменной
check_env_var() {
  local var_name="$1"
  if ! grep -qE "^$var_name=" .env || grep -qE "^$var_name=$" .env; then
    echo "❌ В .env отсутствует или пуста обязательная переменная: $var_name"
    exit 1
  fi
}

# Проверка трёх обязательных переменных
check_env_var TELEGRAM_BOT_TOKEN
check_env_var OPENAI_API_KEY
check_env_var DATABASE_URL

echo "✅ Все обязательные переменные найдены в .env"

echo "🐳 Сборка Docker-образа..."
docker build -t budget-bot .

echo "🧹 Удаление старого контейнера (если есть)..."
docker rm -f budget-bot || true

echo "🚀 Запуск нового контейнера..."
docker run -d --name budget-bot \
  --restart=always \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  budget-bot

echo "📡 Готово! Контейнер запущен:"
docker ps | grep budget-bot

echo "📜 Чтобы посмотреть логи: docker logs -f budget-bot"
