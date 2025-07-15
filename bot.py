import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from database import create_tables
from handlers.start_handler import (start_command, help_command, handle_language_setup, 
                                     handle_name_setup, handle_name_input_setup)
from handlers.enhanced_transaction_handler import EnhancedTransactionHandler
from handlers.categories_handler import categories_command, handle_categories_callback
from handlers.stats_handler import stats_command, handle_stats_callback
from handlers.limits_handler import limits_command, handle_limits_callback
from handlers.export_handler import export_command
from handlers.photo_handler import handle_photo, handle_document
from handlers.edit_handler import edit_command, handle_edit_callback
from handlers.settings_handler import settings_command, handle_settings_callback
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def handle_callback(update, context):
    """Общий обработчик callback-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Обработка настройки языка при регистрации
    if data.startswith("setup_lang_"):
        await handle_language_setup(update, context)
    elif data.startswith("setup_name_") or data == "setup_skip_name":
        await handle_name_setup(update, context)
    
    # Обработка выбора категории для транзакций
    elif data.startswith("select_cat_"):
        await transaction_handler.handle_category_selection(update, context)
    
    # Обработка кнопок статистики
    elif data.startswith("stats_"):
        if data == "stats_back":
            await stats_command(update, context)
        else:
            await handle_stats_callback(update, context)
    
    # Обработка кнопок категорий
    elif data.startswith("cat_") or data == "cat_back":
        await handle_categories_callback(update, context)
        
    # Обработка кнопок лимитов
    elif data.startswith("limits_") or data == "limits_back":
        await handle_limits_callback(update, context)
        
    # Обработка кнопок редактирования
    elif data.startswith("edit_"):
        await handle_edit_callback(update, context)
        
    # Обработка кнопок настроек
    elif data.startswith("settings_") or data.startswith("set_lang_"):
        await handle_settings_callback(update, context)


def main() -> None:
    """Запуск бота"""
    create_tables()
    
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    transaction_handler = EnhancedTransactionHandler()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("limits", limits_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Обработчики callback-кнопок и сообщений
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Обработчик фотографий (чеки)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Обработчик документов (изображения как файлы)
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
    
    # Обработчик текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, transaction_handler.handle_message))
    
    application.run_polling()


if __name__ == '__main__':
    main()