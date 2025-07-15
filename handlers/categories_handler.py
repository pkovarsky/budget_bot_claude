import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit

logger = logging.getLogger(__name__)


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /categories"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        
        if not categories:
            await update.message.reply_text("У вас нет категорий. Используйте кнопку для добавления.")
        
        keyboard = []
        for category in categories:
            keyboard.append([InlineKeyboardButton(
                f"📁 {category.name}",
                callback_data=f"cat_view_{category.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📁 **Управление категориями**\\n\\n"
            "Выберите категорию для просмотра или добавьте новую:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def handle_categories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для управления категориями"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("Сначала выполните команду /start")
            return
        
        if data == "cat_add":
            await query.edit_message_text(
                "📝 **Добавление новой категории**\\n\\n"
                "Отправьте название новой категории:"
            )
            context.user_data['waiting_for_category'] = True
            
        elif data.startswith("cat_view_"):
            category_id = int(data.split("_")[2])
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            # Статистика по категории
            total_spent = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.category_id == category_id,
                Transaction.amount < 0
            ).all()
            
            total_earned = db.query(Transaction).filter(
                Transaction.user_id == user.id,
                Transaction.category_id == category_id,
                Transaction.amount > 0
            ).all()
            
            spent_sum = sum(abs(t.amount) for t in total_spent)
            earned_sum = sum(t.amount for t in total_earned)
            
            # Лимит
            limit = db.query(Limit).filter(
                Limit.user_id == user.id,
                Limit.category_id == category_id
            ).first()
            
            limit_text = f"Лимит: {limit.amount} {limit.currency}" if limit else "Лимит не установлен"
            
            keyboard = []
            if not category.is_default:
                keyboard.append([InlineKeyboardButton("🗑 Удалить категорию", callback_data=f"cat_delete_{category_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="cat_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📁 **{category.name}**\\n\\n"
                f"💸 Потрачено: {spent_sum:.2f} EUR\\n"
                f"💰 Получено: {earned_sum:.2f} EUR\\n"
                f"📊 {limit_text}\\n\\n"
                f"Транзакций: {len(total_spent + total_earned)}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif data.startswith("cat_delete_"):
            category_id = int(data.split("_")[2])
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            if category.is_default:
                await query.edit_message_text("Нельзя удалить базовую категорию.")
                return
            
            # Проверяем, есть ли транзакции в этой категории
            transactions_count = db.query(Transaction).filter(
                Transaction.category_id == category_id
            ).count()
            
            if transactions_count > 0:
                await query.edit_message_text(
                    f"Категория '{category.name}' содержит {transactions_count} транзакций и не может быть удалена."
                )
                return
            
            # Удаляем лимиты для этой категории
            db.query(Limit).filter(Limit.category_id == category_id).delete()
            
            # Удаляем категорию
            db.delete(category)
            db.commit()
            
            await query.edit_message_text(
                f"✅ Категория '{category.name}' удалена."
            )
            
        elif data == "cat_back":
            # Возвращаемся к списку категорий
            categories = db.query(Category).filter(Category.user_id == user.id).all()
            
            keyboard = []
            for category in categories:
                keyboard.append([InlineKeyboardButton(
                    f"📁 {category.name}",
                    callback_data=f"cat_view_{category.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📁 **Управление категориями**\\n\\n"
                "Выберите категорию для просмотра или добавьте новую:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    finally:
        db.close()