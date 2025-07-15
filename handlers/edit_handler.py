import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction
from utils.localization import get_message

logger = logging.getLogger(__name__)


async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /edit для редактирования транзакций"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text(get_message("start_first", user.language if user else "ru"))
            return
        
        # Создаем клавиатуру выбора периода
        keyboard = [
            [InlineKeyboardButton(get_message("today", user.language), callback_data="edit_today")],
            [InlineKeyboardButton(get_message("this_week", user.language), callback_data="edit_week")],
            [InlineKeyboardButton(get_message("this_month", user.language), callback_data="edit_month")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"{get_message('edit_transactions', user.language)}\n\n{get_message('select_period', user.language)}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для редактирования"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text(get_message("start_first", user.language if user else "ru"))
            return
        
        # Определяем период
        now = datetime.now()
        if data == "edit_today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = get_message("today", user.language)
        elif data == "edit_week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_name = get_message("this_week", user.language)
        elif data == "edit_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_name = get_message("this_month", user.language)
        elif data.startswith("edit_transaction_"):
            # Редактирование конкретной транзакции
            transaction_id = int(data.split("_")[2])
            await show_transaction_edit_options(query, user, transaction_id, db)
            return
        elif data.startswith("edit_amount_"):
            # Изменение суммы
            transaction_id = int(data.split("_")[2])
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"edit_transaction_{transaction_id}")]]
            await query.edit_message_text(
                f"{get_message('enter_new_amount', user.language)}\n\n"
                f"💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            context.user_data['editing_transaction'] = transaction_id
            return
        elif data.startswith("delete_transaction_"):
            # Удаление транзакции - запрос подтверждения
            transaction_id = int(data.split("_")[2])
            
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user.id
            ).first()
            
            if not transaction:
                await query.edit_message_text("Транзакция не найдена.")
                return
                
            # Показываем подтверждение удаления
            keyboard = [
                [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"delete_confirm_{transaction_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"edit_transaction_{transaction_id}")]
            ]
            
            await query.edit_message_text(
                f"⚠️ **Подтверждение удаления**\n\n"
                f"Вы уверены, что хотите удалить транзакцию?\n\n"
                f"📝 {transaction.description}\n"
                f"💰 {transaction.amount} {transaction.currency}\n\n"
                f"Это действие нельзя отменить.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
            
        elif data.startswith("delete_confirm_"):
            # Подтвержденное удаление транзакции
            transaction_id = int(data.split("_")[2])
            await delete_transaction(query, user, transaction_id, db)
            return
        elif data == "edit_back":
            context.user_data.pop('editing_transaction', None)
            await edit_command(update, context)
            return
        else:
            return
        
        # Получаем транзакции за период
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user.id,
            Transaction.created_at >= start_date
        ).order_by(Transaction.created_at.desc()).limit(10).all()
        
        if not transactions:
            await query.edit_message_text(
                f"{period_name}\n\n{get_message('no_transactions', user.language)}",
                parse_mode='Markdown'
            )
            return
        
        # Создаем список транзакций для редактирования
        keyboard = []
        for transaction in transactions:
            category = db.query(Category).filter(Category.id == transaction.category_id).first()
            
            # Форматируем строку транзакции
            amount_str = f"{abs(transaction.amount)} {transaction.currency}"
            type_emoji = "💰" if transaction.amount > 0 else "💸"
            date_str = transaction.created_at.strftime("%d.%m")
            
            button_text = f"{type_emoji} {amount_str} - {category.name if category else 'Unknown'} ({date_str})"
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"edit_transaction_{transaction.id}"
                )
            ])
        
        # Кнопка "Назад"
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="edit_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{period_name}\n\n{get_message('select_transaction', user.language)}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def show_transaction_edit_options(query, user, transaction_id: int, db):
    """Показать опции редактирования для конкретной транзакции"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    ).first()
    
    if not transaction:
        await query.edit_message_text("Транзакция не найдена.")
        return
    
    category = db.query(Category).filter(Category.id == transaction.category_id).first()
    
    # Информация о транзакции
    amount_str = f"{abs(transaction.amount)} {transaction.currency}"
    type_emoji = "💰" if transaction.amount > 0 else "💸"
    date_str = transaction.created_at.strftime("%d.%m.%Y %H:%M")
    
    info_text = (
        f"{type_emoji} **{amount_str}**\n"
        f"📁 {category.name if category else 'Unknown'}\n"
        f"📝 {transaction.description}\n"
        f"📅 {date_str}"
    )
    
    # Кнопки редактирования
    keyboard = [
        [InlineKeyboardButton(
            get_message("edit_amount", user.language), 
            callback_data=f"edit_amount_{transaction_id}"
        )],
        [InlineKeyboardButton(
            get_message("delete_transaction", user.language), 
            callback_data=f"delete_transaction_{transaction_id}"
        )],
        [InlineKeyboardButton("🔙 Назад", callback_data="edit_back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        info_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def delete_transaction(query, user, transaction_id: int, db):
    """Удалить транзакцию"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user.id
    ).first()
    
    if not transaction:
        await query.edit_message_text("Транзакция не найдена.")
        return
    
    # Сохраняем информацию о транзакции для сообщения
    description = transaction.description
    amount = transaction.amount
    currency = transaction.currency
    
    db.delete(transaction)
    db.commit()
    
    keyboard = [[InlineKeyboardButton("🔙 К редактированию", callback_data="edit_back")]]
    await query.edit_message_text(
        f"✅ **Транзакция удалена**\n\n"
        f"📝 {description}\n"
        f"💰 {amount} {currency}\n\n"
        f"Транзакция успешно удалена.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_new_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода новой суммы"""
    if 'editing_transaction' not in context.user_data:
        return
    
    transaction_id = context.user_data['editing_transaction']
    user_id = update.effective_user.id
    
    try:
        new_amount = float(update.message.text.replace(',', '.'))
        if new_amount <= 0:
            await update.message.reply_text("Сумма должна быть больше нуля.")
            return
    except ValueError:
        await update.message.reply_text("Некорректная сумма. Введите число.")
        return
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id
        ).first()
        
        if not transaction:
            await update.message.reply_text("Транзакция не найдена.")
            return
        
        # Сохраняем знак (доход/расход)
        is_income = transaction.amount > 0
        transaction.amount = new_amount if is_income else -new_amount
        
        db.commit()
        
        await update.message.reply_text(
            f"✅ {get_message('amount_updated', user.language)}: {new_amount} {transaction.currency}"
        )
        
    finally:
        db.close()
        context.user_data.pop('editing_transaction', None)