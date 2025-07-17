#!/usr/bin/env python3
"""
Миграция для добавления таблицы balances и пересчета балансов пользователей
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Balance, User, Transaction, get_db_session
from sqlalchemy import text

def migrate_balance():
    """Создать таблицу balances и пересчитать балансы"""
    db = get_db_session()
    try:
        # Создаем таблицу balances
        print("Создание таблицы balances...")
        Balance.metadata.create_all(bind=engine)
        print("✅ Таблица balances создана")
        
        # Получаем всех пользователей
        users = db.query(User).all()
        print(f"Найдено {len(users)} пользователей")
        
        for user in users:
            print(f"Пересчитываем баланс для пользователя {user.telegram_id}...")
            
            # Получаем все транзакции пользователя, сгруппированные по валютам
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user.id
            ).all()
            
            if not transactions:
                print(f"  У пользователя {user.telegram_id} нет транзакций")
                continue
                
            # Группируем по валютам
            currency_totals = {}
            for transaction in transactions:
                currency = transaction.currency
                if currency not in currency_totals:
                    currency_totals[currency] = 0
                currency_totals[currency] += transaction.amount
            
            # Создаем записи баланса для каждой валюты
            for currency, total_amount in currency_totals.items():
                # Проверяем, есть ли уже баланс для этой валюты
                existing_balance = db.query(Balance).filter(
                    Balance.user_id == user.id,
                    Balance.currency == currency
                ).first()
                
                if existing_balance:
                    # Обновляем существующий баланс
                    existing_balance.amount = total_amount
                    print(f"  Обновлен баланс: {total_amount} {currency}")
                else:
                    # Создаем новый баланс
                    new_balance = Balance(
                        user_id=user.id,
                        amount=total_amount,
                        currency=currency
                    )
                    db.add(new_balance)
                    print(f"  Создан баланс: {total_amount} {currency}")
        
        db.commit()
        print("✅ Миграция завершена успешно")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка миграции: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_balance()