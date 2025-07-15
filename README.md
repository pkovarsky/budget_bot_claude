# 💰 Budget Bot

Умный Telegram-бот для управления личными финансами с поддержкой ИИ-категоризации расходов и доходов.

## 🚀 Возможности

- **📊 Автоматическая категоризация** транзакций с помощью OpenAI
- **📸 Распознавание чеков** - отправьте фото чека для автоматического добавления расходов
- **💱 Поддержка валют**: EUR, USD
- **📈 Статистика** по периодам (день, неделя, месяц, все время)
- **📋 Управление категориями** с CRUD операциями
- **💳 Лимиты расходов** с уведомлениями
- **📤 Экспорт данных** в Excel с детальной статистикой
- **🤖 Естественный язык**: "35 евро продукты" или "+2000 рублей зарплата"

## 📁 Структура проекта

```
budget_bot_claude/
├── bot.py                    # Основной файл запуска
├── config.py                 # Конфигурация
├── database.py               # Модели базы данных
├── openai_service.py         # Сервис OpenAI
├── requirements.txt          # Зависимости
├── .env.example              # Пример переменных окружения
├── handlers/                 # Обработчики команд
│   ├── start_handler.py      # /start, /help
│   ├── transaction_handler.py # Обработка транзакций
│   ├── categories_handler.py  # /categories
│   ├── stats_handler.py      # /stats
│   ├── limits_handler.py     # /limits
│   ├── export_handler.py     # /export
│   └── photo_handler.py      # 📸 Распознавание чеков
└── utils/                    # Утилиты
    └── parsers.py           # Парсинг сообщений
```

## 🛠 Установка и настройка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd budget_bot_claude
```

**Требования:** Python 3.13 или новее.

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env` и заполните необходимые данные:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///budget_bot.db
```

### 4. Получение API ключей

#### Telegram Bot Token
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям и получите токен
4. Вставьте токен в `.env`

#### OpenAI API Key
1. Зарегистрируйтесь на [OpenAI](https://platform.openai.com/)
2. Перейдите в API Keys
3. Создайте новый ключ
4. Вставьте ключ в `.env`

### 5. Настройка базы данных

#### SQLite (по умолчанию)
База данных создастся автоматически при первом запуске.

#### PostgreSQL (опционально)
```bash
# Установка PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Создание базы данных
sudo -u postgres createdb budget_bot

# Обновите DATABASE_URL в .env:
DATABASE_URL=postgresql://username:password@localhost/budget_bot
```

#### MySQL (опционально)
```bash
# Установка MySQL
sudo apt-get install mysql-server

# Создание базы данных
mysql -u root -p
CREATE DATABASE budget_bot;

# Обновите DATABASE_URL в .env:
DATABASE_URL=mysql://username:password@localhost/budget_bot
```

### 6. Запуск бота

```bash
python bot.py
```

## 🎯 Использование

### Основные команды

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/categories` - Управление категориями
- `/stats` - Просмотр статистики
- `/limits` - Управление лимитами
- `/export` - Экспорт данных в Excel

### Добавление транзакций

#### Расходы:
```
35 евро продукты
150 рублей такси
20 USD кофе
```

#### Доходы:
```
+2000 евро зарплата  
+500 рублей подработка
+100 USD фриланс
```

#### 📸 Распознавание чеков:
Просто отправьте фото чека в чат! ИИ автоматически:
- Распознает общую сумму и валюту
- Определит название магазина
- Категоризирует покупку
- Добавит транзакцию в ваш бюджет

**Поддерживаемые форматы:**
- Фотографии чеков (PNG, JPG)
- Документы с изображениями
- Размер до 20MB

### Поддерживаемые форматы

- **Валюты**: евро, EUR, €, доллары, USD, $
- **Форматы**: 
  - `[сумма] [валюта] [описание]`
  - `[сумма] [описание] [валюта]`
  - `+[сумма] [валюта] [описание]` (для доходов)

## 🏗 Архитектура

### Модули

- **bot.py** - Точка входа, настройка handlers
- **handlers/** - Обработчики команд (разделены по функциональности)
- **utils/parsers.py** - Парсинг текстовых сообщений
- **database.py** - SQLAlchemy модели и настройки БД
- **openai_service.py** - Интеграция с OpenAI для категоризации
- **config.py** - Управление конфигурацией

### База данных

#### Модели:
- **User** - Пользователи Telegram
- **Category** - Категории доходов/расходов
- **Transaction** - Транзакции с суммой, валютой, описанием
- **Limit** - Лимиты расходов по категориям

## 🔧 Разработка

### Запуск в режиме разработки

```bash
# С детальным логированием
python -u bot.py

# Или установите ENVIRONMENT=development в .env
```

### Структура обработчиков

Каждый handler содержит:
- Обработчик команды
- Callback handlers для inline кнопок
- Валидация и обработка ошибок

### Добавление новых функций

1. Создайте новый handler в `handlers/`
2. Импортируйте в `bot.py`
3. Зарегистрируйте CommandHandler в `main()`

## 📊 Особенности

### ИИ-категоризация
- Автоматическое определение категории по описанию
- Обучение на существующих категориях пользователя
- Fallback на категорию "Прочее"

### Мульти-валютность
- Поддержка EUR, USD
- Раздельная статистика по валютам
- Конвертация не требуется

### Лимиты и уведомления
- Месячные лимиты по категориям
- Уведомления при 80% и 100% лимита
- Цветовая индикация статуса

## 🐛 Решение проблем

### Частые ошибки

**"ModuleNotFoundError: No module named 'telegram'"**
```bash
pip install python-telegram-bot==20.7
```

**"Invalid token"**
- Проверьте TELEGRAM_BOT_TOKEN в .env
- Убедитесь, что токен получен от @BotFather

**"OpenAI API error"**
- Проверьте OPENAI_API_KEY в .env
- Убедитесь, что у вас есть средства на счету OpenAI

**"Database connection error"**
- Проверьте DATABASE_URL в .env
- Убедитесь, что база данных доступна

### Логи

Логи сохраняются в консоль. Для детального анализа используйте:

```bash
python bot.py 2>&1 | tee bot.log
```

## 📝 Лицензия

MIT License - см. файл LICENSE

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Создайте Pull Request

## 📞 Поддержка

При возникновении вопросов создайте Issue в репозитории с подробным описанием проблемы.

---

**Budget Bot** - ваш персональный помощник в управлении финансами! 💰✨