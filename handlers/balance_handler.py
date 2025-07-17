import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User
from services.balance_service import BalanceService
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /balance"""
    user_id = update.effective_user.id
    balance_service = BalanceService()
    
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
        
        # Получаем все балансы пользователя
        balances = balance_service.get_all_balances(user.id)
        
        if not balances:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await update.message.reply_text(
                "💳 **Баланс**\n\n"
                "У вас пока нет транзакций.\n"
                "Добавьте доходы или расходы, чтобы увидеть баланс.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # Формируем сообщение с балансами
        message_text = "💳 **Ваш баланс**\n\n"
        
        for balance in balances:
            balance_emoji = "💰" if balance.amount >= 0 else "💸"
            message_text += f"{balance_emoji} {balance.amount:+.2f} {balance.currency}\n"
        
        # Добавляем информацию о том, что это общий баланс
        message_text += "\n📊 Это ваш общий баланс:\n"
        message_text += "• ➕ Доходы увеличивают баланс\n"
        message_text += "• ➖ Расходы уменьшают баланс\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Пересчитать", callback_data="balance_recalculate")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        await update.message.reply_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def balance_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /balance через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    balance_service = BalanceService()
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Получаем все балансы пользователя
        balances = balance_service.get_all_balances(user.id)
        
        if not balances:
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await safe_edit_message(query,
                "💳 **Баланс**\n\n"
                "У вас пока нет транзакций.\n"
                "Добавьте доходы или расходы, чтобы увидеть баланс.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # Формируем сообщение с балансами
        message_text = "💳 **Ваш баланс**\n\n"
        
        for balance in balances:
            balance_emoji = "💰" if balance.amount >= 0 else "💸"
            message_text += f"{balance_emoji} {balance.amount:+.2f} {balance.currency}\n"
        
        # Добавляем информацию о том, что это общий баланс
        message_text += "\n📊 Это ваш общий баланс:\n"
        message_text += "• ➕ Доходы увеличивают баланс\n"
        message_text += "• ➖ Расходы уменьшают баланс\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Пересчитать", callback_data="balance_recalculate")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        await safe_edit_message(query,
            message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def handle_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для баланса"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    if query.data == "balance_recalculate":
        balance_service = BalanceService()
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await safe_edit_message(query, "Сначала выполните команду /start")
                return
            
            # Пересчитываем баланс для всех валют
            # Сначала получаем все уникальные валюты из транзакций
            from database import Transaction
            currencies = db.query(Transaction.currency).filter(
                Transaction.user_id == user.id
            ).distinct().all()
            
            recalculated_balances = []
            for currency_tuple in currencies:
                currency = currency_tuple[0]
                balance = balance_service.recalculate_balance(user.id, currency)
                recalculated_balances.append(balance)
            
            # Показываем обновленный баланс
            if not recalculated_balances:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await safe_edit_message(query,
                    "💳 **Баланс пересчитан**\n\n"
                    "У вас пока нет транзакций.\n"
                    "Добавьте доходы или расходы, чтобы увидеть баланс.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
            
            # Формируем сообщение с пересчитанными балансами
            message_text = "💳 **Баланс пересчитан**\n\n"
            
            for balance in recalculated_balances:
                balance_emoji = "💰" if balance.amount >= 0 else "💸"
                message_text += f"{balance_emoji} {balance.amount:+.2f} {balance.currency}\n"
            
            message_text += "\n✅ Баланс обновлен на основе всех ваших транзакций"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Пересчитать еще раз", callback_data="balance_recalculate")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            
            await safe_edit_message(query,
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        finally:
            db.close()