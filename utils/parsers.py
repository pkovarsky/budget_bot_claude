import re
from typing import Optional, Tuple


def parse_transaction(text: str) -> Optional[Tuple[float, str, str, bool]]:
    """Парсинг текста для извлечения данных транзакции"""
    text = text.strip()
    is_income = text.startswith('+')
    if is_income:
        text = text[1:].strip()
    
    # Паттерны для парсинга с валютой
    patterns_with_currency = [
        r'(\d+(?:\.\d+)?)\s*(евро|euro|eur|€)\s+(.+)',
        r'(\d+(?:\.\d+)?)\s*(доллар|долларов|usd|\$)\s+(.+)',
        r'(\d+(?:\.\d+)?)\s+(.+?)\s*(евро|euro|eur|€)',
        r'(\d+(?:\.\d+)?)\s+(.+?)\s*(доллар|долларов|usd|\$)',
    ]
    
    # Сначала пытаемся найти валюту
    for pattern in patterns_with_currency:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if pattern.startswith(r'(\d+'):  # Паттерны с валютой в начале
                    amount, currency, description = groups
                else:  # Паттерны с валютой в конце
                    amount, description, currency = groups
                
                amount = float(amount)
                currency = normalize_currency(currency)
                description = description.strip()
                
                return amount, currency, description, is_income
    
    # Если валюта не найдена, ищем только сумму и описание
    pattern_without_currency = r'(\d+(?:\.\d+)?)\s+(.+)'
    match = re.search(pattern_without_currency, text, re.IGNORECASE)
    if match:
        amount_str, description = match.groups()
        try:
            amount = float(amount_str)
            description = description.strip()
            # Используем EUR по умолчанию
            return amount, 'EUR', description, is_income
        except ValueError:
            pass
    
    return None


def normalize_currency(currency: str) -> str:
    """Нормализация валюты"""
    currency = currency.lower()
    if currency in ['евро', 'euro', 'eur', '€']:
        return 'EUR'
    elif currency in ['доллар', 'долларов', 'usd', '$']:
        return 'USD'
    return currency.upper()


def parse_amount_and_currency(text: str) -> Optional[Tuple[float, str]]:
    """Парсинг суммы и валюты для лимитов"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(евро|euro|eur|€)',
        r'(\d+(?:\.\d+)?)\s*(доллар|долларов|usd|\$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str, currency_str = match.groups()
            amount = float(amount_str)
            currency = normalize_currency(currency_str)
            return amount, currency
    
    return None