import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from database import get_db_session, User, Category, Transaction, Limit
from services.openai_service import OpenAIService
from utils.parsers import parse_transaction

logger = logging.getLogger(__name__)


class TransactionHandler:
    def __init__(self):
        self.openai_service = OpenAIService()

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка текстовых сообщений для парсинга транзакций"""
        # Если ждем ввода названия категории
        if context.user_data.get('waiting_for_category'):
            await self.handle_new_category(update, context)
            return
            
        # Если ждем ввода лимита
        if context.user_data.get('waiting_for_limit'):
            await self.handle_new_limit(update, context)
            return
            
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text("Сначала выполните команду /start")
                return
            
            # Парсинг сообщения
            transaction_data = parse_transaction(text)
            if not transaction_data:
                await update.message.reply_text(
                    "Не удалось распознать операцию. 🤔\n\n"
                    "Используйте формат: '35 евро продукты' или '+2000 евро зарплата'\n"
                    "Отправьте /help для получения справки."
                )
                return
            
            amount, currency, description, is_income = transaction_data
            
            # Определение категории через OpenAI
            category = await self._determine_category(description, user.id, db)
            
            # Создание транзакции
            transaction = Transaction(
                user_id=user.id,
                amount=amount if is_income else -amount,
                currency=currency,
                description=description,
                category_id=category.id,
                created_at=datetime.now()
            )
            
            db.add(transaction)
            db.commit()
            
            # Проверка лимитов для расходов
            warning_msg = ""
            if not is_income:
                warning_msg = await self._check_limits(user.id, category.id, abs(amount), currency, db)
            
            operation_type = "💰 Доход" if is_income else "💸 Расход"
            await update.message.reply_text(
                f"✅ {operation_type} добавлен!\n\n"
                f"Сумма: {amount} {currency}\n"
                f"Категория: {category.name}\n"
                f"Описание: {description}\n"
                f"{warning_msg}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            await update.message.reply_text("Произошла ошибка при обработке операции.")
        finally:
            db.close()

    async def _determine_category(self, description: str, user_id: int, db) -> Category:
        """Определение категории с помощью OpenAI"""
        categories = db.query(Category).filter(Category.user_id == user_id).all()
        
        if not categories:
            # Создаем категорию "Прочее" если нет категорий
            default_category = Category(name="Прочее", user_id=user_id, is_default=True)
            db.add(default_category)
            db.commit()
            return default_category
        
        category_names = [cat.name for cat in categories]
        
        try:
            suggested_category = await self.openai_service.categorize_transaction(
                description, category_names
            )
            
            # Ищем категорию по имени
            for category in categories:
                if category.name.lower() == suggested_category.lower():
                    return category
                    
        except Exception as e:
            logger.error(f"Ошибка при определении категории через OpenAI: {e}")
        
        # Возвращаем категорию "Прочее" по умолчанию
        default_category = next((cat for cat in categories if cat.name == "Прочее"), categories[0])
        return default_category

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
                await update.message.reply_text("Сначала выполните команду /start")
                return
            
            # Проверяем, не существует ли уже такая категория
            existing_category = db.query(Category).filter(
                Category.user_id == user.id,
                Category.name == category_name
            ).first()
            
            if existing_category:
                await update.message.reply_text("Категория с таким названием уже существует.")
                return
            
            # Создаем новую категорию
            new_category = Category(name=category_name, user_id=user.id, is_default=False)
            db.add(new_category)
            db.commit()
            
            await update.message.reply_text(f"✅ Категория '{category_name}' добавлена!")
            
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
        
        if amount <= 0:
            await update.message.reply_text("Сумма лимита должна быть больше нуля.")
            return
        
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await update.message.reply_text("Сначала выполните команду /start")
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
                Limit.category_id == category_id
            ).first()
            
            if existing_limit:
                await update.message.reply_text("Для этой категории уже установлен лимит.")
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
            
            await update.message.reply_text(
                f"✅ Лимит установлен!\n\n"
                f"Категория: {category.name}\n"
                f"Лимит: {amount} {currency}"
            )
            
        finally:
            db.close()
            context.user_data['waiting_for_limit'] = None