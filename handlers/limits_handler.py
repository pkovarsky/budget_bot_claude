import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit
from utils.telegram_utils import safe_edit_message, safe_answer_callback

logger = logging.getLogger(__name__)


async def limits_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /limits"""
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
        
        # Получаем все лимиты пользователя
        limits = db.query(Limit).filter(Limit.user_id == user.id).all()
        
        keyboard = []
        
        if limits:
            keyboard.append([InlineKeyboardButton("📋 Мои лимиты", callback_data="limits_view")])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить лимит", callback_data="limits_add"),
             InlineKeyboardButton("✏️ Изменить лимит", callback_data="limits_edit")],
            [InlineKeyboardButton("🗑 Удалить лимит", callback_data="limits_delete")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "💳 **Управление лимитами**\n\n"
            "Лимиты помогают контролировать расходы по категориям.\n"
            "Вы получите уведомление при превышении 80% и 100% лимита.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    finally:
        db.close()


async def limits_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /limits через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Получаем все лимиты пользователя
        limits = db.query(Limit).filter(Limit.user_id == user.id).all()
        
        keyboard = []
        
        if limits:
            keyboard.append([InlineKeyboardButton("📋 Мои лимиты", callback_data="limits_view")])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить лимит", callback_data="limits_add"),
             InlineKeyboardButton("🗑 Удалить лимит", callback_data="limits_delete")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query,
            "💳 **Управление лимитами**\n\n"
            "Лимиты помогают контролировать расходы по категориям.\n"
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
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
            await query.edit_message_text(
                "Сначала выполните команду /start",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        if data == "limits_view":
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            if not limits:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "У вас пока нет установленных лимитов.",
                    reply_markup=reply_markup
                )
                return
            
            message = "📋 **Ваши лимиты:**\n\n"
            
            for limit in limits:
                category = db.query(Category).filter(Category.id == limit.category_id).first()
                
                # Считаем потраченную сумму за соответствующий период
                now = datetime.now()
                
                if limit.period == 'weekly':
                    # Неделя - последние 7 дней
                    period_start = now - timedelta(days=7)
                elif limit.period == 'custom' and limit.end_date:
                    # Кастомный период - от создания лимита до конечной даты
                    period_start = limit.created_at
                else:
                    # Месяц - текущий месяц
                    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                spent = db.query(Transaction).filter(
                    Transaction.user_id == user.id,
                    Transaction.category_id == limit.category_id,
                    Transaction.amount < 0,
                    Transaction.created_at >= period_start,
                    Transaction.currency == limit.currency
                ).all()
                
                total_spent = sum(abs(t.amount) for t in spent)
                percentage = (total_spent / limit.amount * 100) if limit.amount > 0 else 0
                
                status_emoji = "🔴" if percentage >= 100 else "🟡" if percentage >= 80 else "🟢"
                
                if limit.period == "weekly":
                    period_text = "неделю"
                elif limit.period == "custom" and limit.end_date:
                    period_text = f"до {limit.end_date.strftime('%d.%m.%Y')}"
                else:
                    period_text = "месяц"
                
                message += f"{status_emoji} **{category.name}**\n"
                message += f"   Лимит: {limit.amount} {limit.currency} за {period_text}\n"
                message += f"   Потрачено: {total_spent:.2f} {limit.currency} ({percentage:.1f}%)\n"
                message += f"   Осталось: {limit.amount - total_spent:.2f} {limit.currency} ({100 - percentage:.1f}%)\n\n"

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
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
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
                await query.edit_message_text(
                    "Для всех категорий уже установлены лимиты.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
                await query.edit_message_text(
                    "📝 **Добавление лимита**\n\n"
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
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Категория не найдена.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # Показываем выбор периода
            keyboard = [
                [InlineKeyboardButton("📅 Еженедельно", callback_data=f"limits_period_weekly_{category_id}")],
                [InlineKeyboardButton("📊 Ежемесячно", callback_data=f"limits_period_monthly_{category_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="limits_add")]
            ]
            
            await query.edit_message_text(
                f"📝 **Настройка лимита для {category.name}**\n\n"
                f"Выберите период для лимита:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_period_"):
            parts = data.split("_")
            period = parts[2]  # weekly или monthly
            category_id = int(parts[3])
            
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Категория не найдена.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            period_text = "неделю" if period == "weekly" else "месяц"
            
            keyboard = [
                [InlineKeyboardButton("❌ Отмена", callback_data="limits_add")]
            ]
            await query.edit_message_text(
                f"📝 **Установка лимита для '{category.name}' ({period_text})**\n\n"
                "Отправьте сумму лимита с валютой, например:\n"
                "`500 EUR` или `300 USD`\n\n"
                "💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            context.user_data['waiting_for_limit'] = {
                'category_id': category_id,
                'period': period
            }
            
        elif data == "limits_edit":
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            if not limits:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
                await query.edit_message_text(
                    "У вас нет лимитов для редактирования.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            keyboard = []
            for limit in limits:
                category = db.query(Category).filter(Category.id == limit.category_id).first()
                period_text = "неделю" if limit.period == "weekly" else "месяц"
                keyboard.append([InlineKeyboardButton(
                    f"✏️ {category.name} ({limit.amount} {limit.currency}/{period_text})",
                    callback_data=f"limits_edit_select_{limit.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
            
            await query.edit_message_text(
                "✏️ **Редактирование лимита**\n\n"
                "Выберите лимит для изменения:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data == "limits_delete":
            limits = db.query(Limit).filter(Limit.user_id == user.id).all()
            
            if not limits:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]]
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
                    callback_data=f"limits_delete_confirm_{limit.id}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
            
            await query.edit_message_text(
                "🗑 **Удаление лимита**\n\n"
                "Выберите лимит для удаления:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_delete_confirm_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            # Показываем подтверждение удаления
            keyboard = [
                [InlineKeyboardButton("🗑 Да, удалить", callback_data=f"limits_delete_final_{limit_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="limits_delete")]
            ]
            
            await query.edit_message_text(
                f"⚠️ **Подтверждение удаления**\n\n"
                f"Вы уверены, что хотите удалить лимит для категории '{category.name}'?\n\n"
                f"Лимит: {limit.amount} {limit.currency}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_delete_final_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            db.delete(limit)
            db.commit()
            
            keyboard = [[InlineKeyboardButton("🔙 К лимитам", callback_data="settings_back")]]
            await query.edit_message_text(
                f"✅ **Лимит удален**\n\n"
                f"Лимит для категории '{category.name}' успешно удален.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_edit_select_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            period_text = "неделю" if limit.period == "weekly" else "месяц"
            
            keyboard = [
                [InlineKeyboardButton("💰 Изменить сумму", callback_data=f"limits_edit_amount_{limit_id}")],
                [InlineKeyboardButton("📅 Изменить период", callback_data=f"limits_edit_period_{limit_id}")],
                [InlineKeyboardButton("📅 Установить конкретную дату", callback_data=f"limits_edit_date_{limit_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="limits_edit")]
            ]
            
            await query.edit_message_text(
                f"✏️ **Редактирование лимита**\n\n"
                f"Категория: {category.name}\n"
                f"Текущий лимит: {limit.amount} {limit.currency} за {period_text}\n\n"
                f"Что хотите изменить?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_edit_amount_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"limits_edit_select_{limit_id}")]]
            await query.edit_message_text(
                f"💰 **Изменение суммы лимита**\n\n"
                f"Категория: {category.name}\n"
                f"Текущий лимит: {limit.amount} {limit.currency}\n\n"
                f"Отправьте новую сумму с валютой, например:\n"
                f"`600 EUR` или `400 USD`\n\n"
                f"💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            context.user_data['editing_limit'] = {
                'limit_id': limit_id,
                'field': 'amount'
            }
            
        elif data.startswith("limits_edit_period_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            keyboard = [
                [InlineKeyboardButton("📅 Еженедельно", callback_data=f"limits_period_update_weekly_{limit_id}")],
                [InlineKeyboardButton("📊 Ежемесячно", callback_data=f"limits_period_update_monthly_{limit_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data=f"limits_edit_select_{limit_id}")]
            ]
            
            current_period = "неделю" if limit.period == "weekly" else "месяц"
            await query.edit_message_text(
                f"📅 **Изменение периода лимита**\n\n"
                f"Категория: {category.name}\n"
                f"Текущий период: {current_period}\n\n"
                f"Выберите новый период:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data.startswith("limits_edit_date_"):
            limit_id = int(data.split("_")[3])
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data=f"limits_edit_select_{limit_id}")]]
            await query.edit_message_text(
                f"📅 **Установка конкретной даты**\n\n"
                f"Категория: {category.name}\n"
                f"Текущий лимит: {limit.amount} {limit.currency}\n\n"
                f"Введите дату в формате ДД.ММ.ГГГГ, например:\n"
                f"`31.07.2024` или `15.08.2024`\n\n"
                f"Лимит будет действовать до указанной даты\n\n"
                f"💡 Или отправьте /cancel для отмены",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            context.user_data['editing_limit'] = {
                'limit_id': limit_id,
                'field': 'date'
            }
            
        elif data.startswith("limits_period_update_"):
            parts = data.split("_")
            new_period = parts[3]  # weekly или monthly
            limit_id = int(parts[4])
            
            limit = db.query(Limit).filter(
                Limit.id == limit_id,
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
                await query.edit_message_text(
                    "Лимит не найден.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            # Обновляем период
            limit.period = new_period
            db.commit()
            
            period_text = "неделю" if new_period == "weekly" else "месяц"
            keyboard = [[InlineKeyboardButton("🔙 К лимитам", callback_data="settings_back")]]
            await query.edit_message_text(
                f"✅ **Период лимита обновлен**\n\n"
                f"Категория: {category.name}\n"
                f"Новый период: {period_text}\n"
                f"Лимит: {limit.amount} {limit.currency} за {period_text}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        elif data == "limits_back":
            context.user_data.pop('waiting_for_limit', None)
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
                "💳 **Управление лимитами**\n\n"
                "Лимиты помогают контролировать расходы по категориям.\n"
                "Вы получите уведомление при превышении 80% и 100% лимита.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    finally:
        db.close()


async def limits_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /limits через callback"""
    query = update.callback_query
    await safe_answer_callback(query)
    
    user_id = update.effective_user.id
    
    db = get_db_session()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await safe_edit_message(query, "Сначала выполните команду /start")
            return
        
        # Получаем категории пользователя
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        
        if not categories:
            await safe_edit_message(query, 
                "❌ У вас нет категорий для установки лимитов.\n"
                "Сначала добавьте категории командой /categories"
            )
            return
        
        # Получаем существующие лимиты
        limits = db.query(Limit).filter(Limit.user_id == user.id).all()
        
        keyboard = []
        
        if limits:
            keyboard.append([InlineKeyboardButton("📋 Мои лимиты", callback_data="limits_view")])
        
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить лимит", callback_data="limits_add"),
             InlineKeyboardButton("✏️ Изменить лимит", callback_data="limits_edit")],
            [InlineKeyboardButton("🗑 Удалить лимит", callback_data="limits_delete")]
        ])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="settings_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(query,
            "💰 **Управление лимитами**\n\n"
            "Лимиты помогают контролировать расходы по категориям.\n"
            "Вы получите уведомление при превышении 80% и 100% лимита.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()