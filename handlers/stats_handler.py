import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction
from services.chart_service import ChartService
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /stats"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="stats_today"),
             InlineKeyboardButton("📆 Эта неделя", callback_data="stats_week")],
            [InlineKeyboardButton("📊 Этот месяц", callback_data="stats_month"),
             InlineKeyboardButton("📈 Все время", callback_data="stats_all")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 **Статистика**\n\n"
            "Выберите период для показа статистики:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для статистики"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("Сначала выполните команду /start")
            return
        
        now = datetime.now()
        
        if data == "stats_today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "Сегодня"
        elif data == "stats_week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = "Эта неделя"
        elif data == "stats_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_name = "Этот месяц"
        else:  # stats_all
            start_date = datetime(2020, 1, 1)
            period_name = "Все время"
        
        # Получаем транзакции за период
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= start_date
        ).all()
        
        if not transactions:
            keyboard = [
                [InlineKeyboardButton("🔙 Назад", callback_data="stats_back"),
                 InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📊 **{period_name}**\n\nНет транзакций за этот период.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        # Считаем доходы и расходы по валютам
        currencies = {}
        for transaction in transactions:
            currency = transaction.currency
            if currency not in currencies:
                currencies[currency] = {'income': 0, 'expenses': 0}
            
            if transaction.amount > 0:
                currencies[currency]['income'] += transaction.amount
            else:
                currencies[currency]['expenses'] += abs(transaction.amount)
        
        # Статистика по категориям (только расходы)
        category_stats = {}
        for transaction in transactions:
            if transaction.amount < 0:
                category = db.query(Category).filter(Category.id == transaction.category_id).first()
                if category:
                    if category.name not in category_stats:
                        category_stats[category.name] = {}
                    
                    currency = transaction.currency
                    if currency not in category_stats[category.name]:
                        category_stats[category.name][currency] = 0
                    category_stats[category.name][currency] += abs(transaction.amount)
        
        # Формируем текст ответа
        text = f"📊 **{period_name}**\n\n"
        
        # Общая статистика по валютам
        for currency, data in currencies.items():
            income = data['income']
            expenses = data['expenses']
            balance = income - expenses
            balance_emoji = "💚" if balance >= 0 else "❤️"
            
            text += f"**{currency}:**\n"
            text += f"💰 Доходы: {income:.2f}\n"
            text += f"💸 Расходы: {expenses:.2f}\n"
            text += f"{balance_emoji} Баланс: {balance:.2f}\n\n"
        
        # Топ категорий расходов
        if category_stats:
            text += "**🏷️ Топ категорий расходов:**\n"
            
            # Сортируем категории по общей сумме расходов
            category_totals = []
            for cat_name, currencies_data in category_stats.items():
                total = sum(currencies_data.values())
                category_totals.append((cat_name, total, currencies_data))
            
            category_totals.sort(key=lambda x: x[1], reverse=True)
            
            for cat_name, total, currencies_data in category_totals[:5]:  # Топ 5
                text += f"• {cat_name}: "
                currency_texts = []
                for currency, amount in currencies_data.items():
                    currency_texts.append(f"{amount:.2f} {currency}")
                text += ", ".join(currency_texts) + "\n"
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="stats_back"),
             InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def handle_stats_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка кнопки назад в статистике"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("Сначала выполните команду /start")
            return
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="stats_today"),
             InlineKeyboardButton("📆 Эта неделя", callback_data="stats_week")],
            [InlineKeyboardButton("📊 Этот месяц", callback_data="stats_month"),
             InlineKeyboardButton("📈 Все время", callback_data="stats_all")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 **Статистика**\n\n"
            "Выберите период для показа статистики:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def handle_charts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для графиков"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "stats_charts":
        keyboard = [
            [InlineKeyboardButton("🍰 Расходы по категориям", callback_data="chart_pie_30")],
            [InlineKeyboardButton("📈 Тренд расходов (30 дней)", callback_data="chart_trend_30")],
            [InlineKeyboardButton("📊 Сравнение по месяцам", callback_data="chart_monthly_6")],
            [InlineKeyboardButton("🔙 Назад", callback_data="stats_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 **Графики и диаграммы**\n\n"
            "Выберите тип графика:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data.startswith("chart_"):
        await query.edit_message_text("📊 Генерирую график...")
        
        chart_service = ChartService()
        buffer = None
        
        if data == "chart_pie_30":
            buffer = chart_service.generate_category_pie_chart(user_id, 30)
            caption = "🍰 Расходы по категориям за последние 30 дней"
        elif data == "chart_trend_30":
            buffer = chart_service.generate_spending_trends_chart(user_id, 30)
            caption = "📈 Тренд расходов по дням за последние 30 дней"
        elif data == "chart_monthly_6":
            buffer = chart_service.generate_monthly_comparison_chart(user_id, 6)
            caption = "📊 Сравнение расходов по месяцам за последние 6 месяцев"
        
        if buffer:
            keyboard = [[InlineKeyboardButton("🔙 К графикам", callback_data="back_to_charts")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_photo(
                photo=buffer,
                caption=caption,
                reply_markup=reply_markup
            )
            
            # Удаляем сообщение "Генерирую график..."
            await query.message.delete()
        else:
            keyboard = [[InlineKeyboardButton("🔙 К графикам", callback_data="back_to_charts")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "😔 Недостаточно данных для создания графика.\n"
                "Добавьте больше транзакций для получения статистики.",
                reply_markup=reply_markup
            )
    
    elif data == "back_to_charts":
        # Возвращаемся к меню графиков, удаляя фото и показывая текстовое меню
        keyboard = [
            [InlineKeyboardButton("🍰 Расходы по категориям", callback_data="chart_pie_30")],
            [InlineKeyboardButton("📈 Тренд расходов (30 дней)", callback_data="chart_trend_30")],
            [InlineKeyboardButton("📊 Сравнение по месяцам", callback_data="chart_monthly_6")],
            [InlineKeyboardButton("🔙 Назад", callback_data="stats_back")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Удаляем фото-сообщение
        await query.message.delete()
        
        # Отправляем новое текстовое сообщение с меню графиков
        await query.message.reply_text(
            "📊 **Графики и диаграммы**\n\n"
            "Выберите тип графика:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def stats_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /stats через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="stats_today"),
             InlineKeyboardButton("📆 Эта неделя", callback_data="stats_week")],
            [InlineKeyboardButton("📊 Этот месяц", callback_data="stats_month"),
             InlineKeyboardButton("📈 Все время", callback_data="stats_all")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query,
            "📊 **Статистика**\n\n"
            "Выберите период для показа статистики:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        db.close()