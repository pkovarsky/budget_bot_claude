"""
Система планирования уведомлений для бюджет-бота
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import List, Optional
import pytz
from telegram import Bot
from telegram.error import TelegramError

from database import get_db_session, User, Category, Transaction, Limit
from utils.localization import get_message

logger = logging.getLogger(__name__)

class NotificationScheduler:
    """Планировщик уведомлений"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running = False
        
    async def start(self):
        """Запуск планировщика"""
        self.running = True
        logger.info("Запуск планировщика уведомлений")
        
        while self.running:
            try:
                await self._check_daily_reminders()
                await self._check_budget_notifications()
                # Проверяем каждую минуту
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(60)
    
    async def stop(self):
        """Остановка планировщика"""
        self.running = False
        logger.info("Остановка планировщика уведомлений")
    
    async def _check_daily_reminders(self):
        """Проверка напоминаний о добавлении трат"""
        db = get_db_session()
        try:
            # Получаем пользователей с включенными напоминаниями
            users = db.query(User).filter(
                User.daily_reminder_enabled == True,
                User.daily_reminder_time.isnot(None)
            ).all()
            
            for user in users:
                await self._send_daily_reminder_if_needed(user)
                
        finally:
            db.close()
    
    async def _send_daily_reminder_if_needed(self, user: User):
        """Отправка напоминания о тратах если нужно"""
        try:
            # Получаем текущее время в часовом поясе пользователя
            user_tz = pytz.timezone(user.timezone)
            current_time = datetime.now(user_tz).time()
            
            # Проверяем, что текущее время соответствует времени напоминания
            # (с точностью до минуты)
            reminder_time = user.daily_reminder_time
            if (current_time.hour == reminder_time.hour and 
                current_time.minute == reminder_time.minute):
                
                # Проверяем, добавлял ли пользователь траты сегодня
                today = datetime.now(user_tz).date()
                today_start = datetime.combine(today, time.min).replace(tzinfo=user_tz)
                today_end = datetime.combine(today, time.max).replace(tzinfo=user_tz)
                
                db = get_db_session()
                try:
                    today_transactions = db.query(Transaction).filter(
                        Transaction.user_id == user.id,
                        Transaction.created_at >= today_start,
                        Transaction.created_at <= today_end
                    ).count()
                    
                    # Если нет трат за сегодня, отправляем напоминание
                    if today_transactions == 0:
                        message = get_message("daily_reminder", user.language)
                        await self.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"Отправлено напоминание пользователю {user.telegram_id}")
                        
                finally:
                    db.close()
                    
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания пользователю {user.telegram_id}: {e}")
    
    async def _check_budget_notifications(self):
        """Проверка уведомлений о бюджете"""
        db = get_db_session()
        try:
            # Получаем пользователей с включенными уведомлениями о бюджете
            users = db.query(User).filter(
                User.budget_notifications_enabled == True,
                User.budget_notification_time.isnot(None),
                User.salary_date.isnot(None)
            ).all()
            
            for user in users:
                await self._send_budget_notification_if_needed(user)
                
        finally:
            db.close()
    
    async def _send_budget_notification_if_needed(self, user: User):
        """Отправка уведомления о бюджете если нужно"""
        try:
            # Получаем текущее время в часовом поясе пользователя
            user_tz = pytz.timezone(user.timezone)
            current_time = datetime.now(user_tz).time()
            current_date = datetime.now(user_tz).date()
            
            # Проверяем, что текущее время соответствует времени уведомления
            notification_time = user.budget_notification_time
            if (current_time.hour == notification_time.hour and 
                current_time.minute == notification_time.minute):
                
                # Проверяем частоту уведомлений
                should_send = False
                
                if user.budget_notification_frequency == "daily":
                    should_send = True
                elif user.budget_notification_frequency == "weekly":
                    # Отправляем раз в неделю в понедельник
                    should_send = current_date.weekday() == 0
                
                if should_send:
                    await self._send_budget_status(user)
                    
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о бюджете пользователю {user.telegram_id}: {e}")
    
    async def _send_budget_status(self, user: User):
        """Отправка статуса бюджета"""
        try:
            db = get_db_session()
            try:
                # Вычисляем дни до зарплаты
                user_tz = pytz.timezone(user.timezone)
                today = datetime.now(user_tz).date()
                
                # Находим следующую дату зарплаты
                next_salary_date = self._get_next_salary_date(today, user.salary_date)
                days_until_salary = (next_salary_date - today).days
                
                # Получаем лимиты пользователя
                limits = db.query(Limit).filter(Limit.user_id == user.id).all()
                
                if not limits:
                    return
                
                message_parts = [
                    f"💰 **Статус бюджета**\n",
                    f"📅 До зарплаты: {days_until_salary} дней\n"
                ]
                
                for limit in limits:
                    category = db.query(Category).filter(Category.id == limit.category_id).first()
                    if not category:
                        continue
                    
                    # Вычисляем потраченную сумму с последней зарплаты
                    last_salary_date = self._get_last_salary_date(today, user.salary_date)
                    spent = self._calculate_spent_since_date(db, user.id, limit.category_id, last_salary_date, limit.currency)
                    
                    remaining = limit.amount - spent
                    daily_budget = remaining / max(days_until_salary, 1) if days_until_salary > 0 else 0
                    
                    category_emoji = category.emoji if hasattr(category, 'emoji') and category.emoji else "📁"
                    
                    message_parts.append(
                        f"{category_emoji} **{category.name}**\n"
                        f"   Осталось: {remaining:.2f} {limit.currency}\n"
                        f"   Можно тратить в день: {daily_budget:.2f} {limit.currency}\n"
                    )
                
                message = "\n".join(message_parts)
                
                await self.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Отправлен статус бюджета пользователю {user.telegram_id}")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Ошибка отправки статуса бюджета пользователю {user.telegram_id}: {e}")
    
    def _get_next_salary_date(self, current_date: datetime.date, salary_day: int) -> datetime.date:
        """Получить следующую дату зарплаты"""
        current_month = current_date.month
        current_year = current_date.year
        
        # Пробуем текущий месяц
        try:
            next_salary = current_date.replace(day=salary_day)
            if next_salary > current_date:
                return next_salary
        except ValueError:
            # Если day больше количества дней в месяце, берем последний день
            import calendar
            last_day = calendar.monthrange(current_year, current_month)[1]
            next_salary = current_date.replace(day=min(salary_day, last_day))
            if next_salary > current_date:
                return next_salary
        
        # Если не подходит текущий месяц, берем следующий
        next_month = current_month + 1
        next_year = current_year
        if next_month > 12:
            next_month = 1
            next_year += 1
        
        try:
            return datetime.date(next_year, next_month, salary_day)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(next_year, next_month)[1]
            return datetime.date(next_year, next_month, min(salary_day, last_day))
    
    def _get_last_salary_date(self, current_date: datetime.date, salary_day: int) -> datetime.date:
        """Получить последнюю дату зарплаты"""
        current_month = current_date.month
        current_year = current_date.year
        
        # Пробуем текущий месяц
        try:
            last_salary = current_date.replace(day=salary_day)
            if last_salary <= current_date:
                return last_salary
        except ValueError:
            # Если day больше количества дней в месяце, берем последний день
            import calendar
            last_day = calendar.monthrange(current_year, current_month)[1]
            last_salary = current_date.replace(day=min(salary_day, last_day))
            if last_salary <= current_date:
                return last_salary
        
        # Если не подходит текущий месяц, берем предыдущий
        prev_month = current_month - 1
        prev_year = current_year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        
        try:
            return datetime.date(prev_year, prev_month, salary_day)
        except ValueError:
            import calendar
            last_day = calendar.monthrange(prev_year, prev_month)[1]
            return datetime.date(prev_year, prev_month, min(salary_day, last_day))
    
    def _calculate_spent_since_date(self, db, user_id: int, category_id: int, since_date: datetime.date, currency: str) -> float:
        """Вычислить потраченную сумму с определенной даты"""
        since_datetime = datetime.combine(since_date, time.min)
        
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.currency == currency,
            Transaction.amount < 0,  # Только расходы
            Transaction.created_at >= since_datetime
        ).all()
        
        return sum(abs(transaction.amount) for transaction in transactions)