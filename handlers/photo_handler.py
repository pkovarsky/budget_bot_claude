import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
import asyncio

from database import get_db_session, User, Category, Transaction
from openai_service import OpenAIService

logger = logging.getLogger(__name__)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка фотографий чеков"""
    user_id = update.effective_user.id
    
    if not update.message.photo:
        return
    
    # Отправляем сообщение о начале обработки
    processing_message = await update.message.reply_text(
        "📸 Анализирую чек... Это может занять несколько секунд."
    )
    
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await processing_message.edit_text("Сначала выполните команду /start")
                return
            
            # Получаем фото в лучшем качестве
            photo = update.message.photo[-1]  # Самое большое изображение
            file = await photo.get_file()
            
            # Скачиваем изображение
            image_data = await file.download_as_bytearray()
            
            # Получаем категории пользователя
            categories = db.query(Category).filter(Category.user_id == user.id).all()
            category_names = [cat.name for cat in categories]
            
            # Обрабатываем чек через OpenAI
            openai_service = OpenAIService()
            transactions = await openai_service.process_receipt_photo(
                bytes(image_data), 
                category_names
            )
            
            if not transactions:
                await processing_message.edit_text(
                    "❌ Не удалось распознать чек. Убедитесь, что фото четкое и содержит информацию о покупках."
                )
                return
            
            # Сохраняем транзакции в базу данных
            saved_transactions = []
            for transaction_data in transactions:
                # Находим категорию
                category = next(
                    (cat for cat in categories if cat.name == transaction_data.get('category')), 
                    categories[0] if categories else None
                )
                
                if not category:
                    # Создаем категорию "Прочее" если нет категорий
                    category = Category(name="Прочее", user_id=user.id, is_default=True)
                    db.add(category)
                    db.commit()
                
                # Создаем транзакцию
                transaction = Transaction(
                    user_id=user.id,
                    amount=-abs(transaction_data['amount']),  # Расходы всегда отрицательные
                    currency=transaction_data['currency'],
                    description=transaction_data['description'],
                    category_id=category.id,
                    created_at=datetime.now()
                )
                
                db.add(transaction)
                saved_transactions.append(transaction)
            
            db.commit()
            
            # Формируем ответ пользователю
            if len(saved_transactions) == 1:
                transaction = saved_transactions[0]
                response = (
                    f"✅ Чек обработан!\n\n"
                    f"💸 Расход: {abs(transaction.amount)} {transaction.currency}\n"
                    f"📁 Категория: {category.name}\n"
                    f"📝 Описание: {transaction.description}"
                )
            else:
                total_amount = sum(abs(t.amount) for t in saved_transactions)
                currency = saved_transactions[0].currency if saved_transactions else "EUR"
                response = (
                    f"✅ Чек обработан!\n\n"
                    f"💸 Общая сумма: {total_amount} {currency}\n"
                    f"📊 Транзакций добавлено: {len(saved_transactions)}\n\n"
                    "Используйте /stats для просмотра статистики."
                )
            
            await processing_message.edit_text(response)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при обработке фото чека: {e}")
        await processing_message.edit_text(
            "❌ Произошла ошибка при обработке чека. Попробуйте еще раз или добавьте транзакцию вручную."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка документов (если пользователь отправит изображение как файл)"""
    if not update.message.document:
        return
    
    # Проверяем, что это изображение
    mime_type = update.message.document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        return
    
    # Размер файла не должен превышать 20MB (ограничение OpenAI)
    if update.message.document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "❌ Файл слишком большой. Максимальный размер: 20MB"
        )
        return
    
    user_id = update.effective_user.id
    
    # Отправляем сообщение о начале обработки
    processing_message = await update.message.reply_text(
        "📄 Анализирую документ с чеком... Это может занять несколько секунд."
    )
    
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if not user:
                await processing_message.edit_text("Сначала выполните команду /start")
                return
            
            # Скачиваем документ
            file = await update.message.document.get_file()
            image_data = await file.download_as_bytearray()
            
            # Получаем категории пользователя
            categories = db.query(Category).filter(Category.user_id == user.id).all()
            category_names = [cat.name for cat in categories]
            
            # Обрабатываем чек через OpenAI
            openai_service = OpenAIService()
            transactions = await openai_service.process_receipt_photo(
                bytes(image_data), 
                category_names
            )
            
            if not transactions:
                await processing_message.edit_text(
                    "❌ Не удалось распознать чек в документе. Убедитесь, что изображение четкое и содержит информацию о покупках."
                )
                return
            
            # Сохраняем транзакции (аналогично handle_photo)
            saved_transactions = []
            for transaction_data in transactions:
                # Находим категорию
                category = next(
                    (cat for cat in categories if cat.name == transaction_data.get('category')), 
                    categories[0] if categories else None
                )
                
                if not category:
                    # Создаем категорию "Прочее" если нет категорий
                    category = Category(name="Прочее", user_id=user.id, is_default=True)
                    db.add(category)
                    db.commit()
                
                # Создаем транзакцию
                transaction = Transaction(
                    user_id=user.id,
                    amount=-abs(transaction_data['amount']),  # Расходы всегда отрицательные
                    currency=transaction_data['currency'],
                    description=transaction_data['description'],
                    category_id=category.id,
                    created_at=datetime.now()
                )
                
                db.add(transaction)
                saved_transactions.append(transaction)
            
            db.commit()
            
            # Формируем ответ пользователю
            if len(saved_transactions) == 1:
                transaction = saved_transactions[0]
                response = (
                    f"✅ Документ обработан!\n\n"
                    f"💸 Расход: {abs(transaction.amount)} {transaction.currency}\n"
                    f"📁 Категория: {category.name}\n"
                    f"📝 Описание: {transaction.description}"
                )
            else:
                total_amount = sum(abs(t.amount) for t in saved_transactions)
                currency = saved_transactions[0].currency if saved_transactions else "EUR"
                response = (
                    f"✅ Документ обработан!\n\n"
                    f"💸 Общая сумма: {total_amount} {currency}\n"
                    f"📊 Транзакций добавлено: {len(saved_transactions)}\n\n"
                    "Используйте /stats для просмотра статистики."
                )
            
            await processing_message.edit_text(response)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при обработке документа с чеком: {e}")
        await processing_message.edit_text(
            "❌ Произошла ошибка при обработке документа. Попробуйте еще раз или добавьте транзакцию вручную."
        )