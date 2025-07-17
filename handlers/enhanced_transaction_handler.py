import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Subcategory, Transaction, Limit, Balance
from services.openai_service import OpenAIService
from services.category_memory_service import CategoryMemoryService
from utils.parsers import parse_transaction
from utils.localization import get_message
from services.emoji_service import EmojiService
from services.balance_service import BalanceService

logger = logging.getLogger(__name__)


class EnhancedTransactionHandler:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.memory_service = CategoryMemoryService()
        self.balance_service = BalanceService()
    
    def _is_cancel_command(self, text: str) -> bool:
        """Проверка на команду отмены"""
        return text.strip().lower() in ['/cancel', 'отмена', 'cancel']
    
    async def _handle_cancel_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     context_key: str, message: str) -> None:
        """Обработка отмены операции"""
        context.user_data.pop(context_key, None)
        await update.message.reply_text(
            f"❌ {message}",
            reply_markup=None
        )
    
    async def _get_user_from_telegram_id(self, telegram_id: int) -> User:
        """Получить пользователя по telegram_id"""
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            return user
        finally:
            db.close()
    
    def _get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Получить клавиатуру с кнопкой главного меню"""
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_emoji_with_fallback(self, obj, fallback: str = "📁") -> str:
        """Получить emoji с fallback значением"""
        return obj.emoji if hasattr(obj, 'emoji') and obj.emoji else fallback
    
    def _calculate_limit_period(self, limit: Limit) -> tuple:
        """Рассчитать период для лимита"""
        if limit.period == 'weekly':
            # Неделя - последние 7 дней
            period_start = datetime.now() - timedelta(days=7)
            period_text = "неделю"
        elif limit.period == 'custom' and hasattr(limit, 'end_date') and limit.end_date:
            # Кастомный период - от создания лимита до конечной даты
            period_start = limit.created_at if hasattr(limit, 'created_at') else datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_text = f"до {limit.end_date.strftime('%d.%m.%Y')}"
        else:
            # Месяц - текущий месяц
            period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_text = "месяц"
        
        return period_start, period_text
    
    def _create_category_keyboard(self, categories: list, suggested_category: str = None) -> InlineKeyboardMarkup:
        """Создать клавиатуру для выбора категорий"""
        keyboard = []
        
        # Первой кнопкой идет предлагаемая категория
        if suggested_category:
            # Находим предлагаемую категорию и добавляем её первой
            suggested_cat_obj = None
            for cat in categories:
                if cat.name == suggested_category:
                    suggested_cat_obj = cat
                    break
            
            if suggested_cat_obj:
                suggested_emoji = self._get_emoji_with_fallback(suggested_cat_obj)
                keyboard.append([InlineKeyboardButton(
                    f"✅ {suggested_emoji} {suggested_category} (предлагается)", 
                    callback_data=f"select_cat_{suggested_category}"
                )])
        
        # Остальные категории
        for category in categories:
            if category.name != suggested_category:
                emoji = self._get_emoji_with_fallback(category)
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {category.name}", 
                    callback_data=f"select_cat_{category.name}"
                )])
        
        # Добавляем кнопки управления
        keyboard.append([InlineKeyboardButton("➕ Создать новую категорию", callback_data="create_new_category")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="select_cancel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_subcategory_keyboard(self, subcategories: list, suggested_subcategory: str = None) -> InlineKeyboardMarkup:
        """Создать клавиатуру для выбора подкатегорий"""
        keyboard = []
        
        # Кнопка пропуска подкатегории
        keyboard.append([InlineKeyboardButton("⏭️ Пропустить подкатегорию", callback_data="subcat_skip")])
        
        # Предлагаемая подкатегория
        if suggested_subcategory:
            keyboard.append([InlineKeyboardButton(
                f"✅ {suggested_subcategory} (предлагается)", 
                callback_data=f"select_subcat_{suggested_subcategory}"
            )])
        
        # Существующие подкатегории
        for subcategory in subcategories:
            if not suggested_subcategory or subcategory.name != suggested_subcategory:
                emoji = self._get_emoji_with_fallback(subcategory, "📂")
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {subcategory.name}", 
                    callback_data=f"select_subcat_{subcategory.name}"
                )])
        
        # Добавляем кнопки управления
        keyboard.append([InlineKeyboardButton("➕ Создать новую подкатегорию", callback_data="create_new_subcategory")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="subcat_back")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _create_emoji_keyboard(self, suggested_emoji: str, category_name: str, 
                             callback_prefix: str = "emoji_select") -> InlineKeyboardMarkup:
        """Создать клавиатуру для выбора смайликов"""
        emoji_service = EmojiService()
        keyboard = []
        
        # Первая кнопка - рекомендуемый смайлик
        keyboard.append([InlineKeyboardButton(
            f"✅ {suggested_emoji} (рекомендуется)", 
            callback_data=f"{callback_prefix}_{suggested_emoji}"
        )])
        
        # Получаем клавиатуру смайликов для категории
        emoji_keyboard = emoji_service.get_emoji_keyboard_for_category(category_name)
        
        # Добавляем смайлики в клавиатуру
        for emoji_row in emoji_keyboard:
            button_row = []
            for emoji in emoji_row:
                if emoji != suggested_emoji:
                    button_row.append(InlineKeyboardButton(
                        emoji, 
                        callback_data=f"{callback_prefix}_{emoji}"
                    ))
            if button_row:
                keyboard.append(button_row)
        
        # Кнопки управления
        more_callback = "more_emojis" if callback_prefix == "emoji_select" else "subcat_more_emojis"
        default_callback = f"{callback_prefix}_📁" if callback_prefix == "emoji_select" else f"{callback_prefix}_📂"
        back_callback = "back_to_name" if callback_prefix == "emoji_select" else "subcat_back_to_name"
        
        keyboard.append([
            InlineKeyboardButton("📂 Больше смайликов", callback_data=more_callback),
            InlineKeyboardButton("📁 По умолчанию", callback_data=default_callback)
        ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=back_callback)])
        
        return InlineKeyboardMarkup(keyboard)
    
    async def _create_and_process_transaction(self, transaction_data: dict, category: Category, 
                                            subcategory: Subcategory = None, db=None) -> tuple:
        """Создать транзакцию и обработать её"""
        # Создаем транзакцию
        transaction = Transaction(
            user_id=transaction_data['user_id'],
            amount=transaction_data['amount'] if transaction_data['is_income'] else -transaction_data['amount'],
            currency=transaction_data['currency'],
            description=transaction_data['description'],
            category_id=category.id,
            subcategory_id=subcategory.id if subcategory else None,
            created_at=datetime.now()
        )
        
        db.add(transaction)
        db.commit()
        
        # Обновляем баланс для расходов
        balance = None
        if not transaction_data['is_income']:
            balance = self.balance_service.subtract_expense(
                transaction_data['user_id'], 
                transaction_data['amount'], 
                transaction_data['currency']
            )
        
        # Запоминаем связь описания с категорией для будущих предложений
        self.memory_service.remember_category(
            user_id=transaction_data['user_id'],
            description=transaction_data['description'],
            category_id=category.id,
            confidence=1.0  # Максимальная уверенность для ручного выбора
        )
        
        # Проверка лимитов для расходов
        warning_msg = ""
        limit_exceeded = False
        limit_info = ""
        if not transaction_data['is_income']:
            warning_msg, limit_exceeded = await self._check_limits(
                transaction_data['user_id'], 
                category.id, 
                abs(transaction_data['amount']), 
                transaction_data['currency'], 
                db
            )
            
            # Получаем информацию о лимите для отображения
            limit_info = await self._get_limit_info(
                transaction_data['user_id'], 
                category.id, 
                transaction_data['currency'], 
                db
            )
        
        return balance, warning_msg, limit_exceeded, limit_info
    
    def _format_transaction_response(self, transaction_data: dict, category: Category, 
                                   subcategory: Subcategory, user: User, balance=None, 
                                   limit_info: str = "", new_category: bool = False) -> str:
        """Форматировать ответ о транзакции"""
        # Персонализированное сообщение
        name = user.name or "бро"
        operation_type = get_message("income_added", user.language) if transaction_data['is_income'] else get_message("expense_added", user.language)
        
        category_emoji = self._get_emoji_with_fallback(category)
        category_text = f"{category_emoji} {category.name}"
        
        if subcategory:
            subcategory_emoji = self._get_emoji_with_fallback(subcategory, "📂")
            category_text += f" → {subcategory_emoji} {subcategory.name}"
        
        # Основное сообщение о транзакции
        response_text = f"✅ {operation_type}\n\n"
        
        if new_category:
            response_text += f"🆕 Создана новая категория: {category_emoji} {category.name}\n\n"
        
        response_text += (
            f"👤 {name}, транзакция сохранена:\n"
            f"{get_message('amount', user.language)}: {transaction_data['amount']} {transaction_data['currency']}\n"
            f"{get_message('category', user.language)}: {category_text}\n"
            f"{get_message('description', user.language)}: {transaction_data['description']}"
        )
        
        # Добавляем информацию о балансе для расходов
        if balance:
            balance_emoji = "💰" if balance.amount >= 0 else "💸"
            response_text += f"\n\n{balance_emoji} **Общий баланс:** {balance.amount:.2f} {balance.currency}"
        
        # Добавляем информацию о лимите
        if limit_info:
            response_text += f"\n{limit_info}"
        
        return response_text

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений для парсинга транзакций с улучшенным UI"""
        # Если ждем ввода названия категории
        if context.user_data.get('waiting_for_category'):
            # Проверяем на отмену
            if self._is_cancel_command(update.message.text):
                await self._handle_cancel_operation(update, context, 'waiting_for_category', 
                                                   "Добавление категории отменено.")
                return
            await self.handle_new_category(update, context)
            return
            
        # Если ждем ввода названия новой категории (для создания из меню)
        if context.user_data.get('waiting_for_category_name'):
            await self.handle_category_name_input(update, context)
            return
            
        # Если ждем ввода названия новой подкатегории
        if context.user_data.get('waiting_for_subcategory_name'):
            await self.handle_subcategory_name_input(update, context)
            return
            
        # Если ждем ввода лимита
        if context.user_data.get('waiting_for_limit'):
            # Проверяем на отмену
            if self._is_cancel_command(update.message.text):
                await self._handle_cancel_operation(update, context, 'waiting_for_limit', 
                                                   "Установка лимита отменена.")
                context.user_data.pop('limit_category_id', None)
                return
            await self.handle_new_limit(update, context)
            return
            
        # Если редактируем сумму транзакции
        if context.user_data.get('editing_transaction'):
            # Проверяем на отмену
            if self._is_cancel_command(update.message.text):
                await self._handle_cancel_operation(update, context, 'editing_transaction', 
                                                   "Редактирование транзакции отменено.")
                return
            from handlers.edit_handler import handle_new_amount
            await handle_new_amount(update, context)
            return
            
        # Если устанавливаем имя при первичной настройке
        if context.user_data.get('setting_up_name'):
            from handlers.start_handler import handle_name_input_setup
            await handle_name_input_setup(update, context)
            return
        
        # Если устанавливаем имя в настройках
        if context.user_data.get('setting_name'):
            from handlers.settings_handler import handle_name_input
            await handle_name_input(update, context)
            return
        
        # Если устанавливаем время для напоминаний
        if context.user_data.get('setting_daily_time'):
            from handlers.notifications_handler import handle_time_input
            await handle_time_input(update, context, 'daily')
            return
        
        # Если устанавливаем время для уведомлений о бюджете
        if context.user_data.get('setting_budget_time'):
            from handlers.notifications_handler import handle_time_input
            await handle_time_input(update, context, 'budget')
            return
        
        # Если устанавливаем дату зарплаты
        if context.user_data.get('setting_salary_date'):
            from handlers.notifications_handler import handle_salary_date_input
            await handle_salary_date_input(update, context)
            return
        
        # Если редактируем лимит
        if context.user_data.get('editing_limit'):
            await self.handle_limit_edit_input(update, context)
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

            
            # Для доходов (с +) не нужен выбор категории - добавляем к балансу
            if is_income:
                # Создаем транзакцию дохода (без категории)
                transaction = Transaction(
                    user_id=user.id,
                    category_id=None,  # Доходы не имеют категории
                    amount=amount,  # Для доходов amount уже положительный
                    currency=currency,
                    description=description
                )
                db.add(transaction)
                db.commit()
                
                # Добавляем к балансу
                balance = self.balance_service.add_income(user.id, amount, currency)
                
                # Показываем уведомление о добавлении дохода
                name = user.name or "бро"
                keyboard = self._get_main_menu_keyboard()
                await update.message.reply_text(
                    f"✅ {name}, доход добавлен к балансу!\n\n"
                    f"💰 **{description}**\n"
                    f"💵 Сумма: +{amount} {currency}\n"
                    f"💳 Текущий баланс: {balance.amount} {currency}",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return
            
            # Для расходов получаем предлагаемую категорию через OpenAI
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
        
        # Сначала проверяем память
        memory_suggestion = self.memory_service.suggest_category(user_id, description)
        if memory_suggestion and memory_suggestion.get('confidence', 0) >= 0.8:
            logger.info(f"Найдено в памяти: {memory_suggestion['category_name']} (уверенность: {memory_suggestion['confidence']:.2f})")
            return memory_suggestion['category_name']
        
        # Если в памяти нет подходящего варианта, используем OpenAI
        try:
            suggested_category = await self.openai_service.categorize_transaction(
                description, category_names
            )
            logger.info(f"Категория предложена через OpenAI: {suggested_category}")
            return suggested_category
        except Exception as e:
            logger.error(f"Ошибка при определении категории через OpenAI: {e}")
            return "Прочее"

    async def _show_category_selection(self, update: Update, suggested_category: str, user, db):
        """Показать диалог выбора категории"""
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        reply_markup = self._create_category_keyboard(categories, suggested_category)
        
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
        
        if query.data == "select_cancel":
            context.user_data.pop('pending_transaction', None)
            await query.edit_message_text("❌ Добавление транзакции отменено.")
            return
        
        if query.data == "create_new_category":
            await self._start_category_creation(query, context)
            return

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
            
            # Сохраняем выбранную категорию
            context.user_data['selected_category'] = category.id
            
            # Получаем подкатегории для выбранной категории
            subcategories = db.query(Subcategory).filter(
                Subcategory.category_id == category.id,
                Subcategory.user_id == user.id
            ).all()
            
            # Показываем выбор подкатегории
            await self._show_subcategory_selection(query, category, subcategories, transaction_data['description'], user, db)
            
        finally:
            db.close()

    async def _show_subcategory_selection(self, query, category, subcategories, description, user, db):
        """Показать диалог выбора подкатегории"""
        # Получаем предлагаемую подкатегорию через OpenAI
        suggested_subcategory = await self._suggest_subcategory(description, category.id, user.id, db)
        reply_markup = self._create_subcategory_keyboard(subcategories, suggested_subcategory)
        
        # Сообщение с предлагаемой подкатегорией
        category_emoji = self._get_emoji_with_fallback(category)
        message_text = (
            f"📂 **Выбор подкатегории для {category_emoji} {category.name}**\n\n"
        )
        
        if suggested_subcategory:
            message_text += f"💡 Предлагаемая подкатегория: {suggested_subcategory}\n\n"
        
        message_text += "Выберите подкатегорию или пропустите этот шаг:"
        
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _suggest_subcategory(self, description: str, category_id: int, user_id: int, db) -> str:
        """Предложение подкатегории с помощью OpenAI"""
        subcategories = db.query(Subcategory).filter(
            Subcategory.category_id == category_id,
            Subcategory.user_id == user_id
        ).all()
        
        if not subcategories:
            return None
        
        subcategory_names = [subcat.name for subcat in subcategories]
        
        try:
            # Получаем категорию для контекста
            category = db.query(Category).filter(Category.id == category_id).first()
            category_name = category.name if category else "Неизвестная"
            
            suggested_subcategory = await self.openai_service.categorize_subcategory(
                description, category_name, subcategory_names
            )
            return suggested_subcategory
        except Exception as e:
            logger.error(f"Ошибка при определении подкатегории через OpenAI: {e}")
            return None

    async def _check_limits(self, user_id: int, category_id: int, amount: float, currency: str, db) -> tuple[str, bool]:
        """Проверка лимитов расходов. Возвращает (warning_message, is_limit_exceeded)"""
        limits = db.query(Limit).filter(
            Limit.user_id == user_id,
            Limit.category_id == category_id
        ).all()
        
        warning_messages = []
        limit_exceeded = False
        
        for limit in limits:
            if limit.currency != currency:
                continue
                
            # Определяем период для расчета
            period_start, period_text = self._calculate_limit_period(limit)
            
            period_expenses = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.currency == currency,
                Transaction.amount < 0,
                Transaction.created_at >= period_start
            ).all()
            
            total_spent = sum(abs(transaction.amount) for transaction in period_expenses)
            total_spent += amount  # Добавляем текущую трату
            
            category = db.query(Category).filter(Category.id == category_id).first()
            
            if total_spent > limit.amount:
                limit_exceeded = True
                warning_messages.append(
                    f"🚨 **ПРЕВЫШЕН ЛИМИТ!** 🚨\n"
                    f"Категория: {category.name}\n"
                    f"Потрачено: {total_spent:.2f}/{limit.amount:.2f} {currency}\n"
                    f"Период: {period_text}"
                )
            elif total_spent > limit.amount * 0.8:  # Предупреждение при 80%
                warning_messages.append(
                    f"🔔 Приближение к лимиту '{category.name}': "
                    f"{total_spent:.2f}/{limit.amount:.2f} {currency} за {period_text}"
                )
        
        return "\n".join(warning_messages), limit_exceeded
    
    async def _get_limit_info(self, user_id: int, category_id: int, currency: str, db) -> str:
        """Получить информацию о лимите для отображения"""
        limits = db.query(Limit).filter(
            Limit.user_id == user_id,
            Limit.category_id == category_id,
            Limit.currency == currency
        ).all()
        
        if not limits:
            return ""
        
        limit_info_lines = []
        
        for limit in limits:
            # Определяем период для расчета
            period_start, period_text = self._calculate_limit_period(limit)
            
            # Считаем потраченное
            period_expenses = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category_id,
                Transaction.currency == currency,
                Transaction.amount < 0,
                Transaction.created_at >= period_start
            ).all()
            
            total_spent = sum(abs(transaction.amount) for transaction in period_expenses)
            
            # Формируем информацию о лимите
            limit_emoji = "💳"
            if total_spent > limit.amount:
                limit_emoji = "🚨"
            elif total_spent > limit.amount * 0.8:
                limit_emoji = "⚠️"
            
            limit_info_lines.append(
                f"{limit_emoji} **Лимит ({period_text}):** {total_spent:.2f}/{limit.amount:.2f} {currency}"
            )
        
        return "\n" + "\n".join(limit_info_lines) if limit_info_lines else ""

    async def handle_subcategory_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора подкатегории"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "subcat_back":
            # Возвращаемся к выбору категории
            context.user_data.pop('selected_category', None)
            
            transaction_data = context.user_data.get('pending_transaction')
            if transaction_data:
                db = get_db_session()
                try:
                    user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
                    if user:
                        suggested_category = await self._suggest_category(transaction_data['description'], user.id, db)
                        await self._show_category_selection_from_query(query, suggested_category, user, db)
                        return
                finally:
                    db.close()
            
            await query.edit_message_text("❌ Сессия истекла.")
            return
        
        if query.data == "create_new_subcategory":
            await self._start_subcategory_creation(query, context)
            return
        
        if query.data == "subcat_skip":
            # Создаем транзакцию без подкатегории
            await self._create_transaction_final(query, context, None)
            return
        
        if query.data.startswith("select_subcat_"):
            subcategory_name = query.data.replace("select_subcat_", "")
            await self._create_transaction_final(query, context, subcategory_name)
            return

    async def _show_category_selection_from_query(self, query, suggested_category: str, user, db):
        """Показать диалог выбора категории (из callback query)"""
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        reply_markup = self._create_category_keyboard(categories, suggested_category)
        
        # Сообщение с предлагаемой категорией
        message_text = (
            f"{get_message('suggest_category', user.language, category=suggested_category)}\n\n"
            f"{get_message('category_question', user.language)}"
        )
        
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _start_subcategory_creation(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать процесс создания новой подкатегории"""
        context.user_data['waiting_for_subcategory_name'] = True
        
        # Получаем информацию о выбранной категории
        selected_category_id = context.user_data.get('selected_category')
        if not selected_category_id:
            await query.edit_message_text("❌ Ошибка: категория не выбрана.")
            return
        
        db = get_db_session()
        try:
            category = db.query(Category).filter(Category.id == selected_category_id).first()
            if not category:
                await query.edit_message_text("❌ Ошибка: категория не найдена.")
                return
            
            category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
            await query.edit_message_text(
                f"🏷️ **Создание новой подкатегории**\n\n"
                f"Категория: {category_emoji} {category.name}\n\n"
                f"Введите название для новой подкатегории:\n"
                f"• Максимум 50 символов\n"
                f"• Название должно быть уникальным в рамках категории\n\n"
                f"Отправьте /cancel для отмены",
                parse_mode='Markdown'
            )
        finally:
            db.close()

    async def handle_subcategory_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ввода названия подкатегории"""
        subcategory_name = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Проверка на отмену
        if self._is_cancel_command(subcategory_name):
            context.user_data.pop('waiting_for_subcategory_name', None)
            
            # Возвращаем к выбору подкатегории
            selected_category_id = context.user_data.get('selected_category')
            if selected_category_id:
                db = get_db_session()
                try:
                    user = db.query(User).filter(User.telegram_id == user_id).first()
                    category = db.query(Category).filter(Category.id == selected_category_id).first()
                    
                    if user and category:
                        subcategories = db.query(Subcategory).filter(
                            Subcategory.category_id == category.id,
                            Subcategory.user_id == user.id
                        ).all()
                        
                        transaction_data = context.user_data.get('pending_transaction')
                        if transaction_data:
                            await self._show_subcategory_selection_from_message(update, category, subcategories, transaction_data['description'], user, db)
                            return
                finally:
                    db.close()
            
            await update.message.reply_text("❌ Создание подкатегории отменено.")
            return
        
        if len(subcategory_name) > 50:
            await update.message.reply_text("❌ Название подкатегории слишком длинное (максимум 50 символов).")
            return
        
        if not subcategory_name:
            await update.message.reply_text("❌ Название подкатегории не может быть пустым.")
            return
        
        selected_category_id = context.user_data.get('selected_category')
        if not selected_category_id:
            await update.message.reply_text("❌ Ошибка: категория не выбрана.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text(get_message("start_first", "ru"))
                return
            
            category = db.query(Category).filter(Category.id == selected_category_id).first()
            if not category:
                await update.message.reply_text("❌ Категория не найдена.")
                return
            
            # Проверяем, не существует ли уже такая подкатегория
            existing_subcategory = db.query(Subcategory).filter(
                Subcategory.user_id == user.id,
                Subcategory.category_id == selected_category_id,
                Subcategory.name == subcategory_name
            ).first()
            
            if existing_subcategory:
                await update.message.reply_text(f"❌ Подкатегория '{subcategory_name}' уже существует в этой категории.")
                return
            
            # Переходим к выбору смайлика
            context.user_data['new_subcategory_name'] = subcategory_name
            context.user_data.pop('waiting_for_subcategory_name', None)
            context.user_data['waiting_for_subcategory_emoji'] = True
            
            await self._show_subcategory_emoji_selection(update, subcategory_name, category.name)
            
        finally:
            db.close()

    async def _show_subcategory_emoji_selection(self, update: Update, subcategory_name: str, category_name: str) -> None:
        """Показать выбор смайлика для подкатегории"""
        emoji_service = EmojiService()
        
        # Получаем рекомендуемый смайлик
        suggested_emoji = emoji_service.get_emoji_by_category_name(subcategory_name)
        
        # Создаем клавиатуру с смайликами
        keyboard = []
        
        # Первая кнопка - рекомендуемый смайлик
        keyboard.append([InlineKeyboardButton(
            f"✅ {suggested_emoji} (рекомендуется)", 
            callback_data=f"subcat_emoji_select_{suggested_emoji}"
        )])
        
        # Получаем клавиатуру смайликов для подкатегории
        emoji_keyboard = emoji_service.get_emoji_keyboard_for_category(subcategory_name)
        
        # Добавляем смайлики в клавиатуру
        for emoji_row in emoji_keyboard:
            button_row = []
            for emoji in emoji_row:
                if emoji != suggested_emoji:  # Не дублируем рекомендуемый
                    button_row.append(InlineKeyboardButton(
                        emoji, 
                        callback_data=f"subcat_emoji_select_{emoji}"
                    ))
            if button_row:
                keyboard.append(button_row)
        
        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("📂 Больше смайликов", callback_data="subcat_more_emojis"),
            InlineKeyboardButton("📂 По умолчанию", callback_data="subcat_emoji_select_📂")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="subcat_back_to_name")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"😊 **Выбор смайлика для подкатегории '{subcategory_name}'**\n\n"
            f"Категория: {category_name}\n"
            f"Рекомендуемый смайлик: {suggested_emoji}\n\n"
            f"Выберите смайлик для новой подкатегории:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _show_subcategory_selection_from_message(self, update: Update, category, subcategories, description, user, db):
        """Показать диалог выбора подкатегории (из message)"""
        # Получаем предлагаемую подкатегорию через OpenAI
        suggested_subcategory = await self._suggest_subcategory(description, category.id, user.id, db)
        
        # Создаем клавиатуру с вариантами подкатегорий
        keyboard = []
        
        # Кнопка пропуска подкатегории
        keyboard.append([InlineKeyboardButton("⏭️ Пропустить подкатегорию", callback_data="subcat_skip")])
        
        # Предлагаемая подкатегория
        if suggested_subcategory:
            keyboard.append([InlineKeyboardButton(
                f"✅ {suggested_subcategory} (предлагается)", 
                callback_data=f"select_subcat_{suggested_subcategory}"
            )])
        
        # Существующие подкатегории
        for subcategory in subcategories:
            if not suggested_subcategory or subcategory.name != suggested_subcategory:
                emoji = subcategory.emoji if hasattr(subcategory, 'emoji') and subcategory.emoji else "📂"
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {subcategory.name}", 
                    callback_data=f"select_subcat_{subcategory.name}"
                )])
        
        # Добавляем кнопку создания новой подкатегории
        keyboard.append([InlineKeyboardButton("➕ Создать новую подкатегорию", callback_data="create_new_subcategory")])
        keyboard.append([InlineKeyboardButton("🔙 Назад к категориям", callback_data="subcat_back")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Сообщение с предлагаемой подкатегорией
        category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
        message_text = (
            f"📂 **Выбор подкатегории для {category_emoji} {category.name}**\n\n"
        )
        
        if suggested_subcategory:
            message_text += f"💡 Предлагаемая подкатегория: {suggested_subcategory}\n\n"
        
        message_text += "Выберите подкатегорию или пропустите этот шаг:"
        
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _create_transaction_final(self, query, context: ContextTypes.DEFAULT_TYPE, subcategory_name: str = None):
        """Создать транзакцию с выбранной категорией и подкатегорией"""
        transaction_data = context.user_data.get('pending_transaction')
        selected_category_id = context.user_data.get('selected_category')
        
        if not transaction_data or not selected_category_id:
            await query.edit_message_text("❌ Данные транзакции не найдены.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
            category = db.query(Category).filter(Category.id == selected_category_id).first()
            
            if not category:
                await query.edit_message_text("❌ Категория не найдена.")
                return
            
            # Находим подкатегорию, если указана
            subcategory = None
            if subcategory_name:
                subcategory = db.query(Subcategory).filter(
                    Subcategory.name == subcategory_name,
                    Subcategory.category_id == selected_category_id,
                    Subcategory.user_id == user.id
                ).first()
            
            # Создаем и обрабатываем транзакцию
            balance, warning_msg, limit_exceeded, limit_info = await self._create_and_process_transaction(
                transaction_data, category, subcategory, db
            )
            
            # Формируем ответ
            response_text = self._format_transaction_response(
                transaction_data, category, subcategory, user, balance, limit_info
            )
            
            # Добавляем кнопку "На главную"
            keyboard = self._get_main_menu_keyboard()
            
            await query.edit_message_text(response_text, parse_mode='Markdown', reply_markup=keyboard)
            
            # Отправляем отдельное заметное сообщение о превышении лимита
            if limit_exceeded:
                limit_keyboard = self._get_main_menu_keyboard()
                await query.message.reply_text(
                    warning_msg,
                    parse_mode='Markdown',
                    reply_markup=limit_keyboard
                )
            elif warning_msg:  # Предупреждение о приближении к лимиту
                await query.message.reply_text(warning_msg, parse_mode='Markdown')
            
        finally:
            db.close()
            context.user_data.pop('pending_transaction', None)
            context.user_data.pop('selected_category', None)
    
    async def handle_limit_edit_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ввода данных для редактирования лимита"""
        text = update.message.text.strip()
        user_id = update.effective_user.id
        edit_data = context.user_data.get('editing_limit')
        
        if not edit_data:
            await update.message.reply_text("❌ Сессия истекла. Попробуйте снова.")
            return
        
        # Проверяем на отмену
        if self._is_cancel_command(text):
            context.user_data.pop('editing_limit', None)
            keyboard = self._get_main_menu_keyboard()
            await update.message.reply_text(
                "❌ Редактирование лимита отменено.",
                reply_markup=keyboard
            )
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                keyboard = self._get_main_menu_keyboard()
                await update.message.reply_text(
                    "Сначала выполните команду /start",
                    reply_markup=keyboard
                )
                return
            
            limit = db.query(Limit).filter(
                Limit.id == edit_data['limit_id'],
                Limit.user_id == user.id
            ).first()
            
            if not limit:
                keyboard = self._get_main_menu_keyboard()
                await update.message.reply_text(
                    "Лимит не найден.",
                    reply_markup=keyboard
                )
                return
            
            category = db.query(Category).filter(Category.id == limit.category_id).first()
            
            if edit_data['field'] == 'amount':
                # Обработка изменения суммы
                from utils.parsers import parse_amount_and_currency
                result = parse_amount_and_currency(text)
                if not result:
                    await update.message.reply_text(
                        "❌ Неверный формат. Укажите сумму и валюту, например:\n"
                        "`600 EUR` или `400 USD`",
                        parse_mode='Markdown'
                    )
                    return
                
                amount, currency = result
                if amount <= 0:
                    await update.message.reply_text("❌ Сумма лимита должна быть больше нуля.")
                    return
                
                # Обновляем лимит
                limit.amount = amount
                limit.currency = currency
                db.commit()
                
                period_text = "неделю" if limit.period == "weekly" else "месяц"
                keyboard = [[InlineKeyboardButton("🔙 К лимитам", callback_data="settings_back")]]
                await update.message.reply_text(
                    f"✅ **Лимит обновлен!**\n\n"
                    f"Категория: {category.name}\n"
                    f"Новый лимит: {amount} {currency} за {period_text}",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                
                
        finally:
            db.close()
            context.user_data.pop('editing_limit', None)

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
            
            # Создаем новую категорию с автоматически подобранным смайликом
            from services.emoji_service import EmojiService
            emoji_service = EmojiService()
            suggested_emoji = emoji_service.get_emoji_by_category_name(category_name)
            
            new_category = Category(
                name=category_name, 
                user_id=user.id, 
                is_default=False,
                emoji=suggested_emoji
            )
            db.add(new_category)
            db.commit()
            
            await update.message.reply_text(
                f"✅ Категория создана!\n\n"
                f"{suggested_emoji} {category_name}\n\n"
                f"Вы можете изменить смайлик через меню категорий (/categories)."
            )
            
        finally:
            db.close()
            context.user_data['waiting_for_category'] = None

    async def handle_new_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ввода нового лимита"""
        from utils.parsers import parse_amount_and_currency
        
        text = update.message.text.strip()
        user_id = update.effective_user.id
        limit_data = context.user_data.get('waiting_for_limit')
        
        # Поддерживаем старый формат для совместимости
        if isinstance(limit_data, int):
            category_id = limit_data
            period = 'monthly'  # По умолчанию месячный период
        else:
            category_id = limit_data.get('category_id')
            period = limit_data.get('period', 'monthly')
            end_date = limit_data.get('end_date')
        
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
                currency=currency,
                period=period,
                end_date=end_date if period == 'custom' else None
            )
            
            db.add(limit)
            db.commit()
            
            name = user.name or "бро"
            
            if period == 'custom':
                period_text = f"до {end_date.strftime('%d.%m.%Y')}"
            else:
                period_text = "неделю" if period == "weekly" else "месяц"
                period_text = f"за {period_text}"
            
            keyboard = self._get_main_menu_keyboard()
            await update.message.reply_text(
                f"✅ {name}, лимит установлен!\n\n"
                f"Категория: {category.name}\n"
                f"Лимит: {amount} {currency} {period_text}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        finally:
            db.close()
            context.user_data['waiting_for_limit'] = None

    async def _start_category_creation(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Начать процесс создания новой категории"""
        context.user_data['waiting_for_category_name'] = True
        
        # Сохраняем данные транзакции для возврата к ней после создания категории
        transaction_data = context.user_data.get('pending_transaction')
        if transaction_data:
            context.user_data['pending_transaction_backup'] = transaction_data
        
        await query.edit_message_text(
            "🏷️ **Создание новой категории**\n\n"
            "Введите название для новой категории:\n"
            "• Максимум 50 символов\n"
            "• Название должно быть уникальным\n\n"
            "Отправьте /cancel для отмены",
            parse_mode='Markdown'
        )

    async def handle_category_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка ввода названия категории"""
        category_name = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Проверка на отмену
        if self._is_cancel_command(category_name):
            context.user_data.pop('waiting_for_category_name', None)
            
            # Возвращаем к выбору категории
            transaction_data = context.user_data.get('pending_transaction_backup')
            if transaction_data:
                context.user_data['pending_transaction'] = transaction_data
                context.user_data.pop('pending_transaction_backup', None)
                
                db = get_db_session()
                try:
                    user = db.query(User).filter(User.telegram_id == user_id).first()
                    if user:
                        suggested_category = await self._suggest_category(transaction_data['description'], user.id, db)
                        await self._show_category_selection(update, suggested_category, user, db)
                        return
                finally:
                    db.close()
            
            await update.message.reply_text("❌ Создание категории отменено.")
            return
        
        if len(category_name) > 50:
            await update.message.reply_text("❌ Название категории слишком длинное (максимум 50 символов).")
            return
        
        if not category_name:
            await update.message.reply_text("❌ Название категории не может быть пустым.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text(get_message("start_first", "ru"))
                return
            
            # Проверяем, не существует ли уже такая категория
            existing_category = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name == category_name
            ).first()
            
            if existing_category:
                await update.message.reply_text(f"❌ Категория '{category_name}' уже существует.")
                return
            
            # Переходим к выбору смайлика
            context.user_data['new_category_name'] = category_name
            context.user_data.pop('waiting_for_category_name', None)
            context.user_data['waiting_for_category_emoji'] = True
            
            await self._show_emoji_selection(update, category_name)
            
        finally:
            db.close()

    async def _show_emoji_selection(self, update: Update, category_name: str) -> None:
        """Показать выбор смайлика для категории"""
        emoji_service = EmojiService()
        
        # Получаем рекомендуемый смайлик
        suggested_emoji = emoji_service.get_emoji_by_category_name(category_name)
        
        # Создаем клавиатуру с смайликами
        reply_markup = self._create_emoji_keyboard(suggested_emoji, category_name, "emoji_select")
        
        await update.message.reply_text(
            f"😊 **Выбор смайлика для категории '{category_name}'**\n\n"
            f"Рекомендуемый смайлик: {suggested_emoji}\n\n"
            "Выберите смайлик для новой категории:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_emoji_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора смайлика"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "back_to_name":
            context.user_data.pop('waiting_for_category_emoji', None)
            context.user_data['waiting_for_category_name'] = True
            await query.edit_message_text(
                "🏷️ **Создание новой категории**\n\n"
                "Введите название для новой категории:\n"
                "• Максимум 50 символов\n"
                "• Название должно быть уникальным\n\n"
                "Отправьте /cancel для отмены",
                parse_mode='Markdown'
            )
            return
        
        if query.data == "more_emojis":
            await self._show_more_emojis(query, context)
            return
        
        if query.data == "back_to_emoji_selection":
            category_name = context.user_data.get('new_category_name', '')
            await self._show_emoji_selection_from_query(query, category_name)
            return
        
        if query.data.startswith("emoji_select_"):
            selected_emoji = query.data.replace("emoji_select_", "")
            await self._create_category_with_emoji(query, context, selected_emoji)
            return

    async def handle_subcategory_emoji_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка выбора смайлика для подкатегории"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "subcat_back_to_name":
            context.user_data.pop('waiting_for_subcategory_emoji', None)
            context.user_data['waiting_for_subcategory_name'] = True
            
            selected_category_id = context.user_data.get('selected_category')
            if selected_category_id:
                db = get_db_session()
                try:
                    category = db.query(Category).filter(Category.id == selected_category_id).first()
                    if category:
                        category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
                        await query.edit_message_text(
                            f"🏷️ **Создание новой подкатегории**\n\n"
                            f"Категория: {category_emoji} {category.name}\n\n"
                            f"Введите название для новой подкатегории:\n"
                            f"• Максимум 50 символов\n"
                            f"• Название должно быть уникальным в рамках категории\n\n"
                            f"Отправьте /cancel для отмены",
                            parse_mode='Markdown'
                        )
                        return
                finally:
                    db.close()
            
            await query.edit_message_text("❌ Ошибка: категория не найдена.")
            return
        
        if query.data == "subcat_more_emojis":
            await self._show_more_subcategory_emojis(query, context)
            return
        
        if query.data == "subcat_back_to_emoji_selection":
            subcategory_name = context.user_data.get('new_subcategory_name', '')
            
            selected_category_id = context.user_data.get('selected_category')
            if selected_category_id:
                db = get_db_session()
                try:
                    category = db.query(Category).filter(Category.id == selected_category_id).first()
                    if category:
                        await self._show_subcategory_emoji_selection_from_query(query, subcategory_name, category.name)
                        return
                finally:
                    db.close()
            
            await query.edit_message_text("❌ Ошибка: категория не найдена.")
            return
        
        if query.data.startswith("subcat_emoji_select_"):
            selected_emoji = query.data.replace("subcat_emoji_select_", "")
            await self._create_subcategory_with_emoji(query, context, selected_emoji)
            return

    async def _show_more_subcategory_emojis(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать больше смайликов для подкатегории"""
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
                    callback_data=f"subcat_emoji_select_{emoji}"
                ))
            keyboard.append(row)
        
        # Кнопка назад
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="subcat_back_to_emoji_selection")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        subcategory_name = context.user_data.get('new_subcategory_name', '')
        await query.edit_message_text(
            f"😊 **Популярные смайлики для '{subcategory_name}'**\n\n"
            f"Выберите смайлик:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _create_subcategory_with_emoji(self, query, context: ContextTypes.DEFAULT_TYPE, emoji: str) -> None:
        """Создать подкатегорию с выбранным смайликом"""
        subcategory_name = context.user_data.get('new_subcategory_name')
        selected_category_id = context.user_data.get('selected_category')
        user_id = query.from_user.id
        
        if not subcategory_name or not selected_category_id:
            await query.edit_message_text("❌ Ошибка: данные подкатегории не найдены.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await query.edit_message_text(get_message("start_first", "ru"))
                return
            
            category = db.query(Category).filter(Category.id == selected_category_id).first()
            if not category:
                await query.edit_message_text("❌ Категория не найдена.")
                return
            
            # Создаем новую подкатегорию с смайликом
            new_subcategory = Subcategory(
                name=subcategory_name,
                emoji=emoji,
                category_id=selected_category_id,
                user_id=user.id
            )
            
            db.add(new_subcategory)
            db.commit()
            db.refresh(new_subcategory)
            
            # Очищаем временные данные
            context.user_data.pop('waiting_for_subcategory_emoji', None)
            context.user_data.pop('new_subcategory_name', None)
            
            # Автоматически создаем транзакцию с новой подкатегорией
            await self._create_transaction_final(query, context, new_subcategory.name)
            
        except Exception as e:
            logger.error(f"Ошибка при создании подкатегории: {e}")
            await query.edit_message_text(f"❌ Ошибка при создании подкатегории: {str(e)}")
        finally:
            db.close()

    async def _show_subcategory_emoji_selection_from_query(self, query, subcategory_name: str, category_name: str) -> None:
        """Показать выбор смайлика для подкатегории (из callback query)"""
        emoji_service = EmojiService()
        
        # Получаем рекомендуемый смайлик
        suggested_emoji = emoji_service.get_emoji_by_category_name(subcategory_name)
        
        # Создаем клавиатуру с смайликами
        keyboard = []
        
        # Первая кнопка - рекомендуемый смайлик
        keyboard.append([InlineKeyboardButton(
            f"✅ {suggested_emoji} (рекомендуется)", 
            callback_data=f"subcat_emoji_select_{suggested_emoji}"
        )])
        
        # Получаем клавиатуру смайликов для подкатегории
        emoji_keyboard = emoji_service.get_emoji_keyboard_for_category(subcategory_name)
        
        # Добавляем смайлики в клавиатуру
        for emoji_row in emoji_keyboard:
            button_row = []
            for emoji in emoji_row:
                if emoji != suggested_emoji:  # Не дублируем рекомендуемый
                    button_row.append(InlineKeyboardButton(
                        emoji, 
                        callback_data=f"subcat_emoji_select_{emoji}"
                    ))
            if button_row:
                keyboard.append(button_row)
        
        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("📂 Больше смайликов", callback_data="subcat_more_emojis"),
            InlineKeyboardButton("📂 По умолчанию", callback_data="subcat_emoji_select_📂")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="subcat_back_to_name")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"😊 **Выбор смайлика для подкатегории '{subcategory_name}'**\n\n"
            f"Категория: {category_name}\n"
            f"Рекомендуемый смайлик: {suggested_emoji}\n\n"
            f"Выберите смайлик для новой подкатегории:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _show_more_emojis(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Показать больше смайликов"""
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
                    callback_data=f"emoji_select_{emoji}"
                ))
            keyboard.append(row)
        
        # Кнопка назад
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_emoji_selection")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        category_name = context.user_data.get('new_category_name', '')
        await query.edit_message_text(
            f"😊 **Популярные смайлики для '{category_name}'**\n\n"
            "Выберите смайлик:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _show_emoji_selection_from_query(self, query, category_name: str) -> None:
        """Показать выбор смайлика для категории (из callback query)"""
        emoji_service = EmojiService()
        
        # Получаем рекомендуемый смайлик
        suggested_emoji = emoji_service.get_emoji_by_category_name(category_name)
        
        # Создаем клавиатуру с смайликами
        keyboard = []
        
        # Первая кнопка - рекомендуемый смайлик
        keyboard.append([InlineKeyboardButton(
            f"✅ {suggested_emoji} (рекомендуется)", 
            callback_data=f"emoji_select_{suggested_emoji}"
        )])
        
        # Получаем клавиатуру смайликов для категории
        emoji_keyboard = emoji_service.get_emoji_keyboard_for_category(category_name)
        
        # Добавляем смайлики в клавиатуру
        for emoji_row in emoji_keyboard:
            button_row = []
            for emoji in emoji_row:
                if emoji != suggested_emoji:  # Не дублируем рекомендуемый
                    button_row.append(InlineKeyboardButton(
                        emoji, 
                        callback_data=f"emoji_select_{emoji}"
                    ))
            if button_row:
                keyboard.append(button_row)
        
        # Кнопки управления
        keyboard.append([
            InlineKeyboardButton("📂 Больше смайликов", callback_data="more_emojis"),
            InlineKeyboardButton("📁 По умолчанию", callback_data="emoji_select_📁")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_name")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"😊 **Выбор смайлика для категории '{category_name}'**\n\n"
            f"Рекомендуемый смайлик: {suggested_emoji}\n\n"
            "Выберите смайлик для новой категории:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _create_category_with_emoji(self, query, context: ContextTypes.DEFAULT_TYPE, emoji: str) -> None:
        """Создать категорию с выбранным смайликом"""
        category_name = context.user_data.get('new_category_name')
        user_id = query.from_user.id
        
        if not category_name:
            await query.edit_message_text("❌ Ошибка: название категории не найдено.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await query.edit_message_text(get_message("start_first", "ru"))
                return
            
            # Создаем новую категорию с смайликом
            new_category = Category(
                name=category_name,
                emoji=emoji,
                user_id=user.id,
                is_default=False
            )
            
            db.add(new_category)
            db.commit()
            db.refresh(new_category)
            
            # Очищаем временные данные
            context.user_data.pop('waiting_for_category_emoji', None)
            context.user_data.pop('new_category_name', None)
            
            # Возвращаем к транзакции с новой категорией
            transaction_data = context.user_data.get('pending_transaction_backup')
            if transaction_data:
                context.user_data['pending_transaction'] = transaction_data
                context.user_data.pop('pending_transaction_backup', None)
                
                # Автоматически выбираем новую категорию
                await self._create_transaction_with_category(query, context, new_category)
            else:
                await query.edit_message_text(
                    f"✅ Категория создана!\n\n"
                    f"{emoji} {category_name}",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Ошибка при создании категории: {e}")
            await query.edit_message_text(f"❌ Ошибка при создании категории: {str(e)}")
        finally:
            db.close()

    async def _create_transaction_with_category(self, query, context: ContextTypes.DEFAULT_TYPE, category: Category) -> None:
        """Создать транзакцию с выбранной категорией"""
        transaction_data = context.user_data.get('pending_transaction')
        if not transaction_data:
            await query.edit_message_text("❌ Данные транзакции не найдены.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == query.from_user.id).first()
            
            # Создаем и обрабатываем транзакцию
            balance, warning_msg, limit_exceeded, limit_info = await self._create_and_process_transaction(
                transaction_data, category, None, db
            )
            
            # Формируем ответ
            response_text = self._format_transaction_response(
                transaction_data, category, None, user, balance, limit_info, new_category=True
            )
            
            # Добавляем кнопку "На главную"
            keyboard = self._get_main_menu_keyboard()
            
            await query.edit_message_text(response_text, parse_mode='Markdown', reply_markup=keyboard)
            
            # Отправляем отдельное заметное сообщение о превышении лимита
            if limit_exceeded:
                limit_keyboard = self._get_main_menu_keyboard()
                await query.message.reply_text(
                    warning_msg,
                    parse_mode='Markdown',
                    reply_markup=limit_keyboard
                )
            elif warning_msg:  # Предупреждение о приближении к лимиту
                await query.message.reply_text(warning_msg, parse_mode='Markdown')
            
        finally:
            db.close()
            context.user_data.pop('pending_transaction', None)