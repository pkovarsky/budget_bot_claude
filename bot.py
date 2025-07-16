import logging
from telegram import BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from database import create_tables
from handlers.start_handler import (start_command, help_command, handle_language_setup, 
                                     handle_name_setup, handle_name_input_setup, handle_help_callback)
from handlers.enhanced_transaction_handler import EnhancedTransactionHandler
from handlers.categories_handler import categories_command, handle_categories_callback
from handlers.stats_handler import stats_command, handle_stats_callback, handle_charts_callback, handle_stats_back
from handlers.charts_handler import charts_command, handle_charts_callback as handle_new_charts_callback
from handlers.limits_handler import limits_command, handle_limits_callback
from handlers.export_handler import export_command
from handlers.photo_handler import handle_photo, handle_document
from handlers.edit_handler import edit_command, handle_edit_callback
from handlers.settings_handler import settings_command, handle_settings_callback
from handlers.notifications_handler import (notifications_command, handle_notifications_callback,
                                           handle_time_input, handle_salary_date_input)
from services.notification_scheduler import NotificationScheduler
import config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный обработчик транзакций, используется в различных функциях
transaction_handler = EnhancedTransactionHandler()


async def set_bot_commands(application: Application) -> None:
    """Register bot commands for the user interface."""
    commands = [
        BotCommand("start", "Начало работы"),
        BotCommand("help", "Справка"),
        BotCommand("categories", "Категории"),
        BotCommand("stats", "Статистика"),
        BotCommand("charts", "Графики"),
        BotCommand("limits", "Лимиты"),
        BotCommand("export", "Экспорт"),
        BotCommand("edit", "Редактировать"),
        BotCommand("settings", "Настройки"),
        BotCommand("notifications", "Уведомления"),
    ]

    await application.bot.set_my_commands(commands)


async def handle_callback(update, context):
    """Общий обработчик callback-кнопок"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Обработка настройки языка при регистрации
    if data.startswith("setup_lang_"):
        await handle_language_setup(update, context)
    elif data.startswith("setup_name_") or data == "setup_skip_name" or data == "setup_back":
        await handle_name_setup(update, context)
    
    # Обработка интерактивной справки
    elif data.startswith("help_"):
        await handle_help_callback(update, context)
    
    # Обработка выбора категории для транзакций
    elif data.startswith("select_cat_") or data == "select_cancel" or data == "create_new_category":
        await transaction_handler.handle_category_selection(update, context)
    
    # Обработка выбора подкатегории для транзакций
    elif (data.startswith("select_subcat_") or data == "subcat_skip" or 
          data == "subcat_back" or data == "create_new_subcategory"):
        await transaction_handler.handle_subcategory_selection(update, context)
    
    # Обработка выбора смайлика для новой категории
    elif (data.startswith("emoji_select_") or data == "more_emojis" or 
          data == "back_to_name" or data == "back_to_emoji_selection"):
        await transaction_handler.handle_emoji_selection(update, context)
    
    # Обработка выбора смайлика для новой подкатегории
    elif (data.startswith("subcat_emoji_select_") or data == "subcat_more_emojis" or 
          data == "subcat_back_to_name" or data == "subcat_back_to_emoji_selection"):
        await transaction_handler.handle_subcategory_emoji_selection(update, context)
    
    # Обработка кнопок статистики
    elif data.startswith("stats_"):
        if data == "stats_back":
            await handle_stats_back(update, context)
        elif data == "stats_charts":
            await handle_new_charts_callback(update, context)
        else:
            await handle_stats_callback(update, context)
    
    # Обработка кнопок графиков (включая period_ и monthly_ для графиков)
    elif (data.startswith("chart_") or data == "back_to_charts" or 
          data.startswith("period_") or data.startswith("monthly_")):
        await handle_new_charts_callback(update, context)
    
    # Обработка кнопок уведомлений
    elif (data.startswith("notif_") or data.startswith("daily_") or 
          data.startswith("budget_") or data.startswith("salary_") or 
          data.startswith("tz_")):
        await handle_notifications_callback(update, context)
    
    # Обработка кнопок категорий
    elif (data.startswith("cat_") or data == "cat_back" or 
          data.startswith("cat_emoji_select_") or data == "cat_more_emojis"):
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
    
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(set_bot_commands)
        .build()
    )
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("charts", charts_command))
    application.add_handler(CommandHandler("limits", limits_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    
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