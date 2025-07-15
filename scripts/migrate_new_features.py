#!/usr/bin/env python3
"""
Скрипт для добавления новых полей в базу данных
"""
import sqlite3
from database import get_db_session, create_tables

def migrate_database():
    """Добавляет новые поля в таблицу users"""
    db = get_db_session()
    
    try:
        # Получаем подключение к SQLite
        connection = db.get_bind().raw_connection()
        cursor = connection.cursor()
        
        # Список полей для добавления
        new_fields = [
            "ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Amsterdam'",
            "ALTER TABLE users ADD COLUMN daily_reminder_enabled BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN daily_reminder_time TIME",
            "ALTER TABLE users ADD COLUMN budget_notifications_enabled BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN budget_notification_frequency TEXT DEFAULT 'daily'",
            "ALTER TABLE users ADD COLUMN budget_notification_time TIME",
            "ALTER TABLE users ADD COLUMN salary_date INTEGER"
        ]
        
        for field_sql in new_fields:
            try:
                cursor.execute(field_sql)
                print(f"✅ Добавлено поле: {field_sql}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"⚠️  Поле уже существует: {field_sql}")
                else:
                    print(f"❌ Ошибка добавления поля: {field_sql} - {e}")
        
        connection.commit()
        print("✅ Миграция завершена успешно!")
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        connection.rollback()
    finally:
        connection.close()
        db.close()

if __name__ == "__main__":
    migrate_database()