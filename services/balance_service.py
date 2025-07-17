from datetime import datetime
from database import get_db_session, User, Balance, Transaction


class BalanceService:
    """Сервис для работы с балансом пользователя"""
    
    def __init__(self):
        pass
    
    def get_or_create_balance(self, user_id: int, currency: str = "EUR") -> Balance:
        """Получить или создать баланс пользователя"""
        db = get_db_session()
        try:
            # Ищем существующий баланс
            balance = db.query(Balance).filter(
                Balance.user_id == user_id,
                Balance.currency == currency
            ).first()
            
            if not balance:
                # Создаем новый баланс
                balance = Balance(
                    user_id=user_id,
                    amount=0.0,
                    currency=currency
                )
                db.add(balance)
                db.commit()
                db.refresh(balance)
            
            return balance
        finally:
            db.close()
    
    def add_income(self, user_id: int, amount: float, currency: str = "EUR") -> Balance:
        """Добавить доход к балансу"""
        db = get_db_session()
        try:
            balance = db.query(Balance).filter(
                Balance.user_id == user_id,
                Balance.currency == currency
            ).first()
            
            if not balance:
                balance = Balance(
                    user_id=user_id,
                    amount=amount,
                    currency=currency
                )
                db.add(balance)
            else:
                balance.amount += amount
                balance.last_updated = datetime.utcnow()
            
            db.commit()
            db.refresh(balance)
            return balance
        finally:
            db.close()
    
    def subtract_expense(self, user_id: int, amount: float, currency: str = "EUR") -> Balance:
        """Вычесть расход из баланса"""
        db = get_db_session()
        try:
            balance = db.query(Balance).filter(
                Balance.user_id == user_id,
                Balance.currency == currency
            ).first()
            
            if not balance:
                balance = Balance(
                    user_id=user_id,
                    amount=-amount,
                    currency=currency
                )
                db.add(balance)
            else:
                balance.amount -= amount
                balance.last_updated = datetime.utcnow()
            
            db.commit()
            db.refresh(balance)
            return balance
        finally:
            db.close()
    
    def get_balance(self, user_id: int, currency: str = "EUR") -> float:
        """Получить текущий баланс пользователя"""
        db = get_db_session()
        try:
            balance = db.query(Balance).filter(
                Balance.user_id == user_id,
                Balance.currency == currency
            ).first()
            
            return balance.amount if balance else 0.0
        finally:
            db.close()
    
    def get_all_balances(self, user_id: int) -> list:
        """Получить все балансы пользователя по валютам"""
        db = get_db_session()
        try:
            balances = db.query(Balance).filter(
                Balance.user_id == user_id
            ).all()
            
            return balances
        finally:
            db.close()
    
    def recalculate_balance(self, user_id: int, currency: str = "EUR") -> Balance:
        """Пересчитать баланс на основе всех транзакций"""
        db = get_db_session()
        try:
            # Получаем все транзакции пользователя в данной валюте
            transactions = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.currency == currency
            ).all()
            
            # Суммируем все транзакции
            total_amount = sum(transaction.amount for transaction in transactions)
            
            # Получаем или создаем баланс
            balance = db.query(Balance).filter(
                Balance.user_id == user_id,
                Balance.currency == currency
            ).first()
            
            if not balance:
                balance = Balance(
                    user_id=user_id,
                    amount=total_amount,
                    currency=currency
                )
                db.add(balance)
            else:
                balance.amount = total_amount
                balance.last_updated = datetime.utcnow()
            
            db.commit()
            db.refresh(balance)
            return balance
        finally:
            db.close()
    
    def update_balance_from_transaction(self, transaction: Transaction) -> Balance:
        """Обновить баланс на основе транзакции"""
        return self.add_income(transaction.user_id, transaction.amount, transaction.currency)