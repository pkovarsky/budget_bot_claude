#!/usr/bin/env python3
"""
Проверка статуса Budget Bot
"""

import os
import psutil
from datetime import datetime

def find_running_bot_processes():
    """Найти запущенные процессы бота"""
    running_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
        try:
            # Проверяем, есть ли bot.py в командной строке
            if proc.info['cmdline'] and any('bot.py' in arg for arg in proc.info['cmdline']):
                running_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return running_processes

def check_environment():
    """Проверить переменные окружения"""
    env_vars = {
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'DATABASE_URL': os.getenv('DATABASE_URL', 'sqlite:///budget_bot.db')
    }
    
    return env_vars

def check_files():
    """Проверить необходимые файлы"""
    required_files = [
        'bot.py',
        'config.py', 
        'database.py',
        'openai_service.py',
        'chart_service.py'
    ]
    
    file_status = {}
    for file_name in required_files:
        file_status[file_name] = os.path.exists(file_name)
    
    return file_status

def main():
    """Основная функция проверки"""
    print("🔍 Budget Bot - Проверка статуса")
    print("=" * 40)
    
    # Проверка запущенных процессов
    running_bots = find_running_bot_processes()
    
    if running_bots:
        print(f"🟢 Статус: ЗАПУЩЕН ({len(running_bots)} процессов)")
        
        for i, bot_process in enumerate(running_bots, 1):
            pid = bot_process['pid']
            create_time = datetime.fromtimestamp(bot_process['create_time'])
            memory_mb = bot_process['memory_info'].rss / 1024 / 1024
            
            print(f"  📊 Процесс {i}:")
            print(f"    PID: {pid}")
            print(f"    Запущен: {create_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Память: {memory_mb:.1f} MB")
    else:
        print("🔴 Статус: НЕ ЗАПУЩЕН")
    
    # Проверка окружения
    print("\n🔧 Переменные окружения:")
    env_vars = check_environment()
    
    for var_name, var_value in env_vars.items():
        if var_value:
            masked_value = var_value[:10] + "..." if len(var_value) > 10 else var_value
            print(f"  ✅ {var_name}: {masked_value}")
        else:
            print(f"  ❌ {var_name}: НЕ УСТАНОВЛЕНА")
    
    # Проверка файлов
    print("\n📁 Необходимые файлы:")
    file_status = check_files()
    
    for file_name, exists in file_status.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {file_name}")
    
    # Проверка базы данных
    print("\n💾 База данных:")
    db_file = "budget_bot.db"
    if os.path.exists(db_file):
        db_size = os.path.getsize(db_file) / 1024  # KB
        print(f"  ✅ {db_file}: {db_size:.1f} KB")
    else:
        print(f"  ⚠️  {db_file}: Будет создана при первом запуске")
    
    # Итоговая оценка
    print("\n📊 Итоговая оценка:")
    
    issues = []
    
    if not running_bots:
        issues.append("Бот не запущен")
    
    if not env_vars['TELEGRAM_BOT_TOKEN']:
        issues.append("Отсутствует TELEGRAM_BOT_TOKEN")
    
    if not env_vars['OPENAI_API_KEY']:
        issues.append("Отсутствует OPENAI_API_KEY")
    
    missing_files = [f for f, exists in file_status.items() if not exists]
    if missing_files:
        issues.append(f"Отсутствуют файлы: {', '.join(missing_files)}")
    
    if issues:
        print("❌ Проблемы:")
        for issue in issues:
            print(f"  • {issue}")
        
        print("\n💡 Рекомендации:")
        if not running_bots:
            print("  • Запустите бота: python start_bot.py")
        if not env_vars['TELEGRAM_BOT_TOKEN'] or not env_vars['OPENAI_API_KEY']:
            print("  • Создайте файл .env с необходимыми переменными")
        if missing_files:
            print("  • Восстановите отсутствующие файлы")
    else:
        print("✅ Все в порядке! Бот готов к работе.")

if __name__ == "__main__":
    main()