import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User
from utils.localization import get_message, get_supported_languages
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /settings для настроек пользователя"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text(get_message("start_first", "ru"))
            return
        
        # Создаем клавиатуру настроек
        keyboard = [
            [InlineKeyboardButton(
                get_message("language_settings", user.language), 
                callback_data="settings_language"
            )],
            [InlineKeyboardButton(
                get_message("name_settings", user.language), 
                callback_data="settings_name"
            )]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Информация о текущих настройках
        current_lang = get_supported_languages().get(user.language, "🇷🇺 Русский")
        current_name = user.name or "Не указано"
        
        settings_text = (
            f"{get_message('settings', user.language)}\n\n"
            f"🌍 {get_message('language_settings', user.language)}: {current_lang}\n"
            f"👤 {get_message('name_settings', user.language)}: {current_name}"
        )
        
        await update.message.reply_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для настроек"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text(get_message("start_first", "ru"))
            return
        
        if data == "settings_language":
            # Показать выбор языка
            keyboard = []
            languages = get_supported_languages()
            
            for lang_code, lang_name in languages.items():
                keyboard.append([InlineKeyboardButton(
                    lang_name, 
                    callback_data=f"set_lang_{lang_code}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                get_message("choose_language", user.language),
                reply_markup=reply_markup
            )
            
        elif data.startswith("set_lang_"):
            # Установить язык
            new_language = data.split("_")[2]
            user.language = new_language
            db.commit()
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                get_message("language_changed", new_language),
                reply_markup=reply_markup
            )
            
        elif data == "settings_name":
            # Запросить ввод имени
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="settings_back")]]
            await query.edit_message_text(
                f"{get_message('enter_name', user.language)}\n\n"
                f"💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            context.user_data['setting_name'] = True

        elif data == "settings_back":
            # Вернуться к настройкам
            context.user_data.pop('setting_name', None)
            await settings_command_callback(update, context)
            
    finally:
        db.close()


async def handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода имени пользователя"""
    if not context.user_data.get('setting_name'):
        return
    
    user_id = update.effective_user.id
    name = update.message.text.strip()
    
    # Проверяем на отмену
    if name.lower() in ['/cancel', 'отмена', 'cancel']:
        context.user_data.pop('setting_name', None)
        await update.message.reply_text(
            "❌ Изменение имени отменено.",
            reply_markup=None
        )
        return
    
    if not name or len(name) > 50:
        await update.message.reply_text("Имя должно быть от 1 до 50 символов.")
        return
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text(get_message("start_first", "ru"))
            return
        
        user.name = name
        db.commit()
        
        await update.message.reply_text(
            get_message("name_updated", user.language, name=name)
        )
        
    finally:
        db.close()
        context.user_data.pop('setting_name', None)


async def settings_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /settings через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, get_message("start_first", "ru"))
            return
        
        # Информация о текущих настройках
        current_lang = get_supported_languages().get(user.language, "🇷🇺 Русский")
        current_name = user.name or "Не указано"
        
        message = (
            f"⚙️ **Настройки**\n\n"
            f"👤 **Имя**: {current_name}\n"
            f"🌍 **Язык**: {current_lang}\n\n"
            f"Выберите что хотите изменить:"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 Изменить имя", callback_data="settings_name")],
            [InlineKeyboardButton("🌍 Изменить язык", callback_data="settings_language")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()