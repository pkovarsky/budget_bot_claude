"""
Обработчик настроек уведомлений и напоминаний
"""
import logging
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import pytz

from database import get_db_session, User
from utils.localization import get_message
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)

async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню настроек уведомлений"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        # Статус настроек
        daily_status = "✅ Включено" if user.daily_reminder_enabled else "❌ Выключено"
        budget_status = "✅ Включено" if user.budget_notifications_enabled else "❌ Выключено"
        
        daily_time = user.daily_reminder_time.strftime("%H:%M") if user.daily_reminder_time else "не установлено"
        budget_time = user.budget_notification_time.strftime("%H:%M") if user.budget_notification_time else "не установлено"
        
        salary_date = f"{user.salary_date} числа" if user.salary_date else "не установлена"
        
        keyboard = [
            [InlineKeyboardButton("📅 Напоминания о тратах", callback_data="notif_daily")],
            [InlineKeyboardButton("💰 Уведомления о бюджете", callback_data="notif_budget")],
            [InlineKeyboardButton("💵 Дата зарплаты", callback_data="notif_salary")],
            [InlineKeyboardButton("🌍 Часовой пояс", callback_data="notif_timezone")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"🔔 **Настройки уведомлений**\n\n"
            f"📅 **Напоминания о тратах**: {daily_status}\n"
            f"⏰ Время: {daily_time}\n\n"
            f"💰 **Уведомления о бюджете**: {budget_status}\n"
            f"⏰ Время: {budget_time}\n"
            f"📊 Частота: {user.budget_notification_frequency}\n\n"
            f"💵 **Дата зарплаты**: {salary_date}\n"
            f"🌍 **Часовой пояс**: {user.timezone}\n\n"
            f"Выберите настройку для изменения:"
        )
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()

async def handle_notifications_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для настроек уведомлений"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        if data == "notif_daily":
            await _show_daily_reminder_settings(query, user)
        elif data == "notif_budget":
            await _show_budget_notification_settings(query, user)
        elif data == "notif_salary":
            await _show_salary_date_settings(query, user)
        elif data == "notif_timezone":
            await _show_timezone_settings(query, user)
        elif data == "notif_back":
            await _show_main_notifications_menu(query, user)
        elif data.startswith("daily_"):
            await _handle_daily_reminder_callback(query, context, user, data)
        elif data.startswith("budget_"):
            await _handle_budget_notification_callback(query, context, user, data)
        elif data.startswith("salary_"):
            await _handle_salary_date_callback(query, context, user, data)
        elif data.startswith("tz_"):
            await _handle_timezone_callback(query, context, user, data)
        
    finally:
        db.close()

async def _show_daily_reminder_settings(query, user: User):
    """Показать настройки напоминаний о тратах"""
    status = "✅ Включено" if user.daily_reminder_enabled else "❌ Выключено"
    time_str = user.daily_reminder_time.strftime("%H:%M") if user.daily_reminder_time else "не установлено"
    
    keyboard = [
        [InlineKeyboardButton(
            "🔄 Включить" if not user.daily_reminder_enabled else "❌ Выключить",
            callback_data="daily_toggle"
        )],
        [InlineKeyboardButton("⏰ Изменить время", callback_data="daily_time")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"📅 **Напоминания о добавлении трат**\n\n"
        f"**Статус**: {status}\n"
        f"**Время**: {time_str}\n\n"
        f"Если включено, бот будет напоминать вам добавить траты за день в указанное время, "
        f"если вы ещё не добавили ни одной транзакции."
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _show_budget_notification_settings(query, user: User):
    """Показать настройки уведомлений о бюджете"""
    status = "✅ Включено" if user.budget_notifications_enabled else "❌ Выключено"
    time_str = user.budget_notification_time.strftime("%H:%M") if user.budget_notification_time else "не установлено"
    
    freq_map = {
        "daily": "Ежедневно",
        "weekly": "Еженедельно",
        "none": "Выключено"
    }
    frequency = freq_map.get(user.budget_notification_frequency, "Неизвестно")
    
    keyboard = [
        [InlineKeyboardButton(
            "🔄 Включить" if not user.budget_notifications_enabled else "❌ Выключить",
            callback_data="budget_toggle"
        )],
        [InlineKeyboardButton("⏰ Изменить время", callback_data="budget_time")],
        [InlineKeyboardButton("📊 Изменить частоту", callback_data="budget_frequency")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"💰 **Уведомления о бюджете**\n\n"
        f"**Статус**: {status}\n"
        f"**Время**: {time_str}\n"
        f"**Частота**: {frequency}\n\n"
        f"Если включено, бот будет сообщать вам сколько денег осталось до зарплаты "
        f"по каждой категории с лимитом и сколько можно тратить в день.\n\n"
        f"⚠️ Требуется установить дату зарплаты и лимиты на категории."
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _show_salary_date_settings(query, user: User):
    """Показать настройки даты зарплаты"""
    salary_date = f"{user.salary_date} числа каждого месяца" if user.salary_date else "не установлена"
    
    keyboard = [
        [InlineKeyboardButton("📅 Установить дату", callback_data="salary_set")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"💵 **Дата зарплаты**\n\n"
        f"**Текущая дата**: {salary_date}\n\n"
        f"Дата зарплаты используется для расчета уведомлений о бюджете. "
        f"Укажите день месяца, когда вы получаете зарплату (например, 15 или 30)."
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _show_timezone_settings(query, user: User):
    """Показать настройки часового пояса"""
    common_timezones = [
        ("Europe/Amsterdam", "🇳🇱 Амстердам (CET/CEST)"),
        ("Europe/Berlin", "🇩🇪 Берлин (CET/CEST)"),
        ("Europe/London", "🇬🇧 Лондон (GMT/BST)"),
        ("Europe/Kiev", "🇺🇦 Киев (EET/EEST)"),
        ("Europe/Moscow", "🇷🇺 Москва (MSK)"),
        ("America/New_York", "🇺🇸 Нью-Йорк (EST/EDT)"),
        ("Asia/Tokyo", "🇯🇵 Токио (JST)")
    ]
    
    keyboard = []
    for tz_code, tz_name in common_timezones:
        status = "✅ " if user.timezone == tz_code else ""
        keyboard.append([InlineKeyboardButton(
            f"{status}{tz_name}",
            callback_data=f"tz_{tz_code}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🌍 **Часовой пояс**\n\n"
        f"**Текущий**: {user.timezone}\n\n"
        f"Выберите ваш часовой пояс для корректной работы уведомлений:"
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _handle_daily_reminder_callback(query, context: ContextTypes.DEFAULT_TYPE, user: User, data: str):
    """Обработка callback для напоминаний о тратах"""
    db = get_db_session()
    try:
        # Получаем пользователя в текущей сессии
        current_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
        if not current_user:
            return
            
        if data == "daily_toggle":
            current_user.daily_reminder_enabled = not current_user.daily_reminder_enabled
            db.commit()
            await _show_daily_reminder_settings(query, current_user)
        elif data == "daily_time":
            context.user_data['setting_daily_time'] = True
            await safe_edit_message(query,
                "⏰ **Установка времени напоминания**\n\n"
                "Отправьте время в формате ЧЧ:ММ (например, 20:00)\n\n"
                "Отправьте /cancel для отмены",
                parse_mode='Markdown'
            )
    finally:
        db.close()

async def _handle_budget_notification_callback(query, context: ContextTypes.DEFAULT_TYPE, user: User, data: str):
    """Обработка callback для уведомлений о бюджете"""
    db = get_db_session()
    try:
        # Получаем пользователя в текущей сессии
        current_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
        if not current_user:
            return
            
        if data == "budget_toggle":
            current_user.budget_notifications_enabled = not current_user.budget_notifications_enabled
            db.commit()
            await _show_budget_notification_settings(query, current_user)
        elif data == "budget_time":
            context.user_data['setting_budget_time'] = True
            await safe_edit_message(query,
                "⏰ **Установка времени уведомлений**\n\n"
                "Отправьте время в формате ЧЧ:ММ (например, 09:00)\n\n"
                "Отправьте /cancel для отмены",
                parse_mode='Markdown'
            )
        elif data == "budget_frequency":
            keyboard = [
                [InlineKeyboardButton("📅 Ежедневно", callback_data="budget_freq_daily")],
                [InlineKeyboardButton("📅 Еженедельно", callback_data="budget_freq_weekly")],
                [InlineKeyboardButton("❌ Выключить", callback_data="budget_freq_none")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await safe_edit_message(query,
                "📊 **Частота уведомлений о бюджете**\n\n"
                "Выберите как часто получать уведомления:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data.startswith("budget_freq_"):
            frequency = data.replace("budget_freq_", "")
            current_user.budget_notification_frequency = frequency
            db.commit()
            await _show_budget_notification_settings(query, current_user)
    finally:
        db.close()

async def _handle_salary_date_callback(query, context: ContextTypes.DEFAULT_TYPE, user: User, data: str):
    """Обработка callback для даты зарплаты"""
    if data == "salary_set":
        context.user_data['setting_salary_date'] = True
        await safe_edit_message(query,
            "📅 **Установка даты зарплаты**\n\n"
            "Отправьте день месяца, когда вы получаете зарплату (число от 1 до 31)\n\n"
            "Примеры: 15, 30, 1\n\n"
            "Отправьте /cancel для отмены",
            parse_mode='Markdown'
        )

async def _handle_timezone_callback(query, context: ContextTypes.DEFAULT_TYPE, user: User, data: str):
    """Обработка callback для часового пояса"""
    if data.startswith("tz_"):
        timezone = data.replace("tz_", "")
        
        db = get_db_session()
        try:
            # Получаем пользователя в текущей сессии
            current_user = db.query(User).filter(User.telegram_id == user.telegram_id).first()
            if not current_user:
                return
                
            current_user.timezone = timezone
            db.commit()
            await _show_timezone_settings(query, current_user)
        finally:
            db.close()

async def _show_main_notifications_menu(query, user: User):
    """Показать главное меню настроек уведомлений"""
    daily_status = "✅ Включено" if user.daily_reminder_enabled else "❌ Выключено"
    budget_status = "✅ Включено" if user.budget_notifications_enabled else "❌ Выключено"
    
    daily_time = user.daily_reminder_time.strftime("%H:%M") if user.daily_reminder_time else "не установлено"
    budget_time = user.budget_notification_time.strftime("%H:%M") if user.budget_notification_time else "не установлено"
    
    salary_date = f"{user.salary_date} числа" if user.salary_date else "не установлена"
    
    keyboard = [
        [InlineKeyboardButton("📅 Напоминания о тратах", callback_data="notif_daily")],
        [InlineKeyboardButton("💰 Уведомления о бюджете", callback_data="notif_budget")],
        [InlineKeyboardButton("💵 Дата зарплаты", callback_data="notif_salary")],
        [InlineKeyboardButton("🌍 Часовой пояс", callback_data="notif_timezone")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"🔔 **Настройки уведомлений**\n\n"
        f"📅 **Напоминания о тратах**: {daily_status}\n"
        f"⏰ Время: {daily_time}\n\n"
        f"💰 **Уведомления о бюджете**: {budget_status}\n"
        f"⏰ Время: {budget_time}\n"
        f"📊 Частота: {user.budget_notification_frequency}\n\n"
        f"💵 **Дата зарплаты**: {salary_date}\n"
        f"🌍 **Часовой пояс**: {user.timezone}\n\n"
        f"Выберите настройку для изменения:"
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE, setting_type: str) -> None:
    """Обработка ввода времени"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверка на отмену
    if text.lower() in ['/cancel', 'отмена', 'cancel']:
        context.user_data.pop(f'setting_{setting_type}_time', None)
        await update.message.reply_text("❌ Установка времени отменена.")
        return
    
    # Парсинг времени
    try:
        time_obj = datetime.strptime(text, "%H:%M").time()
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например, 20:00)"
        )
        return
    
    # Сохранение времени
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        if setting_type == "daily":
            user.daily_reminder_time = time_obj
            message = f"✅ Время напоминаний установлено на {text}"
        elif setting_type == "budget":
            user.budget_notification_time = time_obj
            message = f"✅ Время уведомлений о бюджете установлено на {text}"
        
        db.commit()
        context.user_data.pop(f'setting_{setting_type}_time', None)
        
        await update.message.reply_text(message)
        
    finally:
        db.close()

async def handle_salary_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода даты зарплаты"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверка на отмену
    if text.lower() in ['/cancel', 'отмена', 'cancel']:
        context.user_data.pop('setting_salary_date', None)
        await update.message.reply_text("❌ Установка даты зарплаты отменена.")
        return
    
    # Парсинг даты
    try:
        day = int(text)
        if day < 1 or day > 31:
            raise ValueError("День должен быть от 1 до 31")
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Укажите число от 1 до 31"
        )
        return
    
    # Сохранение даты
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        user.salary_date = day
        db.commit()
        context.user_data.pop('setting_salary_date', None)
        
        await update.message.reply_text(f"✅ Дата зарплаты установлена на {day} число каждого месяца")
        
    finally:
        db.close()


async def notifications_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /notifications через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Формируем статусы для отображения
        daily_status = "✅ Включено" if user.daily_reminder_enabled else "❌ Выключено"
        daily_time = user.daily_reminder_time.strftime("%H:%M") if user.daily_reminder_time else "не установлено"
        
        budget_status = "✅ Включено" if user.budget_notifications_enabled else "❌ Выключено"
        budget_time = user.budget_notification_time.strftime("%H:%M") if user.budget_notification_time else "не установлено"
        
        keyboard = [
            [InlineKeyboardButton("📅 Напоминания о тратах", callback_data="notif_daily")],
            [InlineKeyboardButton("💰 Уведомления о бюджете", callback_data="notif_budget")],
            [InlineKeyboardButton("💵 Дата зарплаты", callback_data="notif_salary")],
            [InlineKeyboardButton("🌍 Часовой пояс", callback_data="notif_timezone")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"🔔 **Настройки уведомлений**\n\n"
            f"📅 **Напоминания о тратах**: {daily_status}\n"
            f"⏰ Время: {daily_time}\n\n"
            f"💰 **Уведомления о бюджете**: {budget_status}\n"
            f"⏰ Время: {budget_time}\n"
            f"📊 Частота: {user.budget_notification_frequency}\n\n"
            f"💵 **Дата зарплаты**: {user.salary_date} числа\n"
            f"🌍 **Часовой пояс**: {user.timezone}\n\n"
            f"Настройте уведомления для лучшего контроля финансов."
        )
        
        await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()