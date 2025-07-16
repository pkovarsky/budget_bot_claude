#!/usr/bin/env python3
"""
Быстрая диагностика графиков для конкретного пользователя
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.chart_service import ChartService
from database import get_db_session, User, Transaction, Category
from datetime import datetime, timedelta

def check_user_data(telegram_id: int):
    """Проверяем данные конкретного пользователя"""
    db = get_db_session()
    try:
        # Найдём пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            print(f"❌ Пользователь с ID {telegram_id} не найден")
            return False
        
        print(f"✅ Пользователь найден: {user.name or 'без имени'} (@{user.username or 'без username'})")
        
        # Проверяем категории
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        print(f"📁 Категорий: {len(categories)}")
        for cat in categories:
            print(f"  - {cat.emoji or '📁'} {cat.name}")
        
        # Проверяем транзакции
        transactions = db.query(Transaction).filter(Transaction.user_id == user.id).all()
        print(f"💰 Всего транзакций: {len(transactions)}")
        
        # Проверяем расходы за последние 30 дней
        start_date = datetime.now() - timedelta(days=30)
        recent_expenses = db.query(Transaction).filter(
            Transaction.user_id == user.id,
            Transaction.amount < 0,
            Transaction.created_at >= start_date
        ).all()
        
        print(f"📉 Расходов за последние 30 дней: {len(recent_expenses)}")
        
        if recent_expenses:
            total_amount = sum(abs(t.amount) for t in recent_expenses)
            print(f"💸 Общая сумма расходов: {total_amount:.2f}")
            
            # Расходы по категориям
            category_expenses = {}
            for t in recent_expenses:
                cat_name = "Неизвестно"
                for cat in categories:
                    if cat.id == t.category_id:
                        cat_name = cat.name
                        break
                
                if cat_name not in category_expenses:
                    category_expenses[cat_name] = 0
                category_expenses[cat_name] += abs(t.amount)
            
            print(f"📊 Расходы по категориям:")
            for cat_name, amount in category_expenses.items():
                print(f"  - {cat_name}: {amount:.2f}")
        
        return len(recent_expenses) > 0
        
    finally:
        db.close()

def test_chart_generation(telegram_id: int):
    """Тестируем генерацию графиков для конкретного пользователя"""
    chart_service = ChartService()
    
    # Тест круговой диаграммы
    print("\n🔄 Тестируем круговую диаграмму...")
    try:
        pie_chart = chart_service.generate_category_pie_chart(telegram_id, 30)
        if pie_chart:
            print(f"✅ Круговая диаграмма создана (размер: {len(pie_chart.getvalue())} байт)")
        else:
            print("❌ Круговая диаграмма не создана")
    except Exception as e:
        print(f"❌ Ошибка создания круговой диаграммы: {e}")
    
    # Тест графика трендов
    print("\n🔄 Тестируем график трендов...")
    try:
        trends_chart = chart_service.generate_spending_trends_chart(telegram_id, 30)
        if trends_chart:
            print(f"✅ График трендов создан (размер: {len(trends_chart.getvalue())} байт)")
        else:
            print("❌ График трендов не создан")
    except Exception as e:
        print(f"❌ Ошибка создания графика трендов: {e}")
    
    # Тест месячного сравнения
    print("\n🔄 Тестируем месячное сравнение...")
    try:
        monthly_chart = chart_service.generate_monthly_comparison_chart(telegram_id, 6)
        if monthly_chart:
            print(f"✅ Месячное сравнение создано (размер: {len(monthly_chart.getvalue())} байт)")
        else:
            print("❌ Месячное сравнение не создано")
    except Exception as e:
        print(f"❌ Ошибка создания месячного сравнения: {e}")

def main():
    """Основная функция"""
    print("🔍 Диагностика графиков Budget Bot")
    print("=" * 50)
    
    # Запрашиваем Telegram ID пользователя
    try:
        telegram_id = input("Введите ваш Telegram ID (цифры): ").strip()
        telegram_id = int(telegram_id)
    except ValueError:
        print("❌ Некорректный Telegram ID")
        return
    
    print(f"\n📋 Проверяем данные пользователя {telegram_id}...")
    has_data = check_user_data(telegram_id)
    
    if not has_data:
        print("\n⚠️ У пользователя нет расходов за последние 30 дней.")
        print("Графики могут не создаваться из-за отсутствия данных.")
        print("\nДля тестирования:")
        print("1. Добавьте несколько транзакций через бота")
        print("2. Повторите диагностику")
        return
    
    print(f"\n📈 Тестируем генерацию графиков...")
    test_chart_generation(telegram_id)
    
    print("\n" + "=" * 50)
    print("✅ Диагностика завершена!")

if __name__ == "__main__":
    main()