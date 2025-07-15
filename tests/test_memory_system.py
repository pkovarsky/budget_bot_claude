#!/usr/bin/env python3
"""
Тесты для системы памяти категорий
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.category_memory_service import CategoryMemoryService
from database import get_db_session, User, Category, CategoryMemory
import unittest

class TestMemorySystem(unittest.TestCase):
    
    def setUp(self):
        """Настройка тестов"""
        self.memory_service = CategoryMemoryService()
        self.test_user_id = 999999  # Тестовый пользователь
        
        # Очищаем тестовые данные
        db = get_db_session()
        try:
            db.query(CategoryMemory).filter(CategoryMemory.user_id == self.test_user_id).delete()
            db.commit()
        finally:
            db.close()
    
    def tearDown(self):
        """Очистка после тестов"""
        db = get_db_session()
        try:
            db.query(CategoryMemory).filter(CategoryMemory.user_id == self.test_user_id).delete()
            db.commit()
        finally:
            db.close()
    
    def test_normalize_description(self):
        """Тест нормализации описаний"""
        test_cases = [
            ("продукты в магазине", "продукты в магазине"),
            ("ПРОДУКТЫ В МАГАЗИНЕ!!!", "продукты в магазине"),
            ("  много   пробелов  ", "много пробелов"),
            ("товары 25.5 EUR", "товары"),
            ("кафе №1", "кафе"),
        ]
        
        for input_text, expected in test_cases:
            result = self.memory_service.normalize_description(input_text)
            self.assertEqual(result, expected, f"Ошибка для '{input_text}': ожидалось '{expected}', получено '{result}'")
    
    def test_remember_and_suggest(self):
        """Тест запоминания и предложения категорий"""
        # Временно понижаем порог для теста
        original_threshold = self.memory_service.min_confidence
        self.memory_service.min_confidence = 0.5
        
        try:
            # Запоминаем связь
            self.memory_service.remember_category(
                user_id=self.test_user_id,
                description="продукты в супермаркете",
                category_id=1,
                confidence=1.0
            )
            
            # Проверяем предложение для похожего описания
            suggestion = self.memory_service.suggest_category(
                user_id=self.test_user_id,
                description="продукты в магазине"
            )
            
            self.assertIsNotNone(suggestion, "Система должна найти похожее описание")
            if suggestion:
                self.assertEqual(suggestion['category_id'], 1)
                self.assertGreater(suggestion['confidence'], 0.5)
        finally:
            # Восстанавливаем исходный порог
            self.memory_service.min_confidence = original_threshold
    
    def test_extract_keywords(self):
        """Тест извлечения ключевых слов"""
        description = "покупка продуктов в большом магазине"
        keywords = self.memory_service.extract_keywords(description)
        
        expected_keywords = ["покупка", "продуктов", "большом", "магазине"]
        self.assertEqual(sorted(keywords), sorted(expected_keywords))
    
    def test_similarity_calculation(self):
        """Тест вычисления схожести"""
        text1 = "продукты магазин"
        text2 = "продукты в магазине"
        
        similarity = self.memory_service.calculate_similarity(text1, text2)
        self.assertGreater(similarity, 0.7, "Схожие тексты должны иметь высокую схожесть")
        
        text3 = "совсем другой текст"
        similarity2 = self.memory_service.calculate_similarity(text1, text3)
        self.assertLess(similarity2, 0.3, "Разные тексты должны иметь низкую схожесть")

def run_tests():
    """Запуск всех тестов"""
    print("🧪 Запуск тестов системы памяти категорий...")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMemorySystem)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("✅ Все тесты пройдены успешно!")
        return True
    else:
        print("❌ Некоторые тесты провалились")
        return False

if __name__ == "__main__":
    run_tests()