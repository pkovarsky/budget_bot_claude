import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit
from openai_service import OpenAIService
from utils.parsers import parse_transaction
from utils.localization import get_message

logger = logging.getLogger(__name__)


class EnhancedTransactionHandler:
    def __init__(self):
        self.openai_service = OpenAIService()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений для парсинга транзакций с улучшенным UI"""
        # Если ждем ввода названия категории
        if context.user_data.get('waiting_for_category'):
            await self.handle_new_category(update, context)
            return
            
        # Если ждем ввода лимита
        if context.user_data.get('waiting_for_limit'):
            await self.handle_new_limit(update, context)
            return
            
        # Если редактируем сумму транзакции
        if context.user_data.get('editing_transaction'):
            from handlers.edit_handler import handle_new_amount
            await handle_new_amount(update, context)
            return
            
        # Если устанавливаем имя
        if context.user_data.get('setting_name'):
            from handlers.settings_handler import handle_name_input
            await handle_name_input(update, context)
            return
            
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text(get_message("start_first", "ru"))
                return
            
            # Парсинг сообщения
            transaction_data = parse_transaction(text)
            if not transaction_data:
                await update.message.reply_text(
                    f"{get_message('transaction_error', user.language)}\n\n"
                    f"{get_message('transaction_format_help', user.language)}\n"
                    "Отправьте /help для получения справки.",
                    parse_mode='Markdown'
                )
                return
            
            amount, currency, description, is_income = transaction_data
            
            # Удаляем RUB из поддерживаемых валют
            if currency == 'RUB':
                await update.message.reply_text(
                    f"❌ Валюта RUB больше не поддерживается.\n"
                    f"Поддерживаемые валюты: {get_message('supported_currencies', user.language)}",
                    parse_mode='Markdown'
                )
                return
            
            # Получаем предлагаемую категорию через OpenAI
            suggested_category = await self._suggest_category(description, user.id, db)
            
            # Сохраняем данные транзакции для последующего создания
            context.user_data['pending_transaction'] = {
                'amount': amount,
                'currency': currency,
                'description': description,
                'is_income': is_income,
                'user_id': user.id
            }
            
            # Показываем диалог выбора категории
            await self._show_category_selection(update, suggested_category, user, db)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            await update.message.reply_text(get_message("error_occurred", user.language if 'user' in locals() else "ru"))
        finally:
            db.close()

    async def _suggest_category(self, description: str, user_id: int, db) -> str:
        """Предложение категории с помощью OpenAI"""
        categories = db.query(Category).filter(Category.user_id == user_id).all()
        
        if not categories:
            return "Прочее"  # Fallback
        
        category_names = [cat.name for cat in categories]
        
        try:
            suggested_category = await self.openai_service.categorize_transaction(
                description, category_names
            )
            return suggested_category
        except Exception as e:
            logger.error(f"Ошибка при определении категории через OpenAI: {e}")
            return "Прочее"

    async def _show_category_selection(self, update: Update, suggested_category: str, user, db):
        """Показать диалог выбора категории"""
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        
        # Создаем клавиатуру с вариантами категорий
        keyboard = []
        
        # Первой кнопкой идет предлагаемая категория
        if suggested_category and suggested_category != "Прочее":
            keyboard.append([InlineKeyboardButton(
                f"✅ {suggested_category} (предлагается)", 
                callback_data=f"select_cat_{suggested_category}"
            )])
        
        # Остальные категории
        for category in categories:
            if category.name != suggested_category:
                keyboard.append([InlineKeyboardButton(
                    f"📁 {category.name}", 
                    callback_data=f"select_cat_{category.name}"
                )])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сообщение с предлагаемой категорией
        message_text = (
            f"{get_message('suggest_category', user.language, category=suggested_category)}\n\n"
            f"{get_message('category_question', user.language)}"
        )
        
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора категории"""
        query = update.callback_query
        await query.answer()
        
        if not context.user_data.get('pending_transaction'):
            await query.edit_message_text("Сессия истекла. Попробуйте снова.")
            return
        
        # Получаем данные транзакции
        transaction_data = context.user_data['pending_transaction']
        category_name = query.data.replace('select_cat_', '')
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
            
            # Находим категорию
            category = db.query(Category).filter(
                Category.user_id == transaction_data['user_id'],
                Category.name == category_name
            ).first()
            
            if not category:
                await query.edit_message_text("Категория не найдена.")
                return
            
            # Создаем транзакцию
            transaction = Transaction(
                user_id=transaction_data['user_id'],
                amount=transaction_data['amount'] if transaction_data['is_income'] else -transaction_data['amount'],
                currency=transaction_data['currency'],
                description=transaction_data['description'],
                category_id=category.id,
                created_at=datetime.now()
            )
            
            db.add(transaction)
            db.commit()
            
            # Проверка лимитов для расходов
            warning_msg = ""
            if not transaction_data['is_income']:
                warning_msg = await self._check_limits(
                    transaction_data['user_id'], 
                    category.id, 
                    abs(transaction_data['amount']), 
                    transaction_data['currency'], 
                    db
                )
            
            # Персонализированное сообщение
            name = user.name or "друг"
            operation_type = get_message("income_added", user.language) if transaction_data['is_income'] else get_message("expense_added", user.language)
            
            response_text = (
                f"✅ {operation_type}\n\n"
                f"👤 {name}, транзакция сохранена:\n"
                f"{get_message('amount', user.language)}: {transaction_data['amount']} {transaction_data['currency']}\n"
                f"{get_message('category', user.language)}: {category.name}\n"
                f"{get_message('description', user.language)}: {transaction_data['description']}\n"
                f"{warning_msg}"
            )
            
            await query.edit_message_text(response_text, parse_mode='Markdown')
            
        finally:
            db.close()
            context.user_data.pop('pending_transaction', None)

    async def _check_limits(self, user_id: int, category_id: int, amount: float, currency: str, db) -> str:
        """Проверка лимитов расходов"""
        limits = db.query(Limit).filter(
            Limit.user_id == user_id,
            Limit.category_id == category_id
        ).all()
        
        warning_messages = []
        
        for limit in limits:
            if limit.currency != currency:
                continue
                
            # Получаем сумму расходов за текущий месяц в этой категории
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            month_expenses = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.currency == currency,
                Transaction.amount < 0,
                Transaction.created_at >= current_month_start
            ).all()
            
            total_spent = sum(abs(transaction.amount) for transaction in month_expenses)
            total_spent += amount  # Добавляем текущую трату
            
            if total_spent > limit.amount:
                category = db.query(Category).filter(Category.id == category_id).first()
                warning_messages.append(
                    f"⚠️ Превышен лимит для категории '{category.name}': "
                    f"{total_spent:.2f}/{limit.amount:.2f} {currency}"
                )
            elif total_spent > limit.amount * 0.8:  # Предупреждение при 80%
                category = db.query(Category).filter(Category.id == category_id).first()
                warning_messages.append(
                    f"🔔 Приближение к лимиту '{category.name}': "
                    f"{total_spent:.2f}/{limit.amount:.2f} {currency}"
                )
        
        return "\n".join(warning_messages)

    async def handle_new_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка добавления новой категории"""
        category_name = update.message.text.strip()
        user_id = update.effective_user.id
        
        if len(category_name) > 50:
            await update.message.reply_text("Название категории слишком длинное (максимум 50 символов).")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text(get_message("start_first", user.language if user else "ru"))
                return
            
            # Проверяем, не существует ли уже такая категория
            existing_category = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name == category_name
            ).first()
            
            if existing_category:
                await update.message.reply_text(
                    get_message("category_exists", user.language, name=category_name)
                )
                return
            
            # Создаем новую категорию
            new_category = Category(name=category_name, user_id=user.id, is_default=False)
            db.add(new_category)
            db.commit()
            
            await update.message.reply_text(
                get_message("category_added", user.language, name=category_name)
            )
            
        finally:
            db.close()
            context.user_data['waiting_for_category'] = None

    async def handle_new_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ввода нового лимита"""
        from utils.parsers import parse_amount_and_currency
        
        text = update.message.text.strip()
        user_id = update.effective_user.id
        category_id = context.user_data.get('waiting_for_limit')
        
        # Парсинг суммы и валюты
        result = parse_amount_and_currency(text)
        if not result:
            await update.message.reply_text(
                "Неверный формат. Укажите сумму и валюту, например:\n"
                "`500 EUR` или `300 USD`",
                parse_mode='Markdown'
            )
            return
        
        amount, currency = result
        
        # Проверяем, что это не RUB
        if currency == 'RUB':
            await update.message.reply_text(
                "❌ Валюта RUB больше не поддерживается.\n"
                "Поддерживаемые валюты: EUR, USD",
                parse_mode='Markdown'
            )
            return
        
        if amount <= 0:
            await update.message.reply_text("Сумма лимита должна быть больше нуля.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text(get_message("start_first", user.language if user else "ru"))
                return
            
            category = db.query(Category).filter(
                Category.id == category_id,
                Category.user_id == user.id
            ).first()
            
            if not category:
                await update.message.reply_text("Категория не найдена.")
                return
            
            # Проверяем, нет ли уже лимита для этой категории
            existing_limit = db.query(Limit).filter(
                Limit.user_id == user.id,
                Limit.category_id == category_id,
                Limit.currency == currency
            ).first()
            
            if existing_limit:
                await update.message.reply_text("Для этой категории уже установлен лимит в данной валюте.")
                return
            
            # Создаем новый лимит
            limit = Limit(
                user_id=user.id,
                category_id=category_id,
                amount=amount,
                currency=currency
            )
            
            db.add(limit)
            db.commit()
            
            name = user.name or "друг"
            await update.message.reply_text(
                f"✅ {name}, лимит установлен!\n\n"
                f"Категория: {category.name}\n"
                f"Лимит: {amount} {currency}",
                parse_mode='Markdown'
            )
            
        finally:
            db.close()
            context.user_data['waiting_for_limit'] = None