import openai
import json
import config
from typing import List, Dict, Optional
import logging
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    
    async def categorize_transaction(self, description: str, existing_categories: List[str]) -> str:
        """Определяет категорию транзакции на основе описания."""

        desc_lower = description.lower().strip()

        # Сначала проверяем точное совпадение с существующей категорией
        for cat in existing_categories:
            if desc_lower == cat.lower():
                return cat

        # Затем ищем категорию как подстроку в описании
        for cat in existing_categories:
            if cat.lower() in desc_lower:
                return cat

        prompt = f"""
        Определи наиболее подходящую категорию для транзакции: "{description}"

        Доступные категории: {', '.join(existing_categories)}

        Верни только название категории из списка доступных категорий.
        Если ни одна не подходит, верни "Прочее".
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник для категоризации транзакций. Отвечай только названием категории."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )

            category = response.choices[0].message.content.strip()
            if category in existing_categories:
                return category

        except Exception as e:
            logger.error(f"Ошибка при обращении к OpenAI: {e}")

        # Fallback
        return "Прочее"
    
    async def analyze_receipt_image(self, image_data: bytes) -> List[Dict]:
        """
        Анализирует изображение чека и извлекает транзакции
        """
        try:
            # Конвертируем изображение в base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            prompt = """
            Проанализируй этот чек и извлеки все покупки.
            Верни результат в формате JSON:
            {
                "currency": "валюта (например, EUR, USD)",
                "total_amount": общая_сумма,
                "store_name": "название_магазина",
                "date": "дата в формате YYYY-MM-DD",
                "items": [
                    {
                        "name": "название_товара",
                        "price": цена,
                        "quantity": количество,
                        "category": "предполагаемая_категория"
                    }
                ]
            }
            
            Если не удается определить какое-либо поле, укажи null.
            Категории: Продукты, Транспорт, Развлечения, Здоровье, Одежда, Коммунальные услуги, Ресторан, Прочее.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Модель с поддержкой изображений
                messages=[
                    {
                        "role": "system",
                        "content": "Ты эксперт по распознаванию чеков. Всегда отвечай в JSON формате."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Очищаем ответ от markdown разметки
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            result = json.loads(content)
            
            # Проверяем обязательные поля
            if not isinstance(result, dict) or 'items' not in result:
                logger.error(f"Некорректный формат ответа: {result}")
                return []
            
            # Нормализуем данные
            transactions = []
            
            # Если есть общая сумма, создаем одну транзакцию
            if result.get('total_amount'):
                store_name = result.get('store_name', 'Магазин')
                description = f"{store_name} (чек)"
                
                transactions.append({
                    'amount': float(result['total_amount']),
                    'currency': self._normalize_currency_from_receipt(result.get('currency', 'EUR')),
                    'description': description,
                    'is_income': False
                })
            
            # Альтернативно - создаем отдельные транзакции для каждого товара
            # (!выключено по умолчанию, чтобы не дублировать)
            
            return transactions
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return []
        except Exception as e:
            logger.error(f"Ошибка при анализе чека: {e}")
            return []
    
    def _normalize_currency_from_receipt(self, currency: str) -> str:
        """Нормализация валюты из чека"""
        if not currency:
            return 'EUR'
        
        currency = currency.upper().strip()
        
        # Маппинг валют
        currency_mapping = {
            'EUR': 'EUR', 'EURO': 'EUR', 'EUROS': 'EUR', 'ЕВРО': 'EUR',
            'USD': 'USD', 'DOLLAR': 'USD', 'DOLLARS': 'USD', 'ДОЛЛАР': 'USD',
            'UAH': 'UAH', 'HRYVNIA': 'UAH', 'ГРИВНА': 'UAH'
        }
        
        return currency_mapping.get(currency, 'EUR')
    
    async def process_receipt_photo(self, image_data: bytes, user_categories: List[str]) -> List[Dict]:
        """
        Полная обработка фото чека с категоризацией
        """
        try:
            # Анализируем чек
            transactions = await self.analyze_receipt_image(image_data)
            
            if not transactions:
                return []
            
            # Категоризируем каждую транзакцию
            categorized_transactions = []
            for transaction in transactions:
                category = await self.categorize_transaction(
                    transaction['description'], 
                    user_categories
                )
                transaction['category'] = category
                categorized_transactions.append(transaction)
            
            return categorized_transactions
            
        except Exception as e:
            logger.error(f"Ошибка при обработке фото чека: {e}")
            return []
    
    def categorize_expense(self, description: str, amount: float, existing_categories: List[str]) -> Dict:
        """
        Определяет категорию расхода на основе описания и суммы (устаревший метод)
        """
        # Используем новый метод для обратной совместимости
        import asyncio
        try:
            category = asyncio.run(self.categorize_transaction(description, existing_categories))
            return {
                "category": category,
                "confidence": 0.8,
                "suggest_new_category": False,
                "suggested_category_name": None
            }
        except Exception as e:
            logger.error(f"Ошибка в categorize_expense: {e}")
            return {
                "category": "Прочее",
                "confidence": 0.5,
                "suggest_new_category": False,
                "suggested_category_name": None
            }