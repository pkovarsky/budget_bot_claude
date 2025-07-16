import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category
from utils.localization import get_message, get_default_categories, get_supported_languages
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            # Новый пользователь - предлагаем выбрать язык
            await show_language_selection(update, user_id, username)
            return
        else:
            # Существующий пользователь - показываем главное меню
            name = user.name or "друг"
            await show_main_menu(update, user)
    finally:
        db.close()


async def show_main_menu(update: Update, user: User) -> None:
    """Показать главное меню с кнопками основных функций"""
    name = user.name or "друг"
    
    # Создаем клавиатуру с основными функциями
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="main_stats"),
         InlineKeyboardButton("📈 Графики", callback_data="main_charts")],
        [InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
         InlineKeyboardButton("✏️ Редактировать", callback_data="main_edit")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="main_settings"),
         InlineKeyboardButton("❓ Справка", callback_data="main_help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"👋 {get_message('welcome_back', user.language, name=name)}\n\n"
        f"🎯 **Главное меню**\n\n"
        f"Выберите действие или просто отправьте сообщение с тратой:\n"
        f"• `35 продукты` - добавить расход\n"
        f"• `+2000 зарплата` - добавить доход\n"
        f"• 📸 **Фото чека** - автоматическое распознавание\n\n"
        f"Доступны команды: /categories, /stats, /charts, /limits, /export, /settings, /notifications"
    )
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_language_selection(update: Update, user_id: int, username: str) -> None:
    """Показать выбор языка для нового пользователя"""
    languages = get_supported_languages()
    keyboard = []
    
    for lang_code, lang_name in languages.items():
        keyboard.append([InlineKeyboardButton(
            lang_name, 
            callback_data=f"setup_lang_{lang_code}_{user_id}_{username or 'unknown'}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🌍 Добро пожаловать в Budget Bot!\n"
        "Welcome to Budget Bot!\n"
        "Ласкаво просимо до Budget Bot!\n\n"
        "Выберите язык / Choose language / Оберіть мову:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_language_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора языка при настройке"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split('_')
    if len(data_parts) < 4:
        return
    
    language = data_parts[2]
    user_id = int(data_parts[3])
    username = data_parts[4] if data_parts[4] != 'unknown' else None
    
    db = get_db_session()
    try:
        # Создаем нового пользователя
        user = User(
            telegram_id=user_id, 
            username=username,
            language=language
        )
        db.add(user)
        db.commit()
        
        # Добавляем базовые категории на выбранном языке
        default_categories = get_default_categories(language)
        for cat_name in default_categories:
            category = Category(name=cat_name, user_id=user.id, is_default=True)
            db.add(category)
        db.commit()
        
        # Приветствие на выбранном языке
        welcome_text = (
            f"{get_message('welcome', language, name='друг')}\n\n"
            f"{get_message('start_description', language)}\n\n"
            f"{get_message('help_commands', language)}"
        )
        
        await query.edit_message_text(welcome_text, parse_mode='Markdown')
        
        # Предлагаем указать имя
        await ask_for_name(query, user, language)
        
    finally:
        db.close()


async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопок главного меню"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    data = query.data
    
    # Обработка кнопок главного меню через callback
    if data == "main_stats":
        from handlers.stats_handler import stats_command_callback
        await stats_command_callback(update, context)
    elif data == "main_charts":
        from handlers.charts_handler import charts_command_callback
        await charts_command_callback(update, context)
    elif data == "main_categories":
        from handlers.categories_handler import categories_command_callback
        await categories_command_callback(update, context)
    elif data == "main_limits":
        from handlers.limits_handler import limits_command_callback
        await limits_command_callback(update, context)
    elif data == "main_export":
        from handlers.export_handler import export_command_callback
        await export_command_callback(update, context)
    elif data == "main_notifications":
        from handlers.notifications_handler import notifications_command_callback
        await notifications_command_callback(update, context)
    elif data == "main_settings":
        from handlers.settings_handler import settings_command_callback
        await settings_command_callback(update, context)
    elif data == "main_edit":
        from handlers.edit_handler import edit_command_callback
        await edit_command_callback(update, context)
    elif data == "main_help":
        await help_command_callback(update, context)


async def help_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Показываем интерактивную справку
        keyboard = [
            [InlineKeyboardButton("💰 Добавление трат", callback_data="help_spending")],
            [InlineKeyboardButton("📸 Фото чеков", callback_data="help_photos")],
            [InlineKeyboardButton("🧠 Умная система", callback_data="help_memory")],
            [InlineKeyboardButton("📊 Команды", callback_data="help_commands")],
            [InlineKeyboardButton("🔔 Уведомления", callback_data="help_notifications")],
            [InlineKeyboardButton("📈 Графики", callback_data="help_charts")],
            [InlineKeyboardButton("🎯 Быстрый старт", callback_data="help_quickstart")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        name = user.name or "друг"
        message = (
            f"❓ **Справка Budget Bot**\n\n"
            f"Привет, {name}! Выберите раздел для получения подробной информации:\n\n"
            f"• 💰 **Добавление трат** - как правильно записывать операции\n"
            f"• 📸 **Фото чеков** - автоматическое распознавание\n"
            f"• 🧠 **Умная система** - как работает система памяти\n"
            f"• 📊 **Команды** - все доступные команды\n"
            f"• 🔔 **Уведомления** - настройка напоминаний\n"
            f"• 📈 **Графики** - визуализация трат\n"
            f"• 🎯 **Быстрый старт** - для новичков"
        )
        
        await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /menu для показа главного меню"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        await show_main_menu(update, user)
    finally:
        db.close()


async def return_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат к главному меню (для кнопок 'Назад')"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Создаем клавиатуру с основными функциями
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="main_stats"),
             InlineKeyboardButton("📈 Графики", callback_data="main_charts")],
            [InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
             InlineKeyboardButton("✏️ Редактировать", callback_data="main_edit")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="main_settings"),
             InlineKeyboardButton("❓ Справка", callback_data="main_help")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        name = user.name or "друг"
        message = (
            f"👋 {get_message('welcome_back', user.language, name=name)}\n\n"
            f"🎯 **Главное меню**\n\n"
            f"Выберите действие или просто отправьте сообщение с тратой:\n"
            f"• `35 продукты` - добавить расход\n"
            f"• `+2000 зарплата` - добавить доход\n"
            f"• 📸 **Фото чека** - автоматическое распознавание\n\n"
            f"Доступны команды: /categories, /stats, /charts, /limits, /export, /settings, /notifications"
        )
        
        await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()


async def ask_for_name(query, user, language: str) -> None:
    """Предложить пользователю указать имя"""
    keyboard = [
        [InlineKeyboardButton(
            "👤 Указать имя", 
            callback_data=f"setup_name_{user.telegram_id}"
        )],
        [InlineKeyboardButton(
            "⏭ Пропустить", 
            callback_data="setup_skip_name"
        )]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение для выбора имени
    await query.message.reply_text(
        text="👋 Хотите указать ваше имя для персонализации?",
        reply_markup=reply_markup
    )


async def handle_name_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка настройки имени"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "setup_skip_name":
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        await query.edit_message_text(
            "✅ Настройка завершена! Теперь вы можете использовать бота.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    if query.data.startswith("setup_name_"):
        user_id = int(query.data.split('_')[2])
        context.user_data['setting_up_name'] = user_id

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="setup_back")]]
        await query.edit_message_text(
            "👤 Введите ваше имя (до 50 символов):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    if query.data == "setup_back":
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
            language = user.language if user else "ru"
            await ask_for_name(query, user, language)
        finally:
            db.close()
        context.user_data.pop('setting_up_name', None)
        return


async def handle_name_input_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода имени при первичной настройке"""
    if 'setting_up_name' not in context.user_data:
        return
    
    user_id = context.user_data['setting_up_name']
    name = update.message.text.strip()
    
    logger.info(f"Обработка ввода имени: user_id={user_id}, name='{name}'")
    
    if not name or len(name) > 50:
        keyboard = [[InlineKeyboardButton("🔙 Попробовать снова", callback_data=f"setup_name_{user_id}")]]
        await update.message.reply_text(
            "Имя должно быть от 1 до 50 символов.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.name = name
            db.commit()
            
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await update.message.reply_text(
                f"✅ Приятно познакомиться, {name}!\n\n"
                f"Настройка завершена. Теперь вы можете использовать бота.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await update.message.reply_text(
                "❌ Ошибка: пользователь не найден. Выполните команду /start",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении имени: {e}", exc_info=True)
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        await update.message.reply_text(
            f"❌ Произошла ошибка при сохранении имени: {str(e)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()
        context.user_data.pop('setting_up_name', None)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help с интерактивным меню"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        language = user.language if user else "ru"
        
        # Основной текст справки
        help_text = """
🤖 **Budget Bot - Умный помощник для финансов**

Выберите раздел для получения подробной информации:
        """
        
        # Создаем интерактивные кнопки
        keyboard = [
            [
                InlineKeyboardButton("💰 Добавление трат", callback_data="help_transactions"),
                InlineKeyboardButton("📸 Фото чеков", callback_data="help_photos")
            ],
            [
                InlineKeyboardButton("🧠 Умная система", callback_data="help_memory"),
                InlineKeyboardButton("📊 Команды", callback_data="help_commands")
            ],
            [
                InlineKeyboardButton("🔔 Уведомления", callback_data="help_notifications"),
                InlineKeyboardButton("📈 Графики", callback_data="help_charts")
            ],
            [
                InlineKeyboardButton("🎯 Быстрый старт", callback_data="help_quickstart")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()


async def handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback'ов для справочной системы"""
    query = update.callback_query
    await query.answer()
    
    help_section = query.data.replace("help_", "")
    
    help_texts = {
        "transactions": """
💰 **Добавление трат**

**Расходы (EUR по умолчанию):**
• `35 продукты` → 35 EUR продукты
• `150 USD такси` → с указанием валюты
• `20 кофе` → 20 EUR кофе

**Доходы (с плюсом):**
• `+2000 зарплата` → +2000 EUR зарплата
• `+500 USD фриланс` → +500 USD фриланс

**Поддерживаемые валюты:**
EUR (по умолчанию), USD

**Формат:** сумма + [валюта] + описание
        """,
        
        "photos": """
📸 **Распознавание фото чеков**

**Как использовать:**
1. Сделайте четкое фото чека
2. Отправьте фото в чат
3. ИИ автоматически распознает и добавит покупки

**Что распознает:**
• Общую сумму и валюту
• Отдельные товары (если различимо)
• Название магазина
• Автоматически определяет категорию

**Поддерживаемые форматы:**
• Фотографии (PNG, JPG)
• Документы с изображениями
• Размер до 20MB
        """,
        
        "memory": """
🧠 **Умная система памяти**

**Как работает:**
• Бот запоминает ваши выборы категорий
• Для похожих описаний предлагает ту же категорию
• Чем чаще используете, тем точнее предложения

**Преимущества:**
• Экономия времени - мгновенные предложения
• Меньше запросов к ИИ
• Персонализация под ваши привычки

**Примеры:**
1. Первый раз: "продукты" → выбираете "Еда"
2. В следующий раз: "продукты в магазине" → автоматически предлагает "Еда"

**Совет:** Система становится умнее с каждым использованием!
        """,
        
        "commands": """
📊 **Команды бота**

**Основные:**
• `/categories` - 📁 управление категориями
• `/stats` - ⚡ быстрая статистика
• `/charts` - 📈 графики с выбором периода

**Управление:**
• `/limits` - 💳 лимиты расходов
• `/export` - 📤 экспорт в Excel
• `/edit` - ✏️ редактировать транзакции

**Настройки:**
• `/notifications` - 🔔 уведомления
• `/settings` - ⚙️ настройки профиля
• `/help` - 📖 эта справка

**Навигация:** 
Используйте кнопки "◀️ Назад" для возврата в меню
        """,
        
        "notifications": """
🔔 **Система уведомлений**

**Напоминания о тратах:**
• Ежедневные напоминания в установленное время
• Уведомление если не добавляли траты за день

**Бюджетные уведомления:**
• Статус бюджета с расчетом до зарплаты
• Сколько можно тратить в день по категориям
• Уведомления о превышении лимитов

**Настройки:**
• Выбор времени уведомлений
• Настройка частоты (ежедневно/еженедельно)
• Установка даты зарплаты
• Выбор часового пояса

**Как настроить:**
`/notifications` → выберите нужные опции
        """,
        
        "charts": """
📈 **Графики и аналитика**

**Типы графиков:**
• 🥧 Расходы по категориям (круговая диаграмма)
• 📈 Тренд расходов по дням
• 📊 Сравнение расходов по месяцам

**Темная тема:**
• Стильный дизайн с неоновыми цветами
• Градиенты и тени для объема
• Эмодзи в заголовках

**Периоды:**
• Дни: 7, 14, 30, 60, 90 дней
• Месяцы: 3, 6, 12, 24 месяца

**Доступ:**
`/charts` → выберите тип графика и период
        """,
        
        "quickstart": """
🎯 **Быстрый старт**

**1. Добавьте первую трату:**
`35 продукты`

**2. Выберите категорию:**
Бот предложит варианты → выберите подходящий

**3. Попробуйте фото чека:**
Отправьте фото любого чека

**4. Посмотрите статистику:**
`/stats` или `/charts`

**5. Настройте уведомления:**
`/notifications` → включите напоминания

**6. Установите лимиты:**
`/limits` → добавьте лимиты на категории

**Готово!** Теперь бот запомнит ваши предпочтения и будет предлагать категории автоматически.

💡 **Совет:** Чаще используйте бот - он становится умнее!
        """
    }
    
    if help_section in help_texts:
        # Создаем кнопку "Назад"
        keyboard = [[InlineKeyboardButton("◀️ Назад к разделам", callback_data="help_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            help_texts[help_section],
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif help_section == "back":
        # Возвращаемся к основному меню справки
        help_text = """
🤖 **Budget Bot - Умный помощник для финансов**

Выберите раздел для получения подробной информации:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("💰 Добавление трат", callback_data="help_transactions"),
                InlineKeyboardButton("📸 Фото чеков", callback_data="help_photos")
            ],
            [
                InlineKeyboardButton("🧠 Умная система", callback_data="help_memory"),
                InlineKeyboardButton("📊 Команды", callback_data="help_commands")
            ],
            [
                InlineKeyboardButton("🔔 Уведомления", callback_data="help_notifications"),
                InlineKeyboardButton("📈 Графики", callback_data="help_charts")
            ],
            [
                InlineKeyboardButton("🎯 Быстрый старт", callback_data="help_quickstart")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')


