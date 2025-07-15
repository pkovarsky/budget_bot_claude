import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category
from utils.localization import get_message, get_default_categories, get_supported_languages

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
            # Существующий пользователь
            name = user.name or "друг"
            await update.message.reply_text(
                f"{get_message('welcome_back', user.language, name=name)}\n\n"
                f"{get_message('help_commands', user.language)}"
            )
    finally:
        db.close()


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


async def ask_for_name(query, user, language: str) -> None:
    """Предложить пользователю указать имя"""
    keyboard = [
        [InlineKeyboardButton(
            "👤 Указать имя", 
            callback_data=f"setup_name_{user.id}"
        )],
        [InlineKeyboardButton(
            "⏭ Пропустить", 
            callback_data="setup_skip_name"
        )]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение для выбора имени
    from telegram import Bot
    bot = Bot.get_current()
    await bot.send_message(
        chat_id=query.message.chat_id,
        text=f"👋 Хотите указать ваше имя для персонализации?",
        reply_markup=reply_markup
    )


async def handle_name_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка настройки имени"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "setup_skip_name":
        await query.edit_message_text("✅ Настройка завершена! Используйте /help для просмотра команд.")
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
    
    if not name or len(name) > 50:
        await update.message.reply_text("Имя должно быть от 1 до 50 символов.")
        return
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            user.name = name
            db.commit()
            
            await update.message.reply_tчext(
                f"✅ Приятно познакомиться, {name}!\n\n"
                f"Настройка завершена. Используйте /help для просмотра команд.",
                parse_mode='Markdown'
            )
        
    finally:
        db.close()
        context.user_data.pop('setting_up_name', None)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        language = user.language if user else "ru"
        
        help_text = f"""
{get_message('help_title', language)}

**{get_message('transactions_section', language)}**
• `35 евро продукты` - добавить расход
• `+2000 евро зарплата` - добавить доход
• 📸 **Отправить фото чека** - автоматическое распознавание

**{get_message('commands_section', language)}**
• `/categories` - управление категориями
• `/stats` - статистика по периодам
• `/limits` - управление лимитами расходов
• `/export` - экспорт данных в Excel
• `/edit` - редактировать транзакции
• `/settings` - настройки (язык, имя)
• `/help` - эта справка

**Формат сообщений:**
• Сумма + валюта + описание
• Поддерживаются: {get_message('supported_currencies', language)}
• Для дохода добавьте '+' в начало

**{get_message('photo_section', language)}**
• Отправьте фото чека для автоматического добавления расходов
• ИИ распознает сумму, валюту и категоризирует покупку
• Поддерживаются четкие фото и документы
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    finally:
        db.close()