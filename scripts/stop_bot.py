#!/usr/bin/env python3
"""
Скрипт для остановки Budget Bot
"""

import os
import sys
import signal
import psutil
import time

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

def stop_bots():
    """Остановить все процессы бота"""
    running_bots = find_running_bot_processes()
    
    if not running_bots:
        print("ℹ️  Запущенных процессов бота не найдено")
        return True
    
    print(f"🔍 Найдено {len(running_bots)} запущенных процессов бота")
    
    for bot_process in running_bots:
        try:
            pid = bot_process['pid']
            print(f"🛑 Завершение процесса {pid}...")
            
            # Пытаемся завершить процесс мягко
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            
            # Проверяем, завершился ли процесс
            if psutil.pid_exists(pid):
                print(f"⚠️  Принудительное завершение процесса {pid}")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
                
            if not psutil.pid_exists(pid):
                print(f"✅ Процесс {pid} успешно завершен")
            else:
                print(f"❌ Не удалось завершить процесс {pid}")
                
        except (ProcessLookupError, psutil.NoSuchProcess):
            print(f"✅ Процесс {pid} уже завершен")
        except Exception as e:
            print(f"❌ Ошибка при завершении процесса {pid}: {e}")
    
    # Проверяем, остались ли процессы
    remaining_bots = find_running_bot_processes()
    
    if remaining_bots:
        print(f"⚠️  Остались активные процессы: {len(remaining_bots)}")
        return False
    else:
        print("✅ Все процессы бота успешно завершены")
        return True

def main():
    """Основная функция"""
    print("🛑 Budget Bot - Остановка")
    print("=" * 30)
    
    success = stop_bots()
    
    if success:
        print("\n🎉 Бот успешно остановлен")
        sys.exit(0)
    else:
        print("\n⚠️  Некоторые процессы могут остаться активными")
        print("💡 Попробуйте перезапустить терминал или перезагрузить систему")
        sys.exit(1)

if __name__ == "__main__":
    main()