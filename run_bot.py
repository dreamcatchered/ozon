#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт запуска Ozon Seller API Telegram Bot на telebot
"""

import sys
import os
from ozon_bot import main

if __name__ == "__main__":
    try:
        print("🚀 Запуск Ozon Seller API Telegram Bot (telebot)...")
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        sys.exit(1)
