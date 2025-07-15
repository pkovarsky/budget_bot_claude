#!/usr/bin/env python3
"""
Безопасный запуск Budget Bot с проверкой на дублирование
"""

import os
import sys
import time
import signal
import psutil
from pathlib import Path

def find_running_bot_processes():
    """Найти запущенные процессы бота"""
    running_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Проверяем, есть ли bot.py в командной строке
            if proc.info['cmdline'] and any('bot.py' in arg for arg in proc.info['cmdline']):
                running_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return running_processes

def kill_existing_bots():
    """Завершить существующие процессы бота"""
    running_bots = find_running_bot_processes()
    
    if running_bots:
        print(f"🔍 Найдено {len(running_bots)} запущенных процессов бота")
        
        for bot_process in running_bots:
            try:
                pid = bot_process['pid']
                print(f"🛑 Завершение процесса {pid}")
                
                # Пытаемся завершить процесс мягко
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                
                # Проверяем, завершился ли процесс
                if psutil.pid_exists(pid):
                    print(f"⚠️  Принудительное завершение процесса {pid}")
                    os.kill(pid, signal.SIGKILL)
                    
            except (ProcessLookupError, psutil.NoSuchProcess):
                # Процесс уже завершен
                pass
            except Exception as e:
                print(f"❌ Ошибка при завершении процесса {pid}: {e}")
        
        print("✅ Все предыдущие процессы завершены")
        time.sleep(1)
    else:
        print("✅ Других экземпляров бота не найдено")

def check_environment():
    """Проверить окружение перед запуском"""
    print("🔍 Проверка окружения...")
    
    # Проверяем наличие файлов
    required_files = ['bot.py', 'config.py', 'database.py', 'openai_service.py']
    
    for file_name in required_files:
        if not os.path.exists(file_name):
            print(f"❌ Отсутствует файл: {file_name}")
            return False
        else:
            print(f"✅ Найден файл: {file_name}")
    
    # Проверяем переменные окружения
    required_env = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    
    for env_var in required_env:
        if not os.getenv(env_var):
            print(f"❌ Отсутствует переменная окружения: {env_var}")
            print("💡 Создайте файл .env с необходимыми переменными")
            return False
        else:
            print(f"✅ Найдена переменная: {env_var}")
    
    return True

def start_bot():
    """Запустить бота"""
    print("🚀 Запуск Budget Bot...")
    
    try:
        # Импортируем и запускаем бота
        from bot import main
        main()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Основная функция"""
    print("🤖 Budget Bot - Безопасный запуск")
    print("=" * 50)
    
    # Проверяем окружение
    if not check_environment():
        print("\n❌ Проверка окружения не пройдена")
        sys.exit(1)
    
    # Завершаем существующие процессы
    kill_existing_bots()
    
    # Запускаем бота
    start_bot()

if __name__ == "__main__":
    main()