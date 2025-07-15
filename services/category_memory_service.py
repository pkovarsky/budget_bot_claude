import re
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from database import get_db_session, CategoryMemory, Category
from sqlalchemy import func, and_, or_

logger = logging.getLogger(__name__)

class CategoryMemoryService:
    """
    Сервис для запоминания и предсказания категорий на основе описаний
    """
    
    def __init__(self):
        self.min_confidence = 0.7  # Минимальная уверенность для автоматического предложения
        self.similarity_threshold = 0.8  # Порог схожести для считания паттернов похожими
    
    def normalize_description(self, description: str) -> str:
        """
        Нормализует описание для сравнения
        """
        if not description:
            return ""
        
        # Приводим к нижнему регистру
        normalized = description.lower().strip()
        
        # Удаляем лишние пробелы
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Удаляем знаки препинания
        normalized = re.sub(r'[^\w\s]', '', normalized)
        
        # Удаляем числа и валюты (суммы, количества)
        normalized = re.sub(r'\d+(?:\.\d+)?', '', normalized)
        normalized = re.sub(r'\b(?:eur|usd|euro|евро|доллар)\b', '', normalized)
        
        # Удаляем лишние пробелы после обработки
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def extract_keywords(self, description: str) -> List[str]:
        """
        Извлекает ключевые слова из описания
        """
        normalized = self.normalize_description(description)
        
        # Разбиваем на слова
        words = normalized.split()
        
        # Фильтруем короткие слова и стоп-слова
        stop_words = {'в', 'на', 'по', 'для', 'из', 'с', 'и', 'или', 'но', 'к', 'от', 'до', 'за', 'при', 'под'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        return keywords
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет схожесть между двумя текстами
        """
        if not text1 or not text2:
            return 0.0
        
        # Используем SequenceMatcher для вычисления схожести
        return SequenceMatcher(None, text1, text2).ratio()
    
    def find_best_match(self, user_id: int, description: str) -> Optional[Tuple[int, float]]:
        """
        Находит лучшее совпадение категории для описания
        Возвращает (category_id, confidence) или None
        """
        if not description:
            return None
        
        db = get_db_session()
        try:
            normalized_desc = self.normalize_description(description)
            keywords = self.extract_keywords(description)
            
            # Получаем все записи памяти для пользователя
            memory_records = db.query(CategoryMemory).filter(
                CategoryMemory.user_id == user_id
            ).all()
            
            best_match = None
            best_score = 0.0
            
            for record in memory_records:
                # Проверяем точное совпадение нормализованного описания
                pattern_similarity = self.calculate_similarity(
                    normalized_desc, 
                    record.description_pattern
                )
                
                # Проверяем совпадение ключевых слов
                record_keywords = self.extract_keywords(record.description_pattern)
                keyword_matches = sum(1 for kw in keywords if kw in record_keywords)
                keyword_score = keyword_matches / max(len(keywords), 1) if keywords else 0
                
                # Комбинированный скор с учетом популярности паттерна
                popularity_boost = min(record.usage_count / 10, 0.2)  # Бонус до 20% за популярность
                combined_score = (pattern_similarity * 0.6 + keyword_score * 0.4 + popularity_boost) * record.confidence
                
                if combined_score > best_score and combined_score > self.min_confidence:
                    best_score = combined_score
                    best_match = (record.category_id, combined_score)
            
            return best_match
            
        except Exception as e:
            logger.error(f"Ошибка при поиске совпадения категории: {e}")
            return None
        finally:
            db.close()
    
    def remember_category(self, user_id: int, description: str, category_id: int, confidence: float = 1.0):
        """
        Запоминает связь описания с категорией
        """
        if not description or not category_id:
            return
        
        db = get_db_session()
        try:
            normalized_desc = self.normalize_description(description)
            
            # Ищем существующий паттерн
            existing = db.query(CategoryMemory).filter(
                and_(
                    CategoryMemory.user_id == user_id,
                    CategoryMemory.description_pattern == normalized_desc,
                    CategoryMemory.category_id == category_id
                )
            ).first()
            
            if existing:
                # Обновляем существующую запись
                existing.usage_count += 1
                existing.last_used = datetime.utcnow()
                existing.confidence = min(existing.confidence + 0.1, 1.0)  # Увеличиваем уверенность
            else:
                # Проверяем, есть ли похожие паттерны
                similar_pattern = self.find_similar_pattern(db, user_id, normalized_desc)
                
                if similar_pattern and similar_pattern.category_id == category_id:
                    # Обновляем похожий паттерн
                    similar_pattern.usage_count += 1
                    similar_pattern.last_used = datetime.utcnow()
                    similar_pattern.confidence = min(similar_pattern.confidence + 0.05, 1.0)
                else:
                    # Создаем новую запись
                    new_memory = CategoryMemory(
                        user_id=user_id,
                        description_pattern=normalized_desc,
                        category_id=category_id,
                        confidence=confidence,
                        usage_count=1,
                        last_used=datetime.utcnow()
                    )
                    db.add(new_memory)
            
            db.commit()
            logger.info(f"Запомнена категория {category_id} для паттерна '{normalized_desc}'")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при сохранении в память: {e}")
        finally:
            db.close()
    
    def find_similar_pattern(self, db, user_id: int, pattern: str) -> Optional[CategoryMemory]:
        """
        Находит похожий паттерн в памяти
        """
        memory_records = db.query(CategoryMemory).filter(
            CategoryMemory.user_id == user_id
        ).all()
        
        for record in memory_records:
            similarity = self.calculate_similarity(pattern, record.description_pattern)
            if similarity >= self.similarity_threshold:
                return record
        
        return None
    
    def get_user_patterns(self, user_id: int) -> List[dict]:
        """
        Получает все паттерны пользователя для анализа
        """
        db = get_db_session()
        try:
            patterns = db.query(
                CategoryMemory.description_pattern,
                Category.name.label('category_name'),
                CategoryMemory.usage_count,
                CategoryMemory.confidence,
                CategoryMemory.last_used
            ).join(
                Category, CategoryMemory.category_id == Category.id
            ).filter(
                CategoryMemory.user_id == user_id
            ).order_by(CategoryMemory.usage_count.desc()).all()
            
            return [
                {
                    'pattern': p.description_pattern,
                    'category': p.category_name,
                    'usage_count': p.usage_count,
                    'confidence': p.confidence,
                    'last_used': p.last_used
                }
                for p in patterns
            ]
        except Exception as e:
            logger.error(f"Ошибка при получении паттернов: {e}")
            return []
        finally:
            db.close()
    
    def cleanup_old_patterns(self, user_id: int, days_threshold: int = 90):
        """
        Очищает старые неиспользуемые паттерны
        """
        db = get_db_session()
        try:
            threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            # Удаляем паттерны с низкой уверенностью и редким использованием
            deleted = db.query(CategoryMemory).filter(
                and_(
                    CategoryMemory.user_id == user_id,
                    CategoryMemory.last_used < threshold_date,
                    CategoryMemory.confidence < 0.5,
                    CategoryMemory.usage_count < 3
                )
            ).delete()
            
            db.commit()
            logger.info(f"Удалено {deleted} устаревших паттернов для пользователя {user_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Ошибка при очистке паттернов: {e}")
        finally:
            db.close()
    
    def suggest_category(self, user_id: int, description: str) -> Optional[dict]:
        """
        Предлагает категорию на основе описания
        Возвращает словарь с информацией о предложении или None
        """
        match = self.find_best_match(user_id, description)
        
        if not match:
            return None
        
        category_id, confidence = match
        
        # Получаем информацию о категории
        db = get_db_session()
        try:
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                return None
            
            return {
                'category_id': category_id,
                'category_name': category.name,
                'category_emoji': category.emoji,
                'confidence': confidence,
                'auto_suggest': confidence >= 0.9  # Автоматически предлагать при высокой уверенности
            }
        finally:
            db.close()