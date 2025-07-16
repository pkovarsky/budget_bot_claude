#!/usr/bin/env python3
"""
Тест для проверки сохранения настроек уведомлений
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db_session, User

def test_notification_settings(telegram_id: int):
    """Тест настроек уведомлений для конкретного пользователя"""
    print(f"🔍 Проверяем настройки уведомлений для пользователя {telegram_id}")
    
    db = get_db_session()
    try:
        # Найдём пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f"❌ Пользователь с ID {telegram_id} не найден")
            return False
        
        print(f"✅ Пользователь найден: {user.name or 'без имени'}")
        
        # Выводим текущие настройки
        print(f"\n📊 Текущие настройки:")
        print(f"📅 Напоминания о тратах: {'✅ Включено' if user.daily_reminder_enabled else '❌ Выключено'}")
        print(f"⏰ Время напоминаний: {user.daily_reminder_time.strftime('%H:%M') if user.daily_reminder_time else 'не установлено'}")
        print(f"💰 Уведомления о бюджете: {'✅ Включено' if user.budget_notifications_enabled else '❌ Выключено'}")
        print(f"⏰ Время уведомлений: {user.budget_notification_time.strftime('%H:%M') if user.budget_notification_time else 'не установлено'}")
        print(f"📊 Частота уведомлений: {user.budget_notification_frequency}")
        print(f"💵 Дата зарплаты: {user.salary_date} числа" if user.salary_date else "не установлена")
        print(f"🌍 Часовой пояс: {user.timezone}")
        
        # Тест изменения настроек
        print(f"\n🔄 Тестируем изменение настроек...")
        
        # Сохраняем оригинальные значения
        original_daily = user.daily_reminder_enabled
        original_budget = user.budget_notifications_enabled
        
        # Изменяем настройки
        user.daily_reminder_enabled = not original_daily
        user.budget_notifications_enabled = not original_budget
        db.commit()
        
        print(f"✅ Настройки изменены в базе данных")
        
        # Проверяем, что изменения сохранились
        db.refresh(user)
        if user.daily_reminder_enabled != original_daily and user.budget_notifications_enabled != original_budget:
            print(f"✅ Изменения успешно сохранены!")
        else:
            print(f"❌ Изменения не сохранились!")
            return False
        
        # Возвращаем оригинальные значения
        user.daily_reminder_enabled = original_daily
        user.budget_notifications_enabled = original_budget
        db.commit()
        
        print(f"🔄 Настройки возвращены к исходным значениям")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        return False
    finally:
        db.close()

def test_new_session_update(telegram_id: int):
    """Тест обновления в новой сессии (имитация проблемы)"""
    print(f"\n🧪 Тест обновления в новой сессии...")
    
    # Первая сессия - получаем пользователя
    db1 = get_db_session()
    try:
        user = db1.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f"❌ Пользователь не найден")
            return False
        
        original_value = user.daily_reminder_enabled
        print(f"📋 Оригинальное значение daily_reminder_enabled: {original_value}")
    finally:
        db1.close()
    
    # Вторая сессия - пытаемся изменить тот же объект (так было в коде)
    db2 = get_db_session()
    try:
        # Это неправильный способ - изменение объекта из другой сессии
        try:
            user.daily_reminder_enabled = not original_value
            db2.commit()
            print(f"❌ Неправильный способ сработал (не должен был)")
        except Exception as e:
            print(f"✅ Неправильный способ вызвал ошибку (как и должен): {type(e).__name__}")
        
        # Правильный способ - получить объект в новой сессии
        fresh_user = db2.query(User).filter(User.telegram_id == telegram_id).first()
        if fresh_user:
            fresh_user.daily_reminder_enabled = not original_value
            db2.commit()
            print(f"✅ Правильный способ сработал!")
            
            # Возвращаем обратно
            fresh_user.daily_reminder_enabled = original_value
            db2.commit()
        
    finally:
        db2.close()

def main():
    """Основная функция"""
    print("🔔 Тест настроек уведомлений Budget Bot")
    print("=" * 50)
    
    # Запрашиваем Telegram ID пользователя
    try:
        telegram_id = input("Введите ваш Telegram ID (цифры): ").strip()
        telegram_id = int(telegram_id)
    except ValueError:
        print("❌ Некорректный Telegram ID")
        return
    
    # Основной тест
    success = test_notification_settings(telegram_id)
    if not success:
        print("\n❌ Основной тест провален")
        return
    
    # Тест проблемы с сессиями
    test_new_session_update(telegram_id)
    
    print("\n" + "=" * 50)
    print("✅ Все тесты завершены!")
    print("\n💡 Если у вас все еще проблемы с сохранением:")
    print("1. Перезапустите бота")
    print("2. Попробуйте отключить/включить настройки снова")
    print("3. Проверьте логи бота на ошибки")

if __name__ == "__main__":
    main()