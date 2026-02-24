#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конфигурационный файл для Ozon Seller API Telegram Bot
"""

import os
from typing import Optional

class Config:
    """Класс конфигурации бота"""
    
    # Telegram Bot настройки
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    ADMIN_CHAT_ID: str = os.getenv("ADMIN_CHAT_ID", "")
    
    # Ozon Seller API настройки
    OZON_API_KEY: str = os.environ.get("OZON_API_KEY", "YOUR_OZON_API_KEY_HERE")
    OZON_CLIENT_ID: str = os.environ.get("OZON_CLIENT_ID", "YOUR_OZON_CLIENT_ID_HERE")
    OZON_BASE_URL: str = "https://api-seller.ozon.ru"
    
    # Настройки мониторинга
    MONITORING_INTERVAL: int = 300  # Интервал проверки в секундах (5 минут)
    MAX_ORDERS_PER_REQUEST: int = 100  # Максимальное количество заказов за запрос
    
    # Настройки логирования
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Настройки уведомлений
    ENABLE_NOTIFICATIONS: bool = True
    NOTIFICATION_BATCH_SIZE: int = 5  # Количество заказов в одном уведомлении
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка корректности конфигурации"""
        if cls.BOT_TOKEN == "YOUR_BOT_TOKEN":
            print("❌ Ошибка: BOT_TOKEN не настроен")
            return False
        
        if cls.ADMIN_CHAT_ID == "YOUR_ADMIN_CHAT_ID":
            print("⚠️ Предупреждение: ADMIN_CHAT_ID не настроен, уведомления недоступны")
        else:
            print("✅ ADMIN_CHAT_ID настроен, уведомления доступны")
        
        if cls.OZON_API_KEY == "YOUR_OZON_API_KEY":
            print("❌ Ошибка: OZON_API_KEY не настроен")
            return False
        
        if cls.OZON_CLIENT_ID == "YOUR_OZON_CLIENT_ID":
            print("❌ Ошибка: OZON_CLIENT_ID не настроен")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Вывод текущей конфигурации"""
        print("🔧 Конфигурация бота:")
        print(f"  Bot Token: {cls.BOT_TOKEN[:10]}...")
        print(f"  Admin Chat ID: {cls.ADMIN_CHAT_ID}")
        print(f"  Ozon API Key: {cls.OZON_API_KEY[:10]}...")
        print(f"  Ozon Client ID: {cls.OZON_CLIENT_ID}")
        print(f"  Monitoring Interval: {cls.MONITORING_INTERVAL}s")
        print(f"  Max Orders Per Request: {cls.MAX_ORDERS_PER_REQUEST}")
        print(f"  Notifications Enabled: {cls.ENABLE_NOTIFICATIONS}")

# Статусы заказов FBS
FBS_STATUSES = {
    "awaiting_registration": "Ожидает регистрации",
    "acceptance_in_progress": "Идёт приёмка", 
    "awaiting_approve": "Ожидает подтверждения",
    "awaiting_packaging": "Ожидает упаковки",
    "awaiting_deliver": "Ожидает отгрузки",
    "arbitration": "Арбитраж",
    "client_arbitration": "Клиентский арбитраж доставки",
    "delivering": "Доставляется",
    "driver_pickup": "У водителя",
    "cancelled": "Отменено",
    "not_accepted": "Не принят на СЦ"
}

# Эмодзи для интерфейса
EMOJIS = {
    "bot": "🤖",
    "orders": "📦",
    "all_orders": "📋",
    "labels": "🏷️",
    "notifications": "🔔",
    "settings": "⚙️",
    "back": "🔙",
    "loading": "⏳",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "monitor": "📊",
    "summary": "📈",
    "start": "▶️",
    "stop": "⏹️"
}
