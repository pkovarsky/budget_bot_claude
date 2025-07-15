import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import json

from database import get_db_session, User, Category, Transaction, Limit, Base, engine
from services.openai_service import OpenAIService
from services.chart_service import ChartService
from handlers.enhanced_transaction_handler import EnhancedTransactionHandler
from handlers.categories_handler import categories_command, handle_categories_callback
from handlers.stats_handler import stats_command, handle_stats_callback, handle_charts_callback
from utils.parsers import parse_transaction


class TestDatabase:
    def setup_method(self):
        """Настройка для каждого теста"""
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        
        # Создаем тестового пользователя
        db = get_db_session()
        try:
            self.test_user = User(
                telegram_id=123456,
                username="test_user",
                name="Test User",
                language="ru"
            )
            db.add(self.test_user)
            db.commit()
            
            # Создаем тестовые категории
            self.test_categories = [
                Category(name="Продукты", user_id=self.test_user.id, is_default=True),
                Category(name="Транспорт", user_id=self.test_user.id, is_default=True),
                Category(name="Развлечения", user_id=self.test_user.id, is_default=True),
                Category(name="Прочее", user_id=self.test_user.id, is_default=True),
            ]
            for cat in self.test_categories:
                db.add(cat)
            db.commit()
            
        finally:
            db.close()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        db = get_db_session()
        try:
            db.query(Transaction).delete()
            db.query(Limit).delete()
            db.query(Category).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()
    
    def test_user_creation(self):
        """Тест создания пользователя"""
        db = get_db_session()
        try:
            user = db.query(User).filter(User.telegram_id == 123456).first()
            assert user is not None
            assert user.username == "test_user"
            assert user.name == "Test User"
            assert user.language == "ru"
        finally:
            db.close()
    
    def test_category_creation(self):
        """Тест создания категорий"""
        db = get_db_session()
        try:
            categories = db.query(Category).filter(Category.user_id == self.test_user.id).all()
            assert len(categories) == 4
            category_names = [cat.name for cat in categories]
            assert "Продукты" in category_names
            assert "Транспорт" in category_names
            assert "Развлечения" in category_names
            assert "Прочее" in category_names
        finally:
            db.close()
    
    def test_transaction_creation(self):
        """Тест создания транзакции"""
        db = get_db_session()
        try:
            category = db.query(Category).filter(Category.name == "Продукты").first()
            
            transaction = Transaction(
                user_id=self.test_user.id,
                category_id=category.id,
                amount=-25.50,
                currency="EUR",
                description="Покупка продуктов"
            )
            db.add(transaction)
            db.commit()
            
            # Проверяем, что транзакция создана
            saved_transaction = db.query(Transaction).filter(Transaction.user_id == self.test_user.id).first()
            assert saved_transaction is not None
            assert saved_transaction.amount == -25.50
            assert saved_transaction.currency == "EUR"
            assert saved_transaction.description == "Покупка продуктов"
            assert saved_transaction.category_id == category.id
        finally:
            db.close()
    
    def test_user_specific_categories(self):
        """Тест того, что категории привязаны к пользователю"""
        db = get_db_session()
        try:
            # Создаем второго пользователя
            user2 = User(
                telegram_id=789012,
                username="test_user2",
                language="en"
            )
            db.add(user2)
            db.commit()
            
            # Создаем категорию для второго пользователя
            category2 = Category(name="Food", user_id=user2.id, is_default=True)
            db.add(category2)
            db.commit()
            
            # Проверяем, что каждый пользователь видит только свои категории
            user1_categories = db.query(Category).filter(Category.user_id == self.test_user.id).all()
            user2_categories = db.query(Category).filter(Category.user_id == user2.id).all()
            
            assert len(user1_categories) == 4
            assert len(user2_categories) == 1
            
            user1_names = [cat.name for cat in user1_categories]
            user2_names = [cat.name for cat in user2_categories]
            
            assert "Продукты" in user1_names
            assert "Food" in user2_names
            assert "Food" not in user1_names
            assert "Продукты" not in user2_names
        finally:
            db.close()


class TestTransactionParser:
    def test_parse_expense_transaction(self):
        """Тест парсинга расходной транзакции"""
        result = parse_transaction("25.50 EUR продукты")
        assert result is not None
        assert result['amount'] == 25.50
        assert result['currency'] == 'EUR'
        assert result['description'] == 'продукты'
        assert result['is_income'] == False
    
    def test_parse_income_transaction(self):
        """Тест парсинга доходной транзакции"""
        result = parse_transaction("+2000 EUR зарплата")
        assert result is not None
        assert result['amount'] == 2000
        assert result['currency'] == 'EUR'
        assert result['description'] == 'зарплата'
        assert result['is_income'] == True
    
    def test_parse_different_currencies(self):
        """Тест парсинга разных валют"""
        test_cases = [
            ("100 USD покупка", 100, "USD"),
            ("50 евро еда", 50, "EUR"),
            ("300 гривен транспорт", 300, "UAH"),
            ("75 € кафе", 75, "EUR"),
            ("200 $ одежда", 200, "USD"),
        ]
        
        for text, expected_amount, expected_currency in test_cases:
            result = parse_transaction(text)
            assert result is not None
            assert result['amount'] == expected_amount
            assert result['currency'] == expected_currency
    
    def test_parse_invalid_transactions(self):
        """Тест парсинга некорректных транзакций"""
        invalid_cases = [
            "просто текст",
            "EUR 25 продукты",  # неправильный порядок
            "25 неизвестная_валюта продукты",
            "",
            "25",
            "EUR продукты",
        ]
        
        for text in invalid_cases:
            result = parse_transaction(text)
            assert result is None


class TestOpenAIService:
    def setup_method(self):
        """Настройка для каждого теста"""
        self.service = OpenAIService()
        self.existing_categories = ["Продукты", "Транспорт", "Развлечения", "Здоровье", "Прочее"]
    
    def test_categorize_exact_match(self):
        """Тест точного совпадения категории"""
        result = asyncio.run(self.service.categorize_transaction("Продукты", self.existing_categories))
        assert result == "Продукты"
    
    def test_categorize_substring_match(self):
        """Тест совпадения подстроки"""
        result = asyncio.run(self.service.categorize_transaction("покупка продукты", self.existing_categories))
        assert result == "Продукты"
    
    def test_local_categorization_food(self):
        """Тест локальной категоризации для продуктов"""
        test_cases = [
            "покупка в ашане",
            "lidl магазин",
            "хлеб и молоко",
            "grocery shopping",
            "еда на дом",
        ]
        
        for description in test_cases:
            result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
            assert result == "Продукты"
    
    def test_local_categorization_transport(self):
        """Тест локальной категоризации для транспорта"""
        test_cases = [
            "такси до дома",
            "uber поездка",
            "заправка автомобиля",
            "билет на автобус",
            "parking fee",
        ]
        
        for description in test_cases:
            result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
            assert result == "Транспорт"
    
    def test_local_categorization_entertainment(self):
        """Тест локальной категоризации для развлечений"""
        test_cases = [
            "билет в кино",
            "концерт группы",
            "фитнес зал",
            "спорт клуб",
            "музей искусств",
        ]
        
        for description in test_cases:
            result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
            assert result == "Развлечения"
    
    def test_local_categorization_health(self):
        """Тест локальной категоризации для здоровья"""
        test_cases = [
            "аптека лекарства",
            "визит к врачу",
            "стоматолог лечение",
            "витамины покупка",
            "анализы крови",
        ]
        
        for description in test_cases:
            result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
            assert result == "Здоровье"
    
    def test_currency_normalization(self):
        """Тест нормализации валют"""
        test_cases = [
            ("EUR", "EUR"),
            ("EURO", "EUR"),
            ("евро", "EUR"),
            ("USD", "USD"),
            ("DOLLAR", "USD"),
            ("доллар", "USD"),
            ("UAH", "UAH"),
            ("гривна", "UAH"),
            ("unknown", "EUR"),  # fallback
        ]
        
        for input_currency, expected in test_cases:
            result = self.service._normalize_currency_from_receipt(input_currency)
            assert result == expected


class TestChartService:
    def setup_method(self):
        """Настройка для каждого теста"""
        self.chart_service = ChartService()
        
        # Создаем тестовые данные в базе
        Base.metadata.create_all(bind=engine)
        
        db = get_db_session()
        try:
            self.test_user = User(
                telegram_id=123456,
                username="test_user",
                language="ru"
            )
            db.add(self.test_user)
            db.commit()
            
            # Создаем категории
            categories = [
                Category(name="Продукты", user_id=self.test_user.id, is_default=True),
                Category(name="Транспорт", user_id=self.test_user.id, is_default=True),
                Category(name="Развлечения", user_id=self.test_user.id, is_default=True),
            ]
            for cat in categories:
                db.add(cat)
            db.commit()
            
            # Создаем тестовые транзакции
            transactions = [
                Transaction(user_id=self.test_user.id, category_id=categories[0].id, amount=-100, currency="EUR", description="Продукты"),
                Transaction(user_id=self.test_user.id, category_id=categories[1].id, amount=-50, currency="EUR", description="Транспорт"),
                Transaction(user_id=self.test_user.id, category_id=categories[2].id, amount=-75, currency="EUR", description="Развлечения"),
                Transaction(user_id=self.test_user.id, category_id=categories[0].id, amount=-80, currency="EUR", description="Еще продукты"),
            ]
            for transaction in transactions:
                db.add(transaction)
            db.commit()
            
        finally:
            db.close()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        db = get_db_session()
        try:
            db.query(Transaction).delete()
            db.query(Category).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()
    
    def test_generate_pie_chart(self):
        """Тест генерации круговой диаграммы"""
        buffer = self.chart_service.generate_category_pie_chart(self.test_user.telegram_id, 30)
        assert buffer is not None
        assert isinstance(buffer, BytesIO)
        
        # Проверяем, что это действительно изображение
        buffer.seek(0)
        image = Image.open(buffer)
        assert image.format == 'PNG'
        assert image.size[0] > 0
        assert image.size[1] > 0
    
    def test_generate_trends_chart(self):
        """Тест генерации графика трендов"""
        buffer = self.chart_service.generate_spending_trends_chart(self.test_user.telegram_id, 30)
        assert buffer is not None
        assert isinstance(buffer, BytesIO)
        
        buffer.seek(0)
        image = Image.open(buffer)
        assert image.format == 'PNG'
    
    def test_generate_monthly_chart(self):
        """Тест генерации месячного сравнения"""
        buffer = self.chart_service.generate_monthly_comparison_chart(self.test_user.telegram_id, 6)
        assert buffer is not None
        assert isinstance(buffer, BytesIO)
        
        buffer.seek(0)
        image = Image.open(buffer)
        assert image.format == 'PNG'
    
    def test_no_data_charts(self):
        """Тест генерации графиков при отсутствии данных"""
        # Создаем пользователя без транзакций
        db = get_db_session()
        try:
            user_no_data = User(
                telegram_id=999999,
                username="no_data_user",
                language="ru"
            )
            db.add(user_no_data)
            db.commit()
            
            # Все графики должны вернуть None
            pie_chart = self.chart_service.generate_category_pie_chart(user_no_data.telegram_id, 30)
            trends_chart = self.chart_service.generate_spending_trends_chart(user_no_data.telegram_id, 30)
            monthly_chart = self.chart_service.generate_monthly_comparison_chart(user_no_data.telegram_id, 6)
            
            assert pie_chart is None
            assert trends_chart is None
            assert monthly_chart is None
            
        finally:
            db.close()
    
    def test_color_generation(self):
        """Тест генерации цветов"""
        colors_3 = self.chart_service._generate_colors(3)
        assert len(colors_3) == 3
        
        colors_25 = self.chart_service._generate_colors(25)
        assert len(colors_25) == 25
        
        # Проверяем, что цвета не повторяются
        assert len(set(colors_3)) == 3
    
    def test_amount_formatting(self):
        """Тест форматирования сумм"""
        assert self.chart_service._format_amount(500) == "500"
        assert self.chart_service._format_amount(1500) == "1.5k"
        assert self.chart_service._format_amount(2000) == "2.0k"
        assert self.chart_service._format_amount(25.67) == "26"


class TestHandlers:
    def setup_method(self):
        """Настройка для каждого теста"""
        Base.metadata.create_all(bind=engine)
        
        db = get_db_session()
        try:
            self.test_user = User(
                telegram_id=123456,
                username="test_user",
                language="ru"
            )
            db.add(self.test_user)
            db.commit()
            
            # Создаем категории
            self.categories = [
                Category(name="Продукты", user_id=self.test_user.id, is_default=True),
                Category(name="Транспорт", user_id=self.test_user.id, is_default=True),
                Category(name="Прочее", user_id=self.test_user.id, is_default=True),
            ]
            for cat in self.categories:
                db.add(cat)
            db.commit()
            
        finally:
            db.close()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        db = get_db_session()
        try:
            db.query(Transaction).delete()
            db.query(Limit).delete()
            db.query(Category).delete()
            db.query(User).delete()
            db.commit()
        finally:
            db.close()
    
    @patch('handlers.enhanced_transaction_handler.OpenAIService')
    def test_transaction_handler_expense(self, mock_openai):
        """Тест обработки расходной транзакции"""
        handler = EnhancedTransactionHandler()
        
        # Создаем mock объекты для Telegram
        update = Mock()
        update.message.text = "25.50 EUR продукты"
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        
        # Мокаем OpenAI service
        mock_openai.return_value.categorize_transaction = AsyncMock(return_value="Продукты")
        
        # Запускаем обработчик
        asyncio.run(handler.handle_message(update, context))
        
        # Проверяем, что транзакция была создана
        db = get_db_session()
        try:
            transaction = db.query(Transaction).filter(Transaction.user_id == 123456).first()
            assert transaction is not None
            assert transaction.amount == -25.50
            assert transaction.currency == "EUR"
            assert transaction.description == "продукты"
        finally:
            db.close()
    
    @patch('handlers.enhanced_transaction_handler.OpenAIService')
    def test_transaction_handler_income(self, mock_openai):
        """Тест обработки доходной транзакции"""
        handler = EnhancedTransactionHandler()
        
        update = Mock()
        update.message.text = "+2000 EUR зарплата"
        update.effective_user.id = 123456
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.user_data = {}
        
        # Мокаем OpenAI service
        mock_openai.return_value.categorize_transaction = AsyncMock(return_value="Прочее")
        
        asyncio.run(handler.handle_message(update, context))
        
        # Проверяем, что транзакция была создана
        db = get_db_session()
        try:
            transaction = db.query(Transaction).filter(Transaction.user_id == 123456).first()
            assert transaction is not None
            assert transaction.amount == 2000
            assert transaction.currency == "EUR"
            assert transaction.description == "зарплата"
        finally:
            db.close()


class TestCostOptimization:
    def setup_method(self):
        """Настройка для каждого теста"""
        self.service = OpenAIService()
        self.existing_categories = ["Продукты", "Транспорт", "Развлечения", "Здоровье", "Прочее"]
    
    @patch('openai_service.OpenAIService.client.chat.completions.create')
    def test_local_categorization_prevents_openai_call(self, mock_openai):
        """Тест того, что локальная категоризация предотвращает вызов OpenAI"""
        # Тест случаев, когда OpenAI не должен вызываться
        test_cases = [
            "покупка в ашане",  # должен найти "Продукты"
            "такси до дома",    # должен найти "Транспорт"
            "билет в кино",     # должен найти "Развлечения"
            "аптека лекарства", # должен найти "Здоровье"
        ]
        
        for description in test_cases:
            result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
            
            # Проверяем, что результат не "Прочее" (значит, локальная категоризация сработала)
            assert result != "Прочее"
            
            # Проверяем, что OpenAI не вызывался
            mock_openai.assert_not_called()
            
            # Сбрасываем mock для следующего теста
            mock_openai.reset_mock()
    
    @patch('openai_service.OpenAIService.client.chat.completions.create')
    def test_openai_called_only_when_needed(self, mock_openai):
        """Тест того, что OpenAI вызывается только при необходимости"""
        # Настраиваем mock для возврата результата
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Прочее"
        mock_openai.return_value = mock_response
        
        # Описание, которое не должно быть распознано локально
        description = "очень специфичное описание которое не попадает ни в одну категорию"
        
        result = asyncio.run(self.service.categorize_transaction(description, self.existing_categories))
        
        # Проверяем, что OpenAI был вызван
        mock_openai.assert_called_once()
        
        # Проверяем, что результат правильный
        assert result == "Прочее"
    
    def test_exact_match_prevents_all_processing(self):
        """Тест того, что точное совпадение предотвращает дальнейшую обработку"""
        with patch.object(self.service, '_categorize_locally') as mock_local:
            with patch.object(self.service.client.chat.completions, 'create') as mock_openai:
                
                result = asyncio.run(self.service.categorize_transaction("Продукты", self.existing_categories))
                
                # Проверяем, что точное совпадение сработало
                assert result == "Продукты"
                
                # Проверяем, что локальная категоризация и OpenAI не вызывались
                mock_local.assert_not_called()
                mock_openai.assert_not_called()
    
    def test_substring_match_prevents_further_processing(self):
        """Тест того, что совпадение подстроки предотвращает дальнейшую обработку"""
        with patch.object(self.service, '_categorize_locally') as mock_local:
            with patch.object(self.service.client.chat.completions, 'create') as mock_openai:
                
                result = asyncio.run(self.service.categorize_transaction("покупка продукты", self.existing_categories))
                
                # Проверяем, что совпадение подстроки сработало
                assert result == "Продукты"
                
                # Проверяем, что локальная категоризация и OpenAI не вызывались
                mock_local.assert_not_called()
                mock_openai.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])