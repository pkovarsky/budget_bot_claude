import logging
import pandas as pd
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /export"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        # Получаем все транзакции пользователя
        transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
        
        if not transactions:
            await update.message.reply_text("У вас нет транзакций для экспорта.")
            return
            
        await update.message.reply_text("📊 Подготавливаю экспорт данных...")
        
        # Создаем DataFrame для экспорта
        data = []
        for transaction in transactions:
            category = db.query(Category).filter(Category.id == transaction.category_id).first()
            
            data.append({
                'Дата': transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Тип': 'Доход' if transaction.amount > 0 else 'Расход',
                'Сумма': abs(transaction.amount),
                'Валюта': transaction.currency,
                'Категория': category.name if category else 'Неизвестно',
                'Описание': transaction.description
            })
        
        df = pd.DataFrame(data)
        
        # Создаем Excel файл в памяти
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Основной лист с транзакциями
            df.to_excel(writer, sheet_name='Транзакции', index=False)
            
            # Лист со статистикой
            stats_data = []
            
            # Общая статистика по валютам
            stats_data.append({
                'Показатель': 'Общий доход',
                'EUR': df[(df['Тип'] == 'Доход') & (df['Валюта'] == 'EUR')]['Сумма'].sum(),
                'USD': df[(df['Тип'] == 'Доход') & (df['Валюта'] == 'USD')]['Сумма'].sum()
            })
            
            stats_data.append({
                'Показатель': 'Общие расходы',
                'EUR': df[(df['Тип'] == 'Расход') & (df['Валюта'] == 'EUR')]['Сумма'].sum(),
                'USD': df[(df['Тип'] == 'Расход') & (df['Валюта'] == 'USD')]['Сумма'].sum()
            })
            
            # Статистика по категориям
            category_stats = df[df['Тип'] == 'Расход'].groupby('Категория')['Сумма'].sum().reset_index()
            category_stats = category_stats.sort_values('Сумма', ascending=False)
            
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='Статистика', index=False)
            
            if not category_stats.empty:
                category_stats.to_excel(writer, sheet_name='По категориям', index=False)
        
        excel_buffer.seek(0)
        
        # Создаем имя файла
        current_date = datetime.now().strftime('%Y-%m-%d')
        filename = f"budget_export_{current_date}.xlsx"
        
        # Отправляем файл пользователю
        await update.message.reply_document(
            document=excel_buffer.getvalue(),
            filename=filename,
            caption=f"📊 **Экспорт данных**\n\n"
                    f"Файл содержит все ваши транзакции и статистику.\n"
                    f"Количество транзакций: {len(transactions)}\n"
                    f"Дата экспорта: {current_date}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте: {e}")
        await update.message.reply_text(
            "Произошла ошибка при создании экспорта. Попробуйте позже."
        )
    finally:
        db.close()


async def export_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /export через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query,
        "📤 **Экспорт данных**\n\n"
        "Экспорт данных пока доступен только через команду /export\n\n"
        "Используйте команду /export для получения Excel файла с вашими транзакциями.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )