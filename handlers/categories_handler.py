import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit
from utils.telegram_utils import safe_edit_message, safe_answer_callback

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
            emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
            keyboard.append([InlineKeyboardButton(
                f"{emoji} {category.name}",
                callback_data=f"cat_view_{category.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📁 **Управление категориями**\n\n"
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
            keyboard = [
                [InlineKeyboardButton("❌ Отмена", callback_data="cat_back")]
            ]
            await query.edit_message_text(
                "📝 **Добавление новой категории**\n\n"
                "Отправьте название новой категории:\n\n"
                "💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
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
            keyboard.append([InlineKeyboardButton("😊 Изменить смайлик", callback_data=f"cat_edit_emoji_{category_id}")])
            if not category.is_default:
                keyboard.append([InlineKeyboardButton("🗑 Удалить категорию", callback_data=f"cat_delete_confirm_{category_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
            await query.edit_message_text(
                f"{category_emoji} **{category.name}**\n\n"
                f"💸 Потрачено: {spent_sum:.2f} EUR\n"
                f"💰 Получено: {earned_sum:.2f} EUR\n"
                f"📊 {limit_text}\n\n"
                f"Транзакций: {len(total_spent + total_earned)}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif data.startswith("cat_delete_confirm_"):
            category_id = int(data.split("_")[3])
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
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"cat_view_{category_id}")]]
                await query.edit_message_text(
                    f"❌ **Удаление невозможно**\n\n"
                    f"Категория '{category.name}' содержит {transactions_count} транзакций и не может быть удалена.\n\n"
                    f"Сначала удалите все транзакции этой категории.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                return
            
            # Показываем подтверждение удаления
            keyboard = [
                [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"cat_delete_final_{category_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"cat_view_{category_id}")]
            ]
            
            await query.edit_message_text(
                f"⚠️ **Подтверждение удаления**\n\n"
                f"Вы уверены, что хотите удалить категорию '{category.name}'?\n\n"
                f"Это действие нельзя отменить.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("cat_delete_final_"):
            category_id = int(data.split("_")[3])
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            # Удаляем лимиты для этой категории
            db.query(Limit).filter(Limit.category_id == category_id).delete()
            
            # Удаляем категорию
            category_name = category.name
            db.delete(category)
            db.commit()
            
            keyboard = [[InlineKeyboardButton("🔙 К категориям", callback_data="cat_back")]]
            await query.edit_message_text(
                f"✅ **Категория удалена**\n\n"
                f"Категория '{category_name}' успешно удалена.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("cat_edit_emoji_"):
            category_id = int(data.split("_")[3])
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            # Сохраняем ID категории для редактирования
            context.user_data['editing_category_emoji'] = category_id
            
            # Показываем выбор смайлика
            from services.emoji_service import EmojiService
            emoji_service = EmojiService()
            
            # Получаем рекомендуемый смайлик
            suggested_emoji = emoji_service.get_emoji_by_category_name(category.name)
            current_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
            
            # Создаем клавиатуру с смайликами
            keyboard = []
            
            # Первая кнопка - текущий смайлик
            keyboard.append([InlineKeyboardButton(
                f"✅ {current_emoji} (текущий)", 
                callback_data=f"cat_emoji_select_{current_emoji}"
            )])
            
            # Вторая кнопка - рекомендуемый смайлик (если отличается от текущего)
            if suggested_emoji != current_emoji:
                keyboard.append([InlineKeyboardButton(
                    f"💡 {suggested_emoji} (рекомендуется)", 
                    callback_data=f"cat_emoji_select_{suggested_emoji}"
                )])
            
            # Получаем клавиатуру смайликов для категории
            emoji_keyboard = emoji_service.get_emoji_keyboard_for_category(category.name)
            
            # Добавляем смайлики в клавиатуру
            for emoji_row in emoji_keyboard:
                button_row = []
                for emoji in emoji_row:
                    if emoji != current_emoji and emoji != suggested_emoji:
                        button_row.append(InlineKeyboardButton(
                            emoji, 
                            callback_data=f"cat_emoji_select_{emoji}"
                        ))
                if button_row:
                    keyboard.append(button_row)
            
            # Кнопки управления
            keyboard.append([
                InlineKeyboardButton("📂 Больше смайликов", callback_data="cat_more_emojis"),
                InlineKeyboardButton("📁 По умолчанию", callback_data="cat_emoji_select_📁")
            ])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"cat_view_{category_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"😊 **Изменение смайлика для '{category.name}'**\n\n"
                f"Текущий смайлик: {current_emoji}\n"
                f"Рекомендуемый: {suggested_emoji}\n\n"
                "Выберите новый смайлик:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif data.startswith("cat_emoji_select_"):
            category_id = context.user_data.get('editing_category_emoji')
            if not category_id:
                await query.edit_message_text("❌ Сессия истекла. Попробуйте снова.")
                return
            
            selected_emoji = data.replace("cat_emoji_select_", "")
            
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            # Обновляем смайлик
            category.emoji = selected_emoji
            db.commit()
            
            # Очищаем временные данные
            context.user_data.pop('editing_category_emoji', None)
            
            await query.edit_message_text(
                f"✅ **Смайлик обновлен!**\n\n"
                f"Категория: {selected_emoji} {category.name}\n\n"
                f"Новый смайлик: {selected_emoji}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 К категории", callback_data=f"cat_view_{category_id}")
                ]]),
                parse_mode='Markdown'
            )
            
        elif data == "cat_more_emojis":
            category_id = context.user_data.get('editing_category_emoji')
            if not category_id:
                await query.edit_message_text("❌ Сессия истекла. Попробуйте снова.")
                return
            
            # Показываем больше смайликов
            from services.emoji_service import EmojiService
            emoji_service = EmojiService()
            popular_emojis = emoji_service.get_popular_emojis()
            
            # Создаем клавиатуру с популярными смайликами
            keyboard = []
            
            # Разбиваем на строки по 5 смайликов
            for i in range(0, len(popular_emojis), 5):
                row = []
                for emoji in popular_emojis[i:i+5]:
                    row.append(InlineKeyboardButton(
                        emoji, 
                        callback_data=f"cat_emoji_select_{emoji}"
                    ))
                keyboard.append(row)
            
            # Кнопка назад
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"cat_edit_emoji_{category_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            category_name = category.name if category else 'категории'
            await query.edit_message_text(
                f"😊 **Популярные смайлики для '{category_name}'**\n\n"
                "Выберите смайлик:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif data == "cat_back":
            context.user_data.pop('waiting_for_category', None)
            context.user_data.pop('editing_category_emoji', None)
            # Возвращаемся к списку категорий
            categories = db.query(Category).filter(Category.user_id == user.id).all()
            
            keyboard = []
            for category in categories:
                emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {category.name}",
                    callback_data=f"cat_view_{category.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📁 **Управление категориями**\n\n"
                "Выберите категорию для просмотра или добавьте новую:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    finally:
        db.close()


async def categories_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /categories через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        
        keyboard = []
        keyboard.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
        
        # Показать существующие категории
        for category in categories:
            category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
            keyboard.append([InlineKeyboardButton(
                f"{category_emoji} {category.name}",
                callback_data=f"cat_view_{category.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query,
            "📁 **Управление категориями**\n\n"
            "Выберите категорию для просмотра или редактирования:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()