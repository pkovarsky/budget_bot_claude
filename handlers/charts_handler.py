"""
Обработчик графиков и статистики с выбором периода
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User
from services.chart_service import ChartService
from utils.localization import get_message
from utils.telegram_utils import safe_edit_message, safe_answer_callback, safe_delete_message

logger = logging.getLogger(__name__)

async def charts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Главное меню графиков"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await update.message.reply_text(
                "Сначала выполните команду /start",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("🥧 Расходы по категориям", callback_data="chart_pie"),
             InlineKeyboardButton("📈 Тренд расходов", callback_data="chart_trends")],
            [InlineKeyboardButton("📊 Сравнение по месяцам", callback_data="chart_monthly")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"📊 **Графики и статистика**\n\n"
            f"Выберите тип графика для просмотра:\n\n"
            f"🥧 **Расходы по категориям** - круговая диаграмма\n"
            f"📈 **Тренд расходов** - динамика по дням\n"
            f"📊 **Сравнение по месяцам** - столбчатая диаграмма\n\n"
            f"Для каждого графика можно выбрать период отображения."
        )
        
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()

async def handle_charts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для графиков"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query, "Сначала выполните команду /start", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if data == "chart_pie":
            context.user_data['chart_type'] = 'pie'
            await _show_period_selection(query, "🥧 Расходы по категориям")
        elif data == "chart_trends":
            context.user_data['chart_type'] = 'trends'
            await _show_period_selection(query, "📈 Тренд расходов")
        elif data == "chart_monthly":
            context.user_data['chart_type'] = 'monthly'
            await _show_monthly_period_selection(query)
        elif data.startswith("period_"):
            await _handle_period_selection(query, context, data)
        elif data.startswith("monthly_"):
            await _handle_monthly_period_selection(query, context, data)
        
    finally:
        db.close()

async def _show_period_selection(query, chart_name: str):
    """Показать выбор периода для ежедневных графиков"""
    keyboard = [
        [InlineKeyboardButton("📅 7 дней", callback_data="period_7")],
        [InlineKeyboardButton("📅 14 дней", callback_data="period_14")],
        [InlineKeyboardButton("📅 30 дней", callback_data="period_30")],
        [InlineKeyboardButton("📅 60 дней", callback_data="period_60")],
        [InlineKeyboardButton("📅 90 дней", callback_data="period_90")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"📊 **{chart_name}**\n\n"
        f"Выберите период для отображения:"
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _show_monthly_period_selection(query):
    """Показать выбор периода для месячных графиков"""
    keyboard = [
        [InlineKeyboardButton("📅 3 месяца", callback_data="monthly_3")],
        [InlineKeyboardButton("📅 6 месяцев", callback_data="monthly_6")],
        [InlineKeyboardButton("📅 12 месяцев", callback_data="monthly_12")],
        [InlineKeyboardButton("📅 24 месяца", callback_data="monthly_24")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        f"📊 **Сравнение по месяцам**\n\n"
        f"Выберите период для отображения:"
    )
    
    await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')

async def _handle_period_selection(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка выбора периода для ежедневных графиков"""
    period_days = int(data.replace("period_", ""))
    chart_type = context.user_data.get('chart_type')
    
    if not chart_type:
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        await safe_edit_message(query, "❌ Ошибка: тип графика не определен", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    await safe_edit_message(query, "⏳ Генерирую график...")
    
    chart_service = ChartService()
    
    try:
        if chart_type == 'pie':
            chart_buffer = chart_service.generate_category_pie_chart(
                user_id=query.from_user.id,
                period_days=period_days
            )
            chart_name = "расходов по категориям"
        elif chart_type == 'trends':
            chart_buffer = chart_service.generate_spending_trends_chart(
                user_id=query.from_user.id,
                period_days=period_days
            )
            chart_name = "тренда расходов"
        else:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query, "❌ Неизвестный тип графика", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        if chart_buffer:
            # Отправляем график
            await query.message.reply_photo(
                photo=chart_buffer,
                caption=f"📊 График {chart_name} за {period_days} дней"
            )
            
            # Завершаем взаимодействие
            await safe_delete_message(query)
        else:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query, 
                f"❌ Не удалось создать график.\n"
                f"Возможно, нет данных за выбранный период ({period_days} дней).",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    except Exception as e:
        logger.error(f"Ошибка при создании графика: {e}")
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        await safe_edit_message(query,
            f"❌ Произошла ошибка при создании графика.\n"
            f"Попробуйте позже или выберите другой период.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    finally:
        context.user_data.pop('chart_type', None)

async def _handle_monthly_period_selection(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка выбора периода для месячных графиков"""
    months = int(data.replace("monthly_", ""))
    
    await safe_edit_message(query, "⏳ Генерирую график...")
    
    chart_service = ChartService()
    
    try:
        chart_buffer = chart_service.generate_monthly_comparison_chart(
            user_id=query.from_user.id,
            months=months
        )
        
        if chart_buffer:
            # Отправляем график
            await query.message.reply_photo(
                photo=chart_buffer,
                caption=f"📊 График сравнения расходов по месяцам за {months} мес."
            )
            
            # Завершаем взаимодействие
            await safe_delete_message(query)
        else:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query,
                f"❌ Не удалось создать график.\n"
                f"Возможно, нет данных за выбранный период ({months} мес.).",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    except Exception as e:
        logger.error(f"Ошибка при создании месячного графика: {e}")
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        await safe_edit_message(query,
            f"❌ Произошла ошибка при создании графика.\n"
            f"Попробуйте позже или выберите другой период.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# Для совместимости с существующим кодом
async def charts_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /charts через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query, "Сначала выполните команду /start", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        keyboard = [
            [InlineKeyboardButton("🥧 Расходы по категориям", callback_data="chart_pie"),
             InlineKeyboardButton("📈 Тренд расходов", callback_data="chart_trends")],
            [InlineKeyboardButton("📊 Сравнение по месяцам", callback_data="chart_monthly")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"📊 **Графики и статистика**\n\n"
            f"Выберите тип графика для просмотра:\n\n"
            f"🥧 **Расходы по категориям** - круговая диаграмма\n"
            f"📈 **Тренд расходов** - динамика по дням\n"
            f"📊 **Сравнение по месяцам** - столбчатая диаграмма\n\n"
            f"Для каждого графика можно выбрать период отображения."
        )
        
        await safe_edit_message(query, message, reply_markup=reply_markup, parse_mode='Markdown')
        
    finally:
        db.close()


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Алиас для команды графиков"""
    await charts_command(update, context)

async def stats_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Алиас для обработки callback статистики"""
    await charts_command_callback(update, context)

async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Алиас для обработки callback графиков"""
    await handle_charts_callback(update, context)