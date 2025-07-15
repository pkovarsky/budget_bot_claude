from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    name = Column(String, nullable=True)  # Имя пользователя для персонализации
    language = Column(String, default="ru")  # ru, en, uk
    timezone = Column(String, default="Europe/Amsterdam")  # Часовой пояс пользователя
    
    # Настройки напоминаний
    daily_reminder_enabled = Column(Boolean, default=False)
    daily_reminder_time = Column(Time, nullable=True)  # Время напоминания о тратах
    
    # Настройки уведомлений о бюджете
    budget_notifications_enabled = Column(Boolean, default=False)
    budget_notification_frequency = Column(String, default="daily")  # daily, weekly, none
    budget_notification_time = Column(Time, nullable=True)
    
    # Дата зачисления зарплаты
    salary_date = Column(Integer, nullable=True)  # День месяца (1-31)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user")
    categories = relationship("Category", back_populates="user")
    limits = relationship("Limit", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    emoji = Column(String, default="📁")  # Смайлик для категории
    user_id = Column(Integer, ForeignKey("users.id"))
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    subcategories = relationship("Subcategory", back_populates="category")

class Subcategory(Base):
    __tablename__ = "subcategories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    emoji = Column(String, default="📂")  # Смайлик для подкатегории
    category_id = Column(Integer, ForeignKey("categories.id"))
    user_id = Column(Integer, ForeignKey("users.id"))  # Для быстрого доступа
    created_at = Column(DateTime, default=datetime.utcnow)
    
    category = relationship("Category", back_populates="subcategories")
    user = relationship("User")
    transactions = relationship("Transaction", back_populates="subcategory")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=True)
    amount = Column(Float)
    currency = Column(String, default="EUR")
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    subcategory = relationship("Subcategory", back_populates="transactions")

class Limit(Base):
    __tablename__ = "limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    amount = Column(Float)
    currency = Column(String, default="EUR")
    period = Column(String, default="monthly")  # daily, weekly, monthly
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="limits")
    category = relationship("Category")

class CategoryMemory(Base):
    __tablename__ = "category_memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    description_pattern = Column(String, index=True)  # Паттерн описания (нормализованный)
    category_id = Column(Integer, ForeignKey("categories.id"))
    confidence = Column(Float, default=1.0)  # Уверенность в соответствии (0.0-1.0)
    usage_count = Column(Integer, default=1)  # Сколько раз использовался
    last_used = Column(DateTime, default=datetime.utcnow)  # Когда последний раз использовался
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    category = relationship("Category")

engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    return SessionLocal()