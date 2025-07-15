from typing import Dict, Any

# Словари локализации
MESSAGES = {
    "ru": {
        # Основные команды
        "welcome": "Добро пожаловать в Budget Bot, {name}! 🎯",
        "welcome_back": "С возвращением, {name}! 👋",
        "help_commands": "Используйте /help для просмотра команд.",
        
        # Команды
        "start_description": "Я помогу вам вести учет доходов и расходов.",
        "help_title": "🎯 **Budget Bot - Команды:**",
        "commands_section": "**Команды:**",
        "transactions_section": "**Добавление операций:**",
        "photo_section": "**📸 Распознавание чеков:**",
        
        # Транзакции
        "expense_added": "💸 Расход добавлен!",
        "income_added": "💰 Доход добавлен!",
        "amount": "Сумма",
        "category": "Категория",
        "description": "Описание",
        "transaction_error": "Не удалось распознать операцию. 🤔",
        "transaction_format_help": "Используйте формат: '35 евро продукты' или '+2000 евро зарплата'",
        
        # Категории
        "categories_title": "📁 Управление категориями",
        "choose_category": "Выберите категорию:",
        "suggest_category": "Предлагаемая категория: **{category}**",
        "category_question": "Подходит ли эта категория?",
        "yes": "✅ Да",
        "no": "❌ Нет, выбрать другую",
        "category_added": "Категория '{name}' добавлена!",
        "category_exists": "Категория '{name}' уже существует",
        
        # Валюты (без RUB)
        "supported_currencies": "EUR, USD",
        
        # Ошибки
        "start_first": "Сначала выполните команду /start",
        "error_occurred": "Произошла ошибка. Попробуйте позже.",
        
        # Редактирование
        "edit_transactions": "✏️ Редактировать транзакции",
        "select_period": "Выберите период:",
        "today": "📅 Сегодня",
        "this_week": "📆 Эта неделя", 
        "this_month": "📊 Этот месяц",
        "no_transactions": "Нет транзакций за этот период",
        "select_transaction": "Выберите транзакцию для редактирования:",
        "edit_amount": "✏️ Изменить сумму",
        "delete_transaction": "🗑 Удалить",
        "transaction_deleted": "Транзакция удалена",
        "enter_new_amount": "Введите новую сумму:",
        "amount_updated": "Сумма обновлена",
        
        # Настройки
        "settings": "⚙️ Настройки",
        "language_settings": "🌍 Язык",
        "name_settings": "👤 Имя",
        "choose_language": "Выберите язык:",
        "language_changed": "Язык изменен на русский",
        "enter_name": "Введите ваше имя:",
        "name_updated": "Имя обновлено: {name}",
        
        # Фото
        "analyzing_receipt": "📸 Анализирую чек... Это может занять несколько секунд.",
        "receipt_processed": "✅ Чек обработан!",
        "receipt_error": "❌ Не удалось распознать чек. Убедитесь, что фото четкое.",
    },
    
    "en": {
        # Basic commands
        "welcome": "Welcome to Budget Bot, {name}! 🎯",
        "welcome_back": "Welcome back, {name}! 👋",
        "help_commands": "Use /help to view commands.",
        
        # Commands
        "start_description": "I'll help you track your income and expenses.",
        "help_title": "🎯 **Budget Bot - Commands:**",
        "commands_section": "**Commands:**",
        "transactions_section": "**Adding transactions:**",
        "photo_section": "**📸 Receipt recognition:**",
        
        # Transactions
        "expense_added": "💸 Expense added!",
        "income_added": "💰 Income added!",
        "amount": "Amount",
        "category": "Category", 
        "description": "Description",
        "transaction_error": "Failed to recognize transaction. 🤔",
        "transaction_format_help": "Use format: '35 euros groceries' or '+2000 euros salary'",
        
        # Categories
        "categories_title": "📁 Manage categories",
        "choose_category": "Choose category:",
        "suggest_category": "Suggested category: **{category}**",
        "category_question": "Is this category suitable?",
        "yes": "✅ Yes",
        "no": "❌ No, choose another",
        "category_added": "Category '{name}' added!",
        "category_exists": "Category '{name}' already exists",
        
        # Currencies (without RUB)
        "supported_currencies": "EUR, USD",
        
        # Errors
        "start_first": "Please run /start command first",
        "error_occurred": "An error occurred. Please try later.",
        
        # Editing
        "edit_transactions": "✏️ Edit transactions",
        "select_period": "Select period:",
        "today": "📅 Today",
        "this_week": "📆 This week",
        "this_month": "📊 This month", 
        "no_transactions": "No transactions for this period",
        "select_transaction": "Select transaction to edit:",
        "edit_amount": "✏️ Edit amount",
        "delete_transaction": "🗑 Delete",
        "transaction_deleted": "Transaction deleted",
        "enter_new_amount": "Enter new amount:",
        "amount_updated": "Amount updated",
        
        # Settings
        "settings": "⚙️ Settings",
        "language_settings": "🌍 Language",
        "name_settings": "👤 Name",
        "choose_language": "Choose language:",
        "language_changed": "Language changed to English",
        "enter_name": "Enter your name:",
        "name_updated": "Name updated: {name}",
        
        # Photo
        "analyzing_receipt": "📸 Analyzing receipt... This may take a few seconds.",
        "receipt_processed": "✅ Receipt processed!",
        "receipt_error": "❌ Failed to recognize receipt. Make sure photo is clear.",
    },
    
    "uk": {
        # Основні команди
        "welcome": "Ласкаво просимо до Budget Bot, {name}! 🎯",
        "welcome_back": "З поверненням, {name}! 👋",
        "help_commands": "Використовуйте /help для перегляду команд.",
        
        # Команди
        "start_description": "Я допоможу вам вести облік доходів та витрат.",
        "help_title": "🎯 **Budget Bot - Команди:**",
        "commands_section": "**Команди:**",
        "transactions_section": "**Додавання операцій:**",
        "photo_section": "**📸 Розпізнавання чеків:**",
        
        # Транзакції
        "expense_added": "💸 Витрату додано!",
        "income_added": "💰 Дохід додано!",
        "amount": "Сума",
        "category": "Категорія",
        "description": "Опис",
        "transaction_error": "Не вдалося розпізнати операцію. 🤔",
        "transaction_format_help": "Використовуйте формат: '35 євро продукти' або '+2000 євро зарплата'",
        
        # Категорії
        "categories_title": "📁 Управління категоріями",
        "choose_category": "Оберіть категорію:",
        "suggest_category": "Запропонована категорія: **{category}**",
        "category_question": "Чи підходить ця категорія?",
        "yes": "✅ Так",
        "no": "❌ Ні, обрати іншу",
        "category_added": "Категорію '{name}' додано!",
        "category_exists": "Категорія '{name}' вже існує",
        
        # Валюти (без RUB)
        "supported_currencies": "EUR, USD",
        
        # Помилки
        "start_first": "Спершу виконайте команду /start",
        "error_occurred": "Сталася помилка. Спробуйте пізніше.",
        
        # Редагування
        "edit_transactions": "✏️ Редагувати транзакції",
        "select_period": "Оберіть період:",
        "today": "📅 Сьогодні",
        "this_week": "📆 Цей тиждень",
        "this_month": "📊 Цей місяць",
        "no_transactions": "Немає транзакцій за цей період",
        "select_transaction": "Оберіть транзакцію для редагування:",
        "edit_amount": "✏️ Змінити суму",
        "delete_transaction": "🗑 Видалити",
        "transaction_deleted": "Транзакцію видалено",
        "enter_new_amount": "Введіть нову суму:",
        "amount_updated": "Суму оновлено",
        
        # Налаштування
        "settings": "⚙️ Налаштування", 
        "language_settings": "🌍 Мова",
        "name_settings": "👤 Ім'я",
        "choose_language": "Оберіть мову:",
        "language_changed": "Мову змінено на українську",
        "enter_name": "Введіть ваше ім'я:",
        "name_updated": "Ім'я оновлено: {name}",
        
        # Фото
        "analyzing_receipt": "📸 Аналізую чек... Це може зайняти кілька секунд.",
        "receipt_processed": "✅ Чек оброблено!",
        "receipt_error": "❌ Не вдалося розпізнати чек. Переконайтеся, що фото чітке.",
    }
}

# Категории по умолчанию для разных языков
DEFAULT_CATEGORIES = {
    "ru": ["Продукты", "Транспорт", "Развлечения", "Здоровье", "Одежда", "Коммунальные услуги", "Ресторан", "Прочее"],
    "en": ["Groceries", "Transport", "Entertainment", "Health", "Clothing", "Utilities", "Restaurant", "Other"],
    "uk": ["Продукти", "Транспорт", "Розваги", "Здоров'я", "Одяг", "Комунальні послуги", "Ресторан", "Інше"]
}

def get_message(key: str, language: str = "ru", **kwargs) -> str:
    """Получить локализованное сообщение"""
    if language not in MESSAGES:
        language = "ru"
    
    message = MESSAGES[language].get(key, MESSAGES["ru"].get(key, key))
    
    if kwargs:
        try:
            return message.format(**kwargs)
        except KeyError:
            return message
    
    return message

def get_default_categories(language: str = "ru") -> list:
    """Получить категории по умолчанию для языка"""
    return DEFAULT_CATEGORIES.get(language, DEFAULT_CATEGORIES["ru"])

def get_supported_languages() -> Dict[str, str]:
    """Получить список поддерживаемых языков"""
    return {
        "ru": "🇷🇺 Русский",
        "en": "🇺🇸 English", 
        "uk": "🇺🇦 Українська"
    }