#!/usr/bin/env python3
"""
Простое решение конфликта Telegram Bot
"""

import os
import subprocess
import time

def main():
    """Решение конфликта бота"""
    print("🔧 Решение конфликта Budget Bot")
    print("=" * 40)
    
    print("1. 🛑 Завершение всех процессов Python...")
    try:
        # Завершаем все процессы Python (осторожно!)
        result = subprocess.run(
            "ps aux | grep python | grep -v grep | awk '{print $2}' | head -20", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"   Найдено {len(pids)} процессов Python")
            
            for pid in pids:
                try:
                    subprocess.run(f"kill -TERM {pid}", shell=True, check=False)
                    print(f"   Завершен процесс {pid}")
                except:
                    pass
        else:
            print("   Активных процессов не найдено")
            
    except Exception as e:
        print(f"   Ошибка при завершении процессов: {e}")
    
    print("\n2. ⏳ Ожидание завершения процессов...")
    time.sleep(5)
    
    print("\n3. 🔍 Проверка переменных окружения...")
    
    # Проверяем .env файл
    if os.path.exists('.env'):
        print("   ✅ Файл .env найден")
        
        with open('.env', 'r') as f:
            content = f.read()
            
        if 'TELEGRAM_BOT_TOKEN' in content:
            print("   ✅ TELEGRAM_BOT_TOKEN настроен")
        else:
            print("   ❌ TELEGRAM_BOT_TOKEN не найден в .env")
            
        if 'OPENAI_API_KEY' in content:
            print("   ✅ OPENAI_API_KEY настроен")
        else:
            print("   ❌ OPENAI_API_KEY не найден в .env")
    else:
        print("   ❌ Файл .env не найден")
        print("   💡 Создайте файл .env с токенами:")
        print("      TELEGRAM_BOT_TOKEN=your_token_here")
        print("      OPENAI_API_KEY=your_key_here")
    
    print("\n4. 📋 Инструкции по запуску:")
    print("   1. Убедитесь, что файл .env существует и содержит токены")
    print("   2. Подождите 30 секунд перед запуском")
    print("   3. Запустите бота: python bot.py")
    print("   4. Если проблема повторится, перезапустите терминал")
    
    print("\n✅ Готово! Теперь можно запускать бота.")

if __name__ == "__main__":
    main()