"""
Утилиты для работы с Telegram API
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    """
    Безопасное редактирование сообщения с обработкой BadRequest
    
    Args:
        query: CallbackQuery объект
        text: Новый текст сообщения
        reply_markup: Клавиатура (опционально)
        parse_mode: Режим парсинга (опционально)
    """
    try:
        # Проверяем, отличается ли новый текст от текущего
        current_text = query.message.text or ""
        if current_text.strip() == text.strip():
            logger.debug("Текст сообщения не изменился, пропускаем редактирование")
            return
            
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.debug(f"Сообщение не изменилось, пропускаем редактирование: {e}")
            # Просто отвечаем на callback без изменения сообщения
            return
        elif "Message to edit not found" in str(e):
            logger.debug(f"Сообщение для редактирования не найдено: {e}")
            # Отправляем новое сообщение
            try:
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as fallback_error:
                logger.error(f"Ошибка при fallback отправке: {fallback_error}")
        else:
            logger.error(f"BadRequest при редактировании сообщения: {e}")
            # Пробуем отправить новое сообщение
            try:
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as fallback_error:
                logger.error(f"Ошибка при fallback отправке: {fallback_error}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}")
        # Пробуем отправить новое сообщение
        try:
            await query.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as fallback_error:
            logger.error(f"Ошибка при fallback отправке: {fallback_error}")

async def safe_answer_callback(query, text=None, show_alert=False):
    """
    Безопасный ответ на callback query
    
    Args:
        query: CallbackQuery объект
        text: Текст уведомления (опционально)
        show_alert: Показать как alert (опционально)
    """
    try:
        await query.answer(text=text, show_alert=show_alert)
    except BadRequest as e:
        if "Query is too old" in str(e):
            logger.debug(f"Callback query слишком старый, пропускаем: {e}")
        else:
            logger.error(f"BadRequest при ответе на callback: {e}")
    except Exception as e:
        logger.error(f"Ошибка при ответе на callback: {e}")

async def safe_delete_message(query):
    """
    Безопасное удаление сообщения
    
    Args:
        query: CallbackQuery объект
    """
    try:
        await query.delete_message()
    except BadRequest as e:
        if "Message to delete not found" in str(e):
            logger.debug(f"Сообщение для удаления не найдено: {e}")
        else:
            logger.error(f"BadRequest при удалении сообщения: {e}")
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")