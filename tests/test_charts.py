#!/usr/bin/env python3
"""
Тест для проверки работы графиков
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from services.chart_service import ChartService
from database import get_db_session, User, Transaction, Category
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_matplotlib_import():
    """Тест импорта matplotlib"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import pandas as pd
        import numpy as np
        logger.info("✅ Все необходимые библиотеки импортированы успешно")
        return True
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        return False

def test_chart_service():
    """Тест создания сервиса графиков"""
    try:
        chart_service = ChartService()
        logger.info("✅ ChartService создан успешно")
        return chart_service
    except Exception as e:
        logger.error(f"❌ Ошибка создания ChartService: {e}")
        return None

def test_database_connection():
    """Тест подключения к базе данных"""
    try:
        db = get_db_session()
        users_count = db.query(User).count()
        transactions_count = db.query(Transaction).count()
        categories_count = db.query(Category).count()
        
        logger.info(f"✅ База данных подключена:")
        logger.info(f"  - Пользователей: {users_count}")
        logger.info(f"  - Транзакций: {transactions_count}")
        logger.info(f"  - Категорий: {categories_count}")
        
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        return False

def test_chart_generation(user_telegram_id: int = None):
    """Тест генерации графика"""
    if not user_telegram_id:
        # Найдем первого пользователя с транзакциями
        db = get_db_session()
        try:
            user_with_transactions = db.query(User).join(Transaction).first()
            if user_with_transactions:
                user_telegram_id = user_with_transactions.telegram_id
            else:
                logger.error("❌ Нет пользователей с транзакциями для тестирования")
                return False
        finally:
            db.close()
    
    try:
        chart_service = ChartService()
        
        # Тестируем круговую диаграмму
        logger.info("🔄 Генерируем круговую диаграмму...")
        pie_chart = chart_service.generate_category_pie_chart(
            user_id=user_telegram_id,
            period_days=30
        )
        
        if pie_chart:
            logger.info("✅ Круговая диаграмма создана успешно")
            logger.info(f"  - Размер файла: {len(pie_chart.getvalue())} байт")
        else:
            logger.warning("⚠️ Круговая диаграмма не создана (возможно, нет данных)")
        
        # Тестируем график трендов
        logger.info("🔄 Генерируем график трендов...")
        trends_chart = chart_service.generate_spending_trends_chart(
            user_id=user_telegram_id,
            period_days=30
        )
        
        if trends_chart:
            logger.info("✅ График трендов создан успешно")
            logger.info(f"  - Размер файла: {len(trends_chart.getvalue())} байт")
        else:
            logger.warning("⚠️ График трендов не создан (возможно, нет данных)")
        
        # Тестируем месячное сравнение
        logger.info("🔄 Генерируем месячное сравнение...")
        monthly_chart = chart_service.generate_monthly_comparison_chart(
            user_id=user_telegram_id,
            months=6
        )
        
        if monthly_chart:
            logger.info("✅ Месячное сравнение создано успешно")
            logger.info(f"  - Размер файла: {len(monthly_chart.getvalue())} байт")
        else:
            logger.warning("⚠️ Месячное сравнение не создано (возможно, нет данных)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации графиков: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def create_test_data():
    """Создать тестовые данные для проверки графиков"""
    try:
        db = get_db_session()
        
        # Найдем первого пользователя
        user = db.query(User).first()
        if not user:
            logger.error("❌ Нет пользователей в базе данных")
            return False
        
        # Проверим, есть ли уже транзакции
        existing_transactions = db.query(Transaction).filter(Transaction.user_id == user.id).count()
        if existing_transactions > 0:
            logger.info(f"✅ У пользователя уже есть {existing_transactions} транзакций")
            return True
        
        # Создадим тестовые категории если их нет
        categories = db.query(Category).filter(Category.user_id == user.id).all()
        if not categories:
            test_categories = [
                Category(name="Продукты", user_id=user.id, is_default=True, emoji="🛒"),
                Category(name="Транспорт", user_id=user.id, is_default=True, emoji="🚗"),
                Category(name="Развлечения", user_id=user.id, is_default=True, emoji="🎮"),
            ]
            for cat in test_categories:
                db.add(cat)
            db.commit()
            categories = test_categories
        
        # Создадим тестовые транзакции
        test_transactions = []
        for i in range(10):
            date = datetime.now() - timedelta(days=i)
            for j, category in enumerate(categories):
                transaction = Transaction(
                    user_id=user.id,
                    category_id=category.id,
                    amount=-(10 + i * 5 + j * 3),  # Отрицательная сумма для расходов
                    currency="EUR",
                    description=f"Тестовая транзакция {category.name} {i}",
                    created_at=date
                )
                test_transactions.append(transaction)
        
        for transaction in test_transactions:
            db.add(transaction)
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Создано {len(test_transactions)} тестовых транзакций")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания тестовых данных: {e}")
        return False

def main():
    """Основная функция тестирования"""
    logger.info("🚀 Начинаем тестирование графиков...")
    
    # Тест 1: Проверка импортов
    logger.info("\n📦 Тест 1: Проверка импортов библиотек")
    if not test_matplotlib_import():
        logger.error("❌ Тест импортов провален")
        return
    
    # Тест 2: Проверка создания сервиса
    logger.info("\n🔧 Тест 2: Создание сервиса графиков")
    chart_service = test_chart_service()
    if not chart_service:
        logger.error("❌ Тест создания сервиса провален")
        return
    
    # Тест 3: Проверка подключения к БД
    logger.info("\n🗄️ Тест 3: Подключение к базе данных")
    if not test_database_connection():
        logger.error("❌ Тест подключения к БД провален")
        return
    
    # Тест 4: Создание тестовых данных
    logger.info("\n📊 Тест 4: Создание тестовых данных")
    if not create_test_data():
        logger.error("❌ Тест создания данных провален")
        return
    
    # Тест 5: Генерация графиков
    logger.info("\n📈 Тест 5: Генерация графиков")
    if not test_chart_generation():
        logger.error("❌ Тест генерации графиков провален")
        return
    
    logger.info("\n🎉 Все тесты пройдены успешно!")

if __name__ == "__main__":
    main()