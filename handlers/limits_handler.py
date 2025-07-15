import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit

logger = logging.getLogger(__name__)


async def limits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /limits"""
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("Сначала выполните команду /start")
            return
        
        # Получаем все лимиты пользователя
        limits = db.query(Limit).filter(Limit.user_id == user.id).all()
        
        keyboard = []
        
        if limits:
            keyboard.append([InlineKeyboardButton("📋 Мои лимиты", callback_data="limits_view")])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить лимит", callback_data="limits_add")],
            [InlineKeyboardButton("🗑 Удалить лимит", callback_data="limits_delete")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💳 **Управление лимитами**\\n\\n"
            "Лимиты помогают контролировать расходы по категориям.\\n"
            "Вы получите уведомление при превышении 80% и 100% лимита.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def handle_limits_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка callback-кнопок для лимитов"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await query.edit_message_text("Сначала выполните команду /start")
            return
        
        if data == "limits_view":
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            if not limits:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="limits_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "У вас пока нет установленных лимитов.",
                    reply_markup=reply_markup
                )
                return
            
            message = "📋 **Ваши лимиты:**\\n\\n"
            
            for limit in limits:
                category = db.query(Category).filter(Category.id == limit.category_id).first()
                
                # Считаем потраченную сумму за текущий месяц
                now = datetime.now()
                start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                spent = db.query(Transaction).filter(
                    Transaction.user_id == user.id,
                    Transaction.category_id == limit.category_id,
                    Transaction.amount < 0,
                    Transaction.created_at >= start_of_month,
                    Transaction.currency == limit.currency
                ).all()
                
                total_spent = sum(abs(t.amount) for t in spent)
                percentage = (total_spent / limit.amount * 100) if limit.amount > 0 else 0
                
                status_emoji = "🔴" if percentage >= 100 else "🟡" if percentage >= 80 else "🟢"
                
                message += f"{status_emoji} **{category.name}**\\n"
                message += f"   Лимит: {limit.amount} {limit.currency}\\n"
                message += f"   Потрачено: {total_spent:.2f} {limit.currency} ({percentage:.1f}%)\\n\\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="limits_back")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        elif data == "limits_add":
            categories = db.query(Category).filter(Category.user_id == user.id).all()
            
            keyboard = []
            for category in categories:
                # Проверяем, есть ли уже лимит для этой категории
                existing_limit = db.query(Limit).filter(
                    Limit.user_id == user.id,
                    Limit.category_id == category.id
                ).first()
                
                if not existing_limit:
                    keyboard.append([InlineKeyboardButton(
                        f"📁 {category.name}",
                        callback_data=f"limits_add_cat_{category.id}"
                    )])
            
            if not keyboard:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="limits_back")]]
                await query.edit_message_text(
                    "Для всех категорий уже установлены лимиты.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="limits_back")])
                await query.edit_message_text(
                    "📝 **Добавление лимита**\\n\\n"
                    "Выберите категорию для установки лимита:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        elif data.startswith("limits_add_cat_"):
            category_id = int(data.split("_")[3])
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            await query.edit_message_text(
                f"📝 **Установка лимита для '{category.name}'**\\n\\n"
                "Отправьте сумму лимита с валютой, например:\\n"
                "`500 EUR` или `10000 RUB` или `300 USD`",
                parse_mode='Markdown'
            )
            
            context.user_data['waiting_for_limit'] = category_id
            
        elif data == "limits_delete":
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            if not limits:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="limits_back")]]
                await query.edit_message_text(
                    "У вас нет лимитов для удаления.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            keyboard = []
            for limit in limits:
                category = db.query(Category).filter(Category.id == limit.category_id).first()
                keyboard.append([InlineKeyboardButton(
                    f"🗑 {category.name} ({limit.amount} {limit.currency})",
                    callback_data=f"limits_delete_{limit.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="limits_back")])
            
            await query.edit_message_text(
                "🗑 **Удаление лимита**\\n\\n"
                "Выберите лимит для удаления:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_delete_"):
            limit_id = int(data.split("_")[2])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                await query.edit_message_text("Лимит не найден.")
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            db.delete(limit)
            db.commit()
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="limits_back")]]
            await query.edit_message_text(
                f"✅ Лимит для категории '{category.name}' удален.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif data == "limits_back":
            # Возвращаемся к главному меню лимитов
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            keyboard = []
            
            if limits:
                keyboard.append([InlineKeyboardButton("📋 Мои лимиты", callback_data="limits_view")])
            
            keyboard.extend([
                [InlineKeyboardButton("➕ Добавить лимит", callback_data="limits_add")],
                [InlineKeyboardButton("🗑 Удалить лимит", callback_data="limits_delete")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "💳 **Управление лимитами**\\n\\n"
                "Лимиты помогают контролировать расходы по категориям.\\n"
                "Вы получите уведомление при превышении 80% и 100% лимита.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    finally:
        db.close()