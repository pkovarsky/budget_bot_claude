#!/usr/bin/env python3
"""
Миграция для добавления системы памяти категорий
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import create_tables, get_db_session, CategoryMemory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_memory_system():
    """
    Создает таблицу category_memory для системы памяти категорий
    """
    try:
        logger.info("Начинаем миграцию системы памяти категорий...")
        
        # Создаем все таблицы (включая новую CategoryMemory)
        create_tables()
        
        logger.info("✅ Система памяти категорий успешно добавлена!")
        logger.info("Теперь бот будет запоминать ваши выборы категорий и предлагать их автоматически.")
        
        # Проверяем, что таблица создана
        db = get_db_session()
        try:
            # Пытаемся выполнить простой запрос к новой таблице
            count = db.query(CategoryMemory).count()
            logger.info(f"Таблица category_memory создана, записей: {count}")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при миграции: {e}")
        return False
        
    return True

if __name__ == "__main__":
    success = migrate_memory_system()
    if success:
        print("🎉 Миграция выполнена успешно!")
    else:
        print("❌ Ошибка при выполнении миграции")
        sys.exit(1)