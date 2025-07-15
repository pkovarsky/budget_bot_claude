import openai
import json
import config
from typing import List, Dict, Optional
import logging
import base64

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

        # Продвинутая местная категоризация на основе ключевых слов
        local_category = OpenAIService._categorize_locally(desc_lower, existing_categories)
        if local_category:
            return local_category

        # Если локальная категоризация не дала результата, обращаемся к OpenAI
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
                    'currency': OpenAIService._normalize_currency_from_receipt(result.get('currency', 'EUR')),
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
    
    @staticmethod
    def _normalize_currency_from_receipt(currency: str) -> str:
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
    
    @staticmethod
    def _categorize_locally(description: str, existing_categories: List[str]) -> Optional[str]:
        """Локальная категоризация на основе ключевых слов без ChatGPT"""
        
        # Словарь ключевых слов для категоризации
        keywords_mapping = {
            'продукты': ['продукты', 'еда', 'пища', 'супермаркет', 'магазин', 'food', 'grocery', 'auchan', 'silpo', 'atb', 'novus', 'сільпо', 'ашан', 'новус', 'хлеб', 'молоко', 'мясо', 'овощи', 'фрукты', 'lidl', 'metro', 'kaufland', 'billa', 'spar', 'rewe', 'edeka', 'penny', 'netto', 'dm', 'rossmann'],
            'транспорт': ['транспорт', 'автобус', 'такси', 'uber', 'bolt', 'taxi', 'бензин', 'газ', 'заправка', 'fuel', 'petrol', 'gas', 'parking', 'парковка', 'метро', 'metro', 'поезд', 'train', 'билет', 'ticket', 'проезд', 'пересадка', 'мост', 'toll', 'платная дорога', 'автомобиль', 'car', 'машина', 'авто', 'transport', 'bus', 'tram', 'трамвай', 'троллейбус', 'trolleybus'],
            'развлечения': ['развлечения', 'кино', 'cinema', 'театр', 'theatre', 'концерт', 'concert', 'игры', 'games', 'спорт', 'sport', 'фитнес', 'fitness', 'gym', 'зал', 'бассейн', 'pool', 'парк', 'park', 'музей', 'museum', 'выставка', 'exhibition', 'клуб', 'club', 'бар', 'bar', 'pub', 'паб', 'entertainment', 'leisure', 'досуг', 'отдых', 'rest', 'vacation', 'отпуск', 'туризм', 'tourism', 'путешествие', 'travel', 'hotel', 'отель', 'hostel', 'хостел'],
            'здоровье': ['здоровье', 'аптека', 'pharmacy', 'лекарство', 'medicine', 'врач', 'doctor', 'больница', 'hospital', 'поликлиника', 'clinic', 'медицина', 'medical', 'лечение', 'treatment', 'анализы', 'tests', 'стоматолог', 'dentist', 'зубы', 'teeth', 'окулист', 'оптика', 'optics', 'glasses', 'очки', 'витамины', 'vitamins', 'добавки', 'supplements', 'массаж', 'massage', 'physio', 'физио', 'терапия', 'therapy', 'health', 'медосмотр', 'checkup'],
            'одежда': ['одежда', 'clothes', 'clothing', 'магазин одежды', 'fashion', 'мода', 'обувь', 'shoes', 'boots', 'сапоги', 'кроссовки', 'sneakers', 'платье', 'dress', 'рубашка', 'shirt', 'брюки', 'pants', 'джинсы', 'jeans', 'куртка', 'jacket', 'пальто', 'coat', 'шапка', 'hat', 'шарф', 'scarf', 'перчатки', 'gloves', 'носки', 'socks', 'белье', 'underwear', 'h&m', 'zara', 'mango', 'bershka', 'pull&bear', 'massimo dutti', 'stradivarius', 'reserved', 'c&a', 'primark', 'uniqlo', 'nike', 'adidas', 'puma', 'reebok'],
            'коммунальные услуги': ['коммунальные', 'utilities', 'электричество', 'electricity', 'газ', 'gas', 'вода', 'water', 'отопление', 'heating', 'интернет', 'internet', 'телефон', 'phone', 'мобильная связь', 'mobile', 'kyivstar', 'vodafone', 'lifecell', 'телеком', 'telecom', 'кабельное', 'cable', 'тв', 'tv', 'телевидение', 'television', 'домофон', 'intercom', 'управляющая компания', 'management', 'жкх', 'housing', 'коммуналка', 'communal', 'счетчики', 'meters', 'квартплата', 'rent', 'аренда'],
            'ресторан': ['ресторан', 'restaurant', 'кафе', 'cafe', 'coffee', 'кофе', 'starbucks', 'mcdonalds', 'kfc', 'burger', 'бургер', 'pizza', 'пицца', 'sushi', 'суши', 'delivery', 'доставка', 'glovo', 'uber eats', 'wolt', 'foodpanda', 'завтрак', 'breakfast', 'обед', 'lunch', 'ужин', 'dinner', 'столовая', 'canteen', 'фастфуд', 'fastfood', 'еда на вынос', 'takeaway', 'бар', 'bar', 'pub', 'паб', 'напитки', 'drinks', 'алкоголь', 'alcohol', 'пиво', 'beer', 'вино', 'wine', 'коктейль', 'cocktail', 'чай', 'tea', 'сок', 'juice', 'food court', 'фуд корт'],
            'прочее': ['прочее', 'other', 'разное', 'misc', 'miscellaneous', 'другое', 'прочие', 'various', 'общие', 'general']
        }
        
        # Нормализуем названия существующих категорий
        normalized_categories = {cat.lower(): cat for cat in existing_categories}
        
        # Проверяем каждую категорию
        for category_key, keywords in keywords_mapping.items():
            # Ищем соответствие среди существующих категорий пользователя
            for existing_cat_lower, existing_cat_original in normalized_categories.items():
                if category_key in existing_cat_lower or existing_cat_lower in category_key:
                    # Проверяем, есть ли ключевые слова в описании
                    for keyword in keywords:
                        if keyword in description:
                            return existing_cat_original
        
        # Если нет соответствия с существующими категориями, проверяем базовые категории
        for category_key, keywords in keywords_mapping.items():
            for keyword in keywords:
                if keyword in description:
                    # Возвращаем категорию только если она есть в списке пользователя
                    for cat in existing_categories:
                        if category_key.lower() in cat.lower() or cat.lower() in category_key.lower():
                            return cat
        
        return None
    
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
        # amount не используется в текущей реализации, но сохраняется для совместимости
        _ = amount  # Явно помечаем как неиспользуемый параметр
        
        try:
            # Используем только локальную категоризацию для совместимости
            desc_lower = description.lower().strip()
            
            # Проверяем точное совпадение
            for cat in existing_categories:
                if desc_lower == cat.lower():
                    return {
                        "category": cat,
                        "confidence": 0.9,
                        "suggest_new_category": False,
                        "suggested_category_name": None
                    }
            
            # Проверяем подстроки
            for cat in existing_categories:
                if cat.lower() in desc_lower:
                    return {
                        "category": cat,
                        "confidence": 0.8,
                        "suggest_new_category": False,
                        "suggested_category_name": None
                    }
            
            # Используем локальную категоризацию
            local_category = OpenAIService._categorize_locally(desc_lower, existing_categories)
            if local_category:
                return {
                    "category": local_category,
                    "confidence": 0.7,
                    "suggest_new_category": False,
                    "suggested_category_name": None
                }
            
            # Fallback
            return {
                "category": "Прочее",
                "confidence": 0.5,
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

    async def categorize_subcategory(self, description: str, category_name: str, existing_subcategories: List[str]) -> Optional[str]:
        """Определяет подкатегорию транзакции на основе описания и выбранной категории."""
        
        if not existing_subcategories:
            return None
        
        desc_lower = description.lower().strip()
        
        # Сначала проверяем точное совпадение с существующей подкатегорией
        for subcat in existing_subcategories:
            if desc_lower == subcat.lower():
                return subcat
        
        # Затем ищем подкатегорию как подстроку в описании
        for subcat in existing_subcategories:
            if subcat.lower() in desc_lower:
                return subcat
        
        # Локальная категоризация подкатегорий
        local_subcategory = self._categorize_subcategory_locally(desc_lower, category_name, existing_subcategories)
        if local_subcategory:
            return local_subcategory
        
        # Если локальная категоризация не дала результата, обращаемся к OpenAI
        prompt = f"""
        Определи наиболее подходящую подкатегорию для транзакции: "{description}"
        
        Категория: {category_name}
        Доступные подкатегории: {', '.join(existing_subcategories)}
        
        Верни только название подкатегории из списка доступных подкатегорий.
        Если ни одна не подходит, верни пустую строку.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты помощник для категоризации транзакций. Отвечай только названием подкатегории или пустой строкой."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            suggested_subcategory = response.choices[0].message.content.strip()
            
            # Проверяем, что предложенная подкатегория существует
            if suggested_subcategory in existing_subcategories:
                return suggested_subcategory
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при определении подкатегории через OpenAI: {e}")
            return None

    def _categorize_subcategory_locally(self, description: str, category_name: str, existing_subcategories: List[str]) -> Optional[str]:
        """Локальная категоризация подкатегорий на основе ключевых слов"""
        
        # Словарь ключевых слов для подкатегорий по категориям
        subcategory_keywords = {
            "продукты": {
                "мясо": ["мясо", "колбаса", "курица", "говядина", "свинина", "рыба"],
                "молочные": ["молоко", "сыр", "творог", "йогурт", "сметана", "кефир"],
                "овощи": ["овощи", "картошка", "морковь", "лук", "помидоры", "огурцы"],
                "фрукты": ["фрукты", "яблоки", "бананы", "апельсины", "груши"],
                "хлеб": ["хлеб", "булка", "батон", "выпечка", "хлебобулочные"],
                "сладости": ["конфеты", "шоколад", "торт", "печенье", "мороженое"]
            },
            "транспорт": {
                "топливо": ["бензин", "дизель", "газ", "заправка", "азс"],
                "общественный": ["автобус", "метро", "трамвай", "троллейбус", "билет"],
                "такси": ["такси", "uber", "яндекс", "bolt", "поездка"],
                "парковка": ["парковка", "паркинг", "стоянка"],
                "ремонт": ["ремонт", "сервис", "шины", "масло", "запчасти"]
            },
            "развлечения": {
                "кино": ["кино", "театр", "концерт", "билет", "спектакль"],
                "спорт": ["спорт", "фитнес", "зал", "тренажерный", "бассейн"],
                "игры": ["игра", "игры", "консоль", "steam", "playstation"],
                "книги": ["книга", "книги", "литература", "роман"],
                "музыка": ["музыка", "spotify", "apple music", "концерт"]
            },
            "здоровье": {
                "лекарства": ["лекарство", "таблетки", "аптека", "медикаменты"],
                "врач": ["врач", "доктор", "прием", "консультация"],
                "стоматология": ["стоматолог", "зубы", "зубной", "стоматология"],
                "анализы": ["анализы", "обследование", "узи", "рентген"]
            },
            "ресторан": {
                "фастфуд": ["макдональдс", "kfc", "бургер", "пицца", "фастфуд"],
                "кафе": ["кафе", "кофе", "чай", "starbucks", "coffee"],
                "ресторан": ["ресторан", "ужин", "обед", "банкет"],
                "доставка": ["доставка", "delivery", "яндекс еда", "uber eats"]
            }
        }
        
        category_lower = category_name.lower()
        
        # Ищем подходящую категорию в словаре
        for cat_key, subcats in subcategory_keywords.items():
            if cat_key in category_lower:
                for subcat_name, keywords in subcats.items():
                    # Проверяем, есть ли такая подкатегория в существующих
                    matching_subcategory = None
                    for existing_subcat in existing_subcategories:
                        if subcat_name.lower() in existing_subcat.lower() or existing_subcat.lower() in subcat_name.lower():
                            matching_subcategory = existing_subcat
                            break
                    
                    if matching_subcategory:
                        # Проверяем ключевые слова
                        for keyword in keywords:
                            if keyword in description:
                                return matching_subcategory
                
                break
        
        return None