#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ozon Seller API Telegram Bot на pyTelegramBotAPI (telebot)
Улучшенный бот для управления заказами FBS с детальной информацией и фото товаров
"""

import logging
import threading
import time
import json
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import telebot
from telebot import types
import fitz  # PyMuPDF
from config import Config, FBS_STATUSES, EMOJIS

# Настройка логирования
logging.basicConfig(
    format=Config.LOG_FORMAT,
    level=getattr(logging, Config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class OzonAPI:
    """Класс для работы с Ozon Seller API"""
    
    def __init__(self, api_key: str, client_id: str):
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = Config.OZON_BASE_URL
        self.headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_orders_for_packaging(self, limit: int = 100) -> Dict[str, Any]:
        """
        Получить заказы готовые к сборке (awaiting_packaging)
        POST /v3/posting/fbs/list
        """
        url = f"{self.base_url}/v3/posting/fbs/list"
        
        # Фильтр по времени (последние 30 дней)
        cutoff_to = datetime.now()
        cutoff_from = cutoff_to - timedelta(days=30)
        
        payload = {
            "dir": "ASC",
            "filter": {
                "since": cutoff_from.isoformat() + "Z",
                "to": cutoff_to.isoformat() + "Z",
                "status": "awaiting_packaging"
            },
            "limit": limit,
            "offset": 0,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "translit": True
            }
        }
        
        try:
            logger.debug(f"Отправка запроса на {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении заказов на сборку: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def get_orders_awaiting_deliver(self, limit: int = 100) -> Dict[str, Any]:
        """
        Получить заказы готовые к отгрузке (awaiting_deliver)
        POST /v3/posting/fbs/list
        """
        url = f"{self.base_url}/v3/posting/fbs/list"
        
        cutoff_to = datetime.now()
        cutoff_from = cutoff_to - timedelta(days=30)
        
        payload = {
            "dir": "ASC",
            "filter": {
                "since": cutoff_from.isoformat() + "Z",
                "to": cutoff_to.isoformat() + "Z",
                "status": "awaiting_deliver"
            },
            "limit": limit,
            "offset": 0,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "translit": True
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении заказов к отгрузке: {e}")
            return {"error": str(e)}
    
    def get_order_details(self, posting_number: str) -> Dict[str, Any]:
        """
        Получить детальную информацию о заказе
        POST /v3/posting/fbs/get
        """
        url = f"{self.base_url}/v3/posting/fbs/get"
        payload = {
            "posting_number": posting_number,
            "with": {
                "analytics_data": True,
                "barcodes": True,
                "financial_data": True,
                "translit": True
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении деталей заказа: {e}")
            return {"error": str(e)}
    
    def get_product_images(self, product_ids: List[str]) -> Dict[str, Any]:
        """
        Получить изображения товаров
        POST /v2/product/pictures/info
        """
        url = f"{self.base_url}/v2/product/pictures/info"
        payload = {
            "product_id": product_ids
        }
        
        try:
            logger.debug(f"Отправка запроса на получение изображений: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API изображений: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Результат изображений: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении изображений товаров: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def ship_order(self, posting_number: str, packages: List[Dict]) -> Dict[str, Any]:
        """
        Собрать заказ
        POST /v4/posting/fbs/ship
        """
        url = f"{self.base_url}/v4/posting/fbs/ship"
        payload = {
            "posting_number": posting_number,
            "packages": packages,
            "with": {
                "additional_data": True
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при сборке заказа: {e}")
            return {"error": str(e)}
    
    def get_package_label(self, posting_numbers: List[str]) -> Dict[str, Any]:
        """
        Получить этикетки для печати
        POST /v2/posting/fbs/package-label
        """
        url = f"{self.base_url}/v2/posting/fbs/package-label"
        payload = {
            "posting_number": posting_numbers
        }
        
        try:
            logger.debug(f"Отправка запроса на получение этикеток: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API для этикеток: {response.status_code}")
            
            if response.status_code == 200:
                # Проверяем content-type
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' in content_type:
                    # Это PDF файл
                    return {
                        "file_content": response.content,
                        "file_name": f"label_{'-'.join(posting_numbers)}.pdf",
                        "content_type": "application/pdf"
                    }
                elif 'application/json' in content_type:
                    # Это JSON ответ
                    return response.json()
                else:
                    logger.error(f"Неожиданный content-type: {content_type}")
                    return {"error": f"Неожиданный content-type: {content_type}"}
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении этикеток: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def get_barcode(self, posting_number: str) -> Dict[str, Any]:
        """
        Получить штрихкод для заказа
        POST /v2/posting/fbs/barcode
        """
        url = f"{self.base_url}/v2/posting/fbs/barcode"
        payload = {
            "posting_number": posting_number
        }
        
        try:
            logger.debug(f"Отправка запроса на получение штрихкода: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API для штрихкода: {response.status_code}")
            
            if response.status_code == 200:
                # Проверяем content-type
                content_type = response.headers.get('content-type', '')
                if 'image/' in content_type:
                    # Это изображение штрихкода
                    return {
                        "file_content": response.content,
                        "file_name": f"barcode_{posting_number}.png",
                        "content_type": content_type
                    }
                elif 'application/json' in content_type:
                    # Это JSON ответ
                    return response.json()
                else:
                    logger.error(f"Неожиданный content-type: {content_type}")
                    return {"error": f"Неожиданный content-type: {content_type}"}
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении штрихкода: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def get_all_products(self, limit: int = 100) -> Dict[str, Any]:
        """
        Получить все товары на продаже через API списка товаров
        POST /v3/product/list
        """
        url = f"{self.base_url}/v3/product/list"
        payload = {
            "filter": {
                "visibility": "ALL"  # Все товары, кроме архивных
            },
            "limit": limit,
            "last_id": ""
        }

        try:
            logger.debug(f"Отправка запроса на получение всех товаров: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API товаров: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Результат товаров: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении товаров: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def get_product_barcode(self, item_id: str) -> Dict[str, Any]:
        """
        Получить штрихкод товара
        POST /v2/product/barcode
        """
        url = f"{self.base_url}/v2/product/barcode"
        payload = {
            "item_id": [item_id]
        }
        
        try:
            logger.debug(f"Отправка запроса на получение штрихкода товара: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API штрихкода товара: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Результат штрихкода товара: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении штрихкода товара: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def update_product_stocks(self, offer_id: str, warehouse_id: int, stock: int) -> Dict[str, Any]:
        """
        Обновить количество товара на складе FBS
        POST /v2/products/stocks
        """
        url = f"{self.base_url}/v2/products/stocks"
        payload = {
            "stocks": [
                {
                    "offer_id": offer_id,
                    "warehouse_id": warehouse_id,
                    "stock": stock
                }
            ]
        }
        
        try:
            logger.debug(f"Отправка запроса на обновление остатков: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API обновления остатков: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Результат обновления остатков: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при обновлении остатков: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}
    
    def get_fbs_stocks(self, sku_list: List[str]) -> Dict[str, Any]:
        """
        Получить информацию об остатках FBS товаров
        POST /v1/product/info/stocks-by-warehouse/fbs
        """
        url = f"{self.base_url}/v1/product/info/stocks-by-warehouse/fbs"
        payload = {
            "sku": sku_list
        }
        
        try:
            logger.debug(f"Отправка запроса на получение остатков FBS: {url} с payload: {payload}")
            response = requests.post(url, headers=self.headers, json=payload)
            logger.debug(f"Ответ API остатков FBS: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"Результат остатков FBS: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении остатков FBS: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Payload: {payload}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
            return {"error": str(e)}

class OrderMonitor:
    """Класс для мониторинга новых заказов"""
    
    def __init__(self, ozon_api, bot, admin_chat_id: str):
        self.ozon_api = ozon_api
        self.bot = bot
        self.admin_chat_id = admin_chat_id
        self.processed_orders: set = set()
        self.is_running = False
        self.monitor_thread = None
        
    def start_monitoring(self, check_interval: int = None):
        """Запуск мониторинга новых заказов"""
        if check_interval is None:
            check_interval = Config.MONITORING_INTERVAL
            
        if self.is_running:
            return
            
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(check_interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info(f"Запуск мониторинга заказов с интервалом {check_interval} секунд")
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("Мониторинг заказов остановлен")
    
    def _monitor_loop(self, check_interval: int):
        """Основной цикл мониторинга"""
        while self.is_running:
            try:
                self.check_new_orders()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Ошибка в мониторинге заказов: {e}")
                time.sleep(60)
    
    def check_new_orders(self):
        """Проверка новых заказов на сборку"""
        try:
            result = self.ozon_api.get_orders_for_packaging(limit=Config.MAX_ORDERS_PER_REQUEST)
            
            if "error" in result:
                logger.error(f"Ошибка при получении заказов: {result['error']}")
                return
            
            orders = result.get("result", {}).get("postings", [])
            if not orders:
                logger.info("Нет новых заказов на сборку")
                return
                
            new_orders = []
            
            for order in orders:
                posting_number = order.get("posting_number")
                if posting_number and posting_number not in self.processed_orders:
                    new_orders.append(order)
                    self.processed_orders.add(posting_number)
            
            if new_orders:
                self.send_new_orders_notification(new_orders)
            else:
                logger.info("Все заказы уже обработаны")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке новых заказов: {e}")
    
    def send_new_orders_notification(self, orders: List[Dict[str, Any]]):
        """Отправка уведомления о новых заказах на сборку"""
        try:
            text = f"🔔 <b>Новые заказы на сборку ({len(orders)})</b>\n\n"
            
            for order in orders[:Config.NOTIFICATION_BATCH_SIZE]:
                posting_number = order.get("posting_number", "N/A")
                shipment_date = order.get("shipment_date", "N/A")
                
                text += f"📦 <b>{posting_number}</b>\n"
                text += f"Дата отгрузки: {shipment_date}\n\n"
            
            if len(orders) > Config.NOTIFICATION_BATCH_SIZE:
                text += f"... и еще {len(orders) - Config.NOTIFICATION_BATCH_SIZE} заказов\n\n"
            
            text += "Используйте /orders для просмотра всех заказов"
            
            self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=text,
                parse_mode="HTML"
            )
            
            logger.info(f"Отправлено уведомление о {len(orders)} новых заказах")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
    
    def get_processed_orders_count(self) -> int:
        """Получить количество обработанных заказов"""
        return len(self.processed_orders)

class OzonBot:
    """Основной класс Telegram бота на telebot"""
    
    def __init__(self):
        self.ozon_api = OzonAPI(Config.OZON_API_KEY, Config.OZON_CLIENT_ID)
        self.bot = telebot.TeleBot(Config.BOT_TOKEN)
        self.order_monitor = OrderMonitor(self.ozon_api, self.bot, Config.ADMIN_CHAT_ID)
        self.setup_handlers()
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        # Список администраторов
        admin_ids = [
            str(Config.ADMIN_CHAT_ID),  # Основной администратор
            "669994046"  # Дополнительный администратор
        ]
        return str(user_id) in admin_ids
    
    def check_admin_access(self, user_id: int) -> bool:
        """Проверить права доступа администратора"""
        if not self.is_admin(user_id):
            return False
        return True
    
    def send_access_denied(self, chat_id: int):
        """Отправить сообщение об отказе в доступе"""
        self.bot.send_message(
            chat_id,
            "🚫 <b>Доступ запрещен</b>\n\n"
            "У вас нет прав для использования этого бота.\n"
            "Обратитесь к администратору для получения доступа.",
            parse_mode="HTML"
        )
    
    def show_main_menu(self, chat_id: int, user_id: int):
        """Показать главное меню (универсальная функция)"""
        # Проверяем права доступа
        if not self.check_admin_access(user_id):
            self.send_access_denied(chat_id)
            return
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(
            types.InlineKeyboardButton("📦 Заказы на сборку", callback_data="packaging_orders"),
            types.InlineKeyboardButton("🚚 Готовые к отгрузке", callback_data="delivery_orders")
        )
        keyboard.row(
            types.InlineKeyboardButton("🔔 Уведомления", callback_data="notifications")
        )
        keyboard.row(
            types.InlineKeyboardButton("📦 Товары", callback_data="all_products")
        )
        keyboard.row(
            types.InlineKeyboardButton("📊 Статистика", callback_data="stats")
        )
        
        welcome_text = (
            "🤖 <b>Ozon Seller Bot</b>\n\n"
            "Добро пожаловать! Этот бот поможет вам управлять заказами FBS:\n\n"
            "📦 <b>Заказы на сборку</b> - заказы в статусе awaiting_packaging\n"
            "🚚 <b>Готовые к отгрузке</b> - заказы в статусе awaiting_deliver\n"
            "🔔 <b>Уведомления</b> - управление уведомлениями\n"
            "📊 <b>Статистика</b> - общая статистика по заказам\n\n"
            "Выберите нужное действие:"
        )
        
        self.bot.send_message(
            chat_id,
            welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            """Обработчик команды /start"""
            self.show_main_menu(message.chat.id, message.from_user.id)
        
        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            """Обработчик команды /help"""
            # Проверяем права доступа
            if not self.check_admin_access(message.from_user.id):
                self.send_access_denied(message.chat.id)
                return
            
            help_text = (
                "📖 <b>Справка по командам:</b>\n\n"
                "/start - Главное меню бота\n"
                "/help - Эта справка\n"
                "/orders - Быстрый доступ к заказам\n"
                "/labels - Быстрый доступ к этикеткам\n"
                "/monitor - Статус мониторинга\n\n"
                "<b>Основные функции:</b>\n"
                "• Просмотр заказов на сборку с фото товаров\n"
                "• Сборка заказов одним нажатием\n"
                "• Получение этикеток для печати\n"
                "• Уведомления о новых заказах\n"
                "• Детальная информация о каждом заказе\n\n"
                "<b>Безопасность:</b>\n"
                "• Доступ только для администратора\n"
                "• Все действия логируются\n"
                "• Защита от несанкционированного доступа"
            )
            
            self.bot.send_message(message.chat.id, help_text, parse_mode="HTML")
        
        @self.bot.message_handler(commands=['orders'])
        def orders_command(message):
            """Обработчик команды /orders"""
            # Проверяем права доступа
            if not self.check_admin_access(message.from_user.id):
                self.send_access_denied(message.chat.id)
                return
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton("📦 На сборку", callback_data="packaging_orders"),
                types.InlineKeyboardButton("🚚 К отгрузке", callback_data="delivery_orders")
            )
            keyboard.row(
                types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu")
            )
            
            self.bot.send_message(
                message.chat.id,
                "📋 <b>Управление заказами</b>\n\nВыберите тип заказов:",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        @self.bot.message_handler(commands=['labels'])
        def labels_command(message):
            """Обработчик команды /labels"""
            # Проверяем права доступа
            if not self.check_admin_access(message.from_user.id):
                self.send_access_denied(message.chat.id)
                return
            
            self.show_labels_menu(message.chat.id)
        
        @self.bot.message_handler(commands=['monitor'])
        def monitor_command(message):
            """Обработчик команды /monitor"""
            # Проверяем права доступа
            if not self.check_admin_access(message.from_user.id):
                self.send_access_denied(message.chat.id)
                return
            
            if self.order_monitor.is_running:
                text = (
                    f"✅ Мониторинг активен\n"
                    f"Обработано заказов: {self.order_monitor.get_processed_orders_count()}"
                )
            else:
                text = "❌ Мониторинг не запущен"
            
            self.bot.send_message(message.chat.id, text)
        
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            """Обработчик нажатий на inline кнопки"""
            # Проверяем права доступа
            if not self.check_admin_access(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 Доступ запрещен", show_alert=True)
                self.send_access_denied(call.message.chat.id)
                return
            
            self.bot.answer_callback_query(call.id)
            
            data = call.data
            
            if data == "main_menu":
                self.show_main_menu(call.message.chat.id, call.from_user.id)
            elif data == "packaging_orders":
                self.show_packaging_orders(call.message.chat.id)
            elif data == "delivery_orders":
                self.show_delivery_orders(call.message.chat.id)
            elif data == "labels":
                self.show_labels_menu(call.message.chat.id)
            elif data == "notifications":
                self.show_notifications_menu(call.message.chat.id)
            elif data == "stats":
                self.show_stats(call.message.chat.id)
            elif data == "all_products":
                self.show_all_products_menu(call.message.chat.id, 0)
            elif data.startswith("products_page_"):
                # Обработка пагинации товаров
                page = int(data.replace("products_page_", ""))
                self.show_all_products_menu(call.message.chat.id, page)
            elif data == "products_packaging":
                self.show_products_by_status(call.message.chat.id, "awaiting_packaging")
            elif data == "products_delivery":
                self.show_products_by_status(call.message.chat.id, "awaiting_deliver")
            elif data.startswith("order_"):
                posting_number = data.replace("order_", "")
                self.show_order_details(call.message.chat.id, posting_number)
            elif data.startswith("ship_"):
                posting_number = data.replace("ship_", "")
                self.ship_order(call.message.chat.id, posting_number, call.message.message_id)
            elif data.startswith("label_"):
                posting_number = data.replace("label_", "")
                self.show_order_details(call.message.chat.id, posting_number)
            elif data.startswith("download_label_"):
                posting_number = data.replace("download_label_", "")
                self.get_single_label(call.message.chat.id, posting_number)
            elif data.startswith("download_barcode_"):
                posting_number = data.replace("download_barcode_", "")
                self.get_single_barcode(call.message.chat.id, posting_number)
            elif data.startswith("products_"):
                posting_number = data.replace("products_", "")
                self.show_order_products(call.message.chat.id, posting_number)
            elif data.startswith("barcodes_"):
                posting_number = data.replace("barcodes_", "")
                self.get_order_barcodes(call.message.chat.id, posting_number)
            elif data.startswith("combined_"):
                posting_number = data.replace("combined_", "")
                self.get_combined_barcode_label(call.message.chat.id, posting_number)
            elif data.startswith("product_"):
                # Обработка кнопок товаров из заказов
                parts = data.split("_")
                if len(parts) >= 3:
                    sku = parts[1]
                    posting_number = parts[2]
                    self.show_product_from_order(call.message.chat.id, sku, posting_number)
            elif data.startswith("product_detail_"):
                product_id = data.replace("product_detail_", "")
                if product_id.isdigit():
                    self.show_product_details(call.message.chat.id, product_id)
                else:
                    self.bot.send_message(call.message.chat.id, "❌ Неверный ID товара")
            elif data.startswith("item_detail_"):
                product_id = data.replace("item_detail_", "")
                if product_id.isdigit():
                    self.show_product_details(call.message.chat.id, product_id)
                else:
                    self.bot.send_message(call.message.chat.id, "❌ Неверный ID товара")
            elif data.startswith("edit_stock_"):
                product_id = data.replace("edit_stock_", "")
                self.show_edit_stock_menu(call.message.chat.id, product_id)
            elif data.startswith("update_stock_"):
                # Формат: update_stock_{product_id}_{new_stock}
                parts = data.replace("update_stock_", "").split("_")
                if len(parts) >= 2:
                    product_id = parts[0]
                    new_stock = int(parts[1])
                    self.update_product_stock(call.message.chat.id, product_id, new_stock)
            elif data.startswith("barcode_"):
                # Обработка получения штрихкода товара
                product_id = data.replace("barcode_", "")
                self.get_product_barcode_by_id(call.message.chat.id, product_id)
            elif data == "start_monitoring":
                self.start_monitoring(call.message.chat.id)
            elif data == "stop_monitoring":
                self.stop_monitoring(call.message.chat.id)
            elif data == "monitoring_status":
                self.show_monitoring_status(call.message.chat.id)
    
    def show_packaging_orders(self, chat_id: int):
        """Показать заказы на сборку"""
        self.bot.send_message(chat_id, "⏳ Загружаю заказы на сборку...")
        
        result = self.ozon_api.get_orders_for_packaging(limit=20)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении заказов: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        orders = result.get("result", {}).get("postings", [])
        
        if not orders:
            text = "✅ Заказов на сборку не найдено"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
            return
        
        text = f"📦 <b>Заказы на сборку ({len(orders)})</b>\n\n"
        keyboard = types.InlineKeyboardMarkup()
        
        # Получаем информацию о товарах для всех заказов
        all_skus = []
        for order in orders[:10]:
            products = order.get("products", [])
            for product in products:
                sku = str(product.get('sku', ''))
                if sku and sku != 'N/A':
                    all_skus.append(sku)
        
        # Получаем детали товаров для эмодзи
        product_details = {}
        if all_skus:
            try:
                url = f"{self.ozon_api.base_url}/v3/product/info/list"
                payload = {"sku": all_skus}
                response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                response.raise_for_status()
                detailed_result = response.json()
                detailed_products = detailed_result.get("items", [])
                
                for product_detail in detailed_products:
                    sku = str(product_detail.get('sku', ''))
                    product_details[sku] = product_detail
            except Exception as e:
                logger.error(f"Ошибка при получении деталей товаров для списка заказов на сборку: {e}")
        
        for order in orders[:10]:  # Показываем первые 10
            posting_number = order.get("posting_number", "N/A")
            shipment_date = order.get("shipment_date", "N/A")
            
            # Получаем эмодзи товаров для этого заказа
            order_emojis = []
            products = order.get("products", [])
            for product in products:
                sku = str(product.get('sku', ''))
                product_name = product.get('name', 'N/A')
                
                if sku in product_details:
                    detailed_product = product_details[sku]
                    color = self.extract_color_from_product(detailed_product, product_name)
                    color_emoji = self.get_color_emoji(color.lower())
                    type_emoji = self.get_product_type_emoji(product_name)
                    
                    # Объединяем эмодзи (тип + цвет)
                    main_emoji = type_emoji
                    if color_emoji:
                        main_emoji = f"{type_emoji}{color_emoji}"
                    
                    order_emojis.append(main_emoji)
                else:
                    # Если нет деталей, используем только тип товара
                    type_emoji = self.get_product_type_emoji(product_name)
                    order_emojis.append(type_emoji)
            
            # Обрезаем номер заказа для кнопки
            short_number = posting_number[:12] + "..." if len(posting_number) > 15 else posting_number
            
            # Добавляем эмодзи товаров в текст и кнопку
            emojis_text = "".join(order_emojis[:3]) if order_emojis else "📦"  # Максимум 3 эмодзи
            
            text += f"{emojis_text} <b>{posting_number}</b>\n"
            text += f"📅 {shipment_date}\n\n"
            
            # Кнопка для деталей заказа с эмодзи
            keyboard.row(types.InlineKeyboardButton(
                f"{emojis_text} {short_number}", 
                callback_data=f"order_{posting_number}"
            ))
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_delivery_orders(self, chat_id: int):
        """Показать заказы готовые к отгрузке"""
        self.bot.send_message(chat_id, "⏳ Загружаю заказы готовые к отгрузке...")
        
        result = self.ozon_api.get_orders_awaiting_deliver(limit=20)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении заказов: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        orders = result.get("result", {}).get("postings", [])
        
        if not orders:
            text = "✅ Заказов готовых к отгрузке не найдено"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
            return
        
        text = f"🚚 <b>Готовые к отгрузке ({len(orders)})</b>\n\n"
        keyboard = types.InlineKeyboardMarkup()
        
        # Получаем информацию о товарах для всех заказов
        all_skus = []
        for order in orders[:10]:
            products = order.get("products", [])
            for product in products:
                sku = str(product.get('sku', ''))
                if sku and sku != 'N/A':
                    all_skus.append(sku)
        
        # Получаем детали товаров для эмодзи
        product_details = {}
        if all_skus:
            try:
                url = f"{self.ozon_api.base_url}/v3/product/info/list"
                payload = {"sku": all_skus}
                response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                response.raise_for_status()
                detailed_result = response.json()
                detailed_products = detailed_result.get("items", [])
                
                for product_detail in detailed_products:
                    sku = str(product_detail.get('sku', ''))
                    product_details[sku] = product_detail
            except Exception as e:
                logger.error(f"Ошибка при получении деталей товаров для списка заказов: {e}")
        
        for order in orders[:10]:  # Показываем первые 10
            posting_number = order.get("posting_number", "N/A")
            shipment_date = order.get("shipment_date", "N/A")
            
            # Получаем эмодзи товаров для этого заказа
            order_emojis = []
            products = order.get("products", [])
            for product in products:
                sku = str(product.get('sku', ''))
                product_name = product.get('name', 'N/A')
                
                if sku in product_details:
                    detailed_product = product_details[sku]
                    color = self.extract_color_from_product(detailed_product, product_name)
                    color_emoji = self.get_color_emoji(color.lower())
                    type_emoji = self.get_product_type_emoji(product_name)
                    
                    # Объединяем эмодзи (тип + цвет)
                    main_emoji = type_emoji
                    if color_emoji:
                        main_emoji = f"{type_emoji}{color_emoji}"
                    
                    order_emojis.append(main_emoji)
                else:
                    # Если нет деталей, используем только тип товара
                    type_emoji = self.get_product_type_emoji(product_name)
                    order_emojis.append(type_emoji)
            
            # Обрезаем номер заказа для кнопки
            short_number = posting_number[:12] + "..." if len(posting_number) > 15 else posting_number
            
            # Добавляем эмодзи товаров в текст и кнопку
            emojis_text = "".join(order_emojis[:3]) if order_emojis else "📦"  # Максимум 3 эмодзи
            
            text += f"{emojis_text} <b>{posting_number}</b>\n"
            text += f"📅 {shipment_date}\n\n"
            
            # Кнопка для просмотра деталей заказа с эмодзи
            keyboard.row(types.InlineKeyboardButton(
                f"{emojis_text} {short_number}", 
                callback_data=f"order_{posting_number}"
            ))
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_order_details(self, chat_id: int, posting_number: str):
        """Показать детали заказа с фото товаров"""
        self.bot.send_message(chat_id, f"⏳ Загружаю детали заказа {posting_number}...")
        
        result = self.ozon_api.get_order_details(posting_number)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении деталей заказа: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        order = result.get("result", {})
        
        # Основная информация
        text = f"📋 <b>Заказ {posting_number}</b>\n\n"
        text += f"<b>Статус:</b> {FBS_STATUSES.get(order.get('status', ''), order.get('status', 'N/A'))}\n"
        text += f"<b>Дата отгрузки:</b> {order.get('shipment_date', 'N/A')}\n"
        text += f"<b>Дата доставки:</b> {order.get('delivering_date', 'N/A')}\n"
        text += f"<b>Склад:</b> {order.get('warehouse', {}).get('name', 'N/A')}\n\n"
        
        # Информация о покупателе
        customer = order.get("customer", {})
        if customer:
            text += f"<b>Покупатель:</b> {customer.get('name', 'N/A')}\n"
            text += f"<b>Телефон:</b> {customer.get('phone', 'N/A')}\n\n"
        
        # Товары
        products = order.get("products", [])
        product_emojis = []  # Инициализируем список эмодзи товаров
        if products:
            text += f"<b>Товары ({len(products)}):</b>\n"
            
            # Получаем изображения товаров через правильный API
            sku_list = [str(product.get('sku', '')) for product in products if product.get('sku')]
            images_data = {}
            if sku_list:
                try:
                    logger.debug(f"Запрашиваем детали товаров для получения изображений: {sku_list}")
                    url = f"{self.ozon_api.base_url}/v3/product/info/list"
                    payload = {"sku": sku_list}
                    response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                    response.raise_for_status()
                    detailed_result = response.json()
                    detailed_products = detailed_result.get("items", [])
                    
                    for product_detail in detailed_products:
                        sku = str(product_detail.get('sku', ''))
                        # Получаем изображения из правильного поля
                        images = product_detail.get('images', [])
                        if not images:
                            # Пробуем получить primary_image
                            primary_images = product_detail.get('primary_image', [])
                            if primary_images:
                                images = primary_images
                        
                        if images and len(images) > 0:
                            images_data[sku] = images[0]  # Берем первое изображение
                            logger.debug(f"Найдено изображение для товара {sku}: {images[0]}")
                        else:
                            logger.debug(f"Нет изображений для товара {sku}")
                            
                except Exception as e:
                    logger.error(f"Ошибка при получении изображений: {e}")
            
            # Используем уже полученную детальную информацию о товарах
            product_details = {}
            for product_detail in detailed_products:
                sku = str(product_detail.get('sku', ''))
                product_details[sku] = product_detail
            
            # Собираем фото товаров для отправки в одном сообщении
            product_photos = []
            product_emojis = []
            
            for i, product in enumerate(products[:5]):  # Показываем первые 5 товаров
                product_name = product.get('name', 'N/A')
                quantity = product.get('quantity', 1)
                sku = str(product.get('sku', ''))
                
                # Получаем цвет товара и тип товара
                detailed_product = product_details.get(sku, {})
                color = self.extract_color_from_product(detailed_product, product_name)
                color_emoji = self.get_color_emoji(color.lower())
                type_emoji = self.get_product_type_emoji(product_name)
                
                # Обрезаем название товара
                short_name = product_name[:30] + "..." if len(product_name) > 30 else product_name
                
                # Объединяем эмодзи (тип + цвет)
                main_emoji = type_emoji
                if color_emoji:
                    main_emoji = f"{type_emoji}{color_emoji}"
                
                text += f"• {main_emoji} <b>{short_name}</b> x{quantity}\n"
                
                # Собираем фото и эмодзи для отправки
                if sku and str(sku) in images_data:
                    try:
                        logger.debug(f"Добавляем фото для товара {sku}: {images_data[str(sku)]}")
                        product_photos.append(images_data[str(sku)])
                        product_emojis.append(main_emoji)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке фото товара {sku}: {e}")
                else:
                    logger.debug(f"Нет изображения для товара {sku}")
                    product_emojis.append(main_emoji)
            
            # Отправляем все фото товаров в одном сообщении
            if product_photos:
                try:
                    logger.debug(f"Отправляем {len(product_photos)} фото товаров в одном сообщении")
                    self.bot.send_media_group(
                        chat_id=chat_id,
                        media=[types.InputMediaPhoto(photo) for photo in product_photos]
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке группы фото: {e}")
                    # Если не удалось отправить группу, отправляем по одному
                    for photo in product_photos:
                        try:
                            self.bot.send_photo(chat_id=chat_id, photo=photo)
                        except Exception as e:
                            logger.error(f"Ошибка при отправке отдельного фото: {e}")
            
            if len(products) > 5:
                text += f"... и еще {len(products) - 5} товаров\n"
        
        keyboard = types.InlineKeyboardMarkup()
        
        # Кнопка для сборки заказа (если статус awaiting_packaging)
        if order.get("status") == "awaiting_packaging":
            keyboard.row(types.InlineKeyboardButton(
                "📦 Собрать заказ", 
                callback_data=f"ship_{posting_number}"
            ))
        
        # Кнопка для получения этикетки (если статус awaiting_deliver)
        elif order.get("status") == "awaiting_deliver":
            keyboard.row(types.InlineKeyboardButton(
                "🏷️ Этикетка", 
                callback_data=f"download_label_{posting_number}"
            ))
        
        # Кнопка для просмотра товаров (доступна всегда) с эмодзи товаров
        product_emojis_text = "".join(product_emojis[:3]) if product_emojis else "📦"
        keyboard.row(types.InlineKeyboardButton(f"📋 {product_emojis_text} Товары", callback_data=f"products_{posting_number}"))
        
        # Кнопка для получения штрихкодов всех товаров заказа
        keyboard.row(types.InlineKeyboardButton("📊 Штрихкоды всех товаров", callback_data=f"barcodes_{posting_number}"))
        
        # Кнопка для получения штрихкодов + этикетки в одном файле
        keyboard.row(types.InlineKeyboardButton("📊📦 Штрихкоды + Этикетка", callback_data=f"combined_{posting_number}"))
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def ship_order(self, chat_id: int, posting_number: str, original_message_id: int = None):
        """Собрать заказ"""
        # Отправляем сообщение о процессе сборки
        processing_msg = self.bot.send_message(chat_id, f"⏳ Собираю заказ {posting_number}...")
        
        # Получаем детали заказа для создания packages
        result = self.ozon_api.get_order_details(posting_number)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении деталей заказа: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        order = result.get("result", {})
        products = order.get("products", [])
        
        # Создаем packages для сборки
        packages = [{
            "products": [
                {
                    "product_id": product.get("sku"),
                    "quantity": product.get("quantity", 1)
                }
                for product in products
            ]
        }]
        
        # Отправляем запрос на сборку
        ship_result = self.ozon_api.ship_order(posting_number, packages)
        
        if "error" in ship_result:
            error_text = f"❌ Ошибка при сборке заказа: {ship_result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        # Удаляем сообщение о процессе сборки
        try:
            self.bot.delete_message(chat_id, processing_msg.message_id)
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения о процессе: {e}")
        
        # Удаляем исходное сообщение с кнопкой "Собрать заказ"
        if original_message_id:
            try:
                self.bot.delete_message(chat_id, original_message_id)
            except Exception as e:
                logger.error(f"Ошибка при удалении исходного сообщения: {e}")
        
        # Заказ успешно собран - показываем полную информацию о заказе с кнопками для собранного заказа
        # Получаем детали заказа для отображения
        order_result = self.ozon_api.get_order_details(posting_number)
        
        if "error" in order_result:
            # Если не удалось получить детали, показываем простое сообщение об успехе
            text = f"✅ <b>Заказ {posting_number} успешно собран!</b>\n\n"
            text += f"Теперь заказ готов к отгрузке. Вы можете получить этикетку для печати."
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton(
                "🏷️ Этикетка", 
                callback_data=f"download_label_{posting_number}"
            ))
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        order = order_result.get("result", {})
        products = order.get("products", [])
        
        # Формируем текст с информацией о заказе
        text = f"✅ <b>Заказ {posting_number} успешно собран!</b>\n\n"
        text += f"📦 <b>Статус:</b> Готов к отгрузке\n"
        text += f"📅 <b>Дата сборки:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if products:
            text += f"📋 <b>Товары в заказе:</b>\n"
            for i, product in enumerate(products[:3], 1):  # Показываем первые 3 товара
                product_name = product.get('name', 'N/A')
                quantity = product.get('quantity', 1)
                # Обрезаем название товара
                short_name = product_name[:40] + "..." if len(product_name) > 40 else product_name
                text += f"• {short_name} x{quantity}\n"
            
            if len(products) > 3:
                text += f"... и еще {len(products) - 3} товаров\n"
        
        # Создаем клавиатуру с кнопками для собранного заказа (БЕЗ кнопки "Собрать заказ")
        keyboard = types.InlineKeyboardMarkup()
        
        # Кнопка для получения этикетки (главная кнопка для собранного заказа)
        keyboard.row(types.InlineKeyboardButton(
            "🏷️ Этикетка", 
            callback_data=f"download_label_{posting_number}"
        ))
        
        # Кнопка для просмотра товаров
        keyboard.row(types.InlineKeyboardButton(f"📋 Товары", callback_data=f"products_{posting_number}"))
        
        # Кнопка для получения штрихкодов всех товаров заказа
        keyboard.row(types.InlineKeyboardButton("📊 Штрихкоды всех товаров", callback_data=f"barcodes_{posting_number}"))
        
        # Кнопка для получения штрихкодов + этикетки в одном файле
        keyboard.row(types.InlineKeyboardButton("📊📦 Штрихкоды + Этикетка", callback_data=f"combined_{posting_number}"))
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_labels_menu(self, chat_id: int):
        """Показать меню этикеток"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🚚 Готовые к отгрузке", callback_data="delivery_orders"))
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        text = (
            "🏷️ <b>Этикетки для печати</b>\n\n"
            "Выберите заказы готовые к отгрузке для получения этикеток"
        )
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def get_single_label(self, chat_id: int, posting_number: str):
        """Получить этикетку для одного заказа"""
        self.bot.send_message(chat_id, f"⏳ Генерирую этикетку для {posting_number}...")
        
        result = self.ozon_api.get_package_label([posting_number])
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении этикетки: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        # Проверяем, что получили файл
        if isinstance(result, dict) and "file_content" in result:
            file_content = result["file_content"]
            file_name = result.get("file_name", f"label_{posting_number}.pdf")
            
            # Получаем информацию о заказе для названия товара
            order_result = self.ozon_api.get_order_details(posting_number)
            product_name = "Товар"
            
            if not order_result.get("error") and order_result.get("result", {}).get("products"):
                products = order_result["result"]["products"]
                if products:
                    product_name = products[0].get('name', 'Товар')
            
            # Генерируем умную этикетку
            smart_label = self.generate_smart_label(file_content, product_name, posting_number, products)
            
            if smart_label:
                # Отправляем умную этикетку как PNG
                smart_label.name = f"smart_label_{posting_number}.png"
                
                self.bot.send_document(
                    chat_id=chat_id,
                    document=smart_label,
                    caption=f"🏷️ Умная этикетка для заказа {posting_number}\n📦 {product_name}"
                )
            else:
                # Если не удалось сгенерировать умную этикетку, отправляем обычную PDF
                from io import BytesIO
                pdf_file = BytesIO(file_content)
                pdf_file.name = f"label_{posting_number}.pdf"
                
                self.bot.send_document(
                    chat_id=chat_id,
                    document=pdf_file,
                    caption=f"🏷️ Этикетка для заказа {posting_number}"
                )
            
            # Возвращаемся в меню
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, "✅ Этикетка отправлена!", reply_markup=keyboard)
        else:
            error_text = f"❌ Не удалось получить этикетку. Ответ API: {result}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
    
    def get_single_barcode(self, chat_id: int, posting_number: str):
        """Получить штрихкод для одного заказа"""
        self.bot.send_message(chat_id, f"⏳ Генерирую штрихкод для {posting_number}...")
        
        result = self.ozon_api.get_barcode(posting_number)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении штрихкода: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        # Проверяем, что получили файл
        if isinstance(result, dict) and "file_content" in result:
            file_content = result["file_content"]
            file_name = result.get("file_name", f"barcode_{posting_number}.png")
            
            # Отправляем изображение штрихкода
            from io import BytesIO
            barcode_file = BytesIO(file_content)
            barcode_file.name = file_name
            
            self.bot.send_document(
                chat_id=chat_id,
                document=barcode_file,
                caption=f"📊 Штрихкод для заказа {posting_number}"
            )
            
            # Возвращаемся в меню
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, "✅ Штрихкод отправлен!", reply_markup=keyboard)
        else:
            error_text = f"❌ Не удалось получить штрихкод. Ответ API: {result}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
    
    def show_order_products(self, chat_id: int, posting_number: str):
        """Показать товары заказа с цветными смайликами"""
        self.bot.send_message(chat_id, f"⏳ Загружаю товары заказа {posting_number}...")
        
        result = self.ozon_api.get_order_details(posting_number)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении деталей заказа: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        order = result.get("result", {})
        products = order.get("products", [])
        
        if not products:
            text = f"📦 <b>Товары заказа {posting_number}</b>\n\n❌ Товары не найдены"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Получаем детальную информацию о товарах для цветов
        sku_list = [str(product.get('sku', '')) for product in products if product.get('sku')]
        product_details = {}
        
        if sku_list:
            try:
                url = f"{self.ozon_api.base_url}/v3/product/info/list"
                payload = {"sku": sku_list}
                response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                response.raise_for_status()
                detailed_result = response.json()
                detailed_products = detailed_result.get("items", [])
                
                for p in detailed_products:
                    sku = str(p.get('sku', ''))
                    product_details[sku] = p
            except Exception as e:
                logger.error(f"Ошибка при получении деталей товаров: {e}")
        
        text = f"📦 <b>Товары заказа {posting_number}</b>\n\n"
        
        keyboard = types.InlineKeyboardMarkup()
        
        for i, product in enumerate(products):
            product_name = product.get('name', 'N/A')
            quantity = product.get('quantity', 1)
            sku = str(product.get('sku', ''))
            
            # Получаем цвет товара из детальной информации
            detailed_product = product_details.get(sku, {})
            color = self.extract_color_from_product(detailed_product, product_name)
            color_emoji = self.get_color_emoji(color.lower())
            
            # Обрезаем название товара для кнопки
            short_name = product_name[:25] + "..." if len(product_name) > 25 else product_name
            
            text += f"{color_emoji} <b>{short_name}</b> x{quantity}\n"
            
            # Добавляем кнопку для каждого товара
            keyboard.row(types.InlineKeyboardButton(
                f"{color_emoji} {short_name}", 
                callback_data=f"product_{sku}_{posting_number}"
            ))
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def get_product_type_emoji(self, product_name: str) -> str:
        """Получить смайлик по типу товара"""
        if not product_name or product_name == 'N/A':
            return '📦'
        
        name_lower = product_name.lower()
        
        # Словарь типов товаров и их эмодзи
        product_type_map = {
            # Чехлы и аксессуары для телефонов
            'чехол': '📱', 'чехлы': '📱', 'case': '📱', 'cover': '📱',
            'защитн': '🛡️', 'защита': '🛡️', 'protection': '🛡️',
            'стекло': '🪟', 'стекла': '🪟', 'glass': '🪟',
            'пленка': '🎞️', 'пленки': '🎞️', 'film': '🎞️',
            
            # Игрушки
            'игрушка': '🧸', 'игрушки': '🧸', 'toy': '🧸', 'toys': '🧸',
            'кукла': '👸', 'куклы': '👸', 'doll': '👸', 'dolls': '👸',
            'машинка': '🚗', 'машинки': '🚗', 'car': '🚗', 'cars': '🚗',
            'мяч': '⚽', 'мячи': '⚽', 'ball': '⚽', 'balls': '⚽',
            'конструктор': '🧱', 'конструкторы': '🧱', 'constructor': '🧱',
            'пазл': '🧩', 'пазлы': '🧩', 'puzzle': '🧩', 'puzzles': '🧩',
            
            # Одежда
            'футболка': '👕', 'футболки': '👕', 't-shirt': '👕', 'tshirt': '👕',
            'рубашка': '👔', 'рубашки': '👔', 'shirt': '👔', 'shirts': '👔',
            'платье': '👗', 'платья': '👗', 'dress': '👗', 'dresses': '👗',
            'брюки': '👖', 'брюк': '👖', 'pants': '👖', 'trousers': '👖',
            'куртка': '🧥', 'куртки': '🧥', 'jacket': '🧥', 'jackets': '🧥',
            'кроссовки': '👟', 'кроссовок': '👟', 'sneakers': '👟', 'shoes': '👟',
            'ботинки': '👢', 'ботинок': '👢', 'boots': '👢',
            'шапка': '🧢', 'шапки': '🧢', 'hat': '🧢', 'cap': '🧢',
            
            # Электроника
            'наушники': '🎧', 'наушник': '🎧', 'headphones': '🎧', 'earphones': '🎧',
            'зарядка': '🔌', 'зарядки': '🔌', 'charger': '🔌', 'charging': '🔌',
            'кабель': '🔌', 'кабели': '🔌', 'cable': '🔌', 'cables': '🔌',
            'аккумулятор': '🔋', 'аккумуляторы': '🔋', 'battery': '🔋', 'batteries': '🔋',
            'динамик': '🔊', 'динамики': '🔊', 'speaker': '🔊', 'speakers': '🔊',
            'микрофон': '🎤', 'микрофоны': '🎤', 'microphone': '🎤', 'mic': '🎤',
            
            # Дом и сад
            'лампа': '💡', 'лампы': '💡', 'lamp': '💡', 'light': '💡',
            'свеча': '🕯️', 'свечи': '🕯️', 'candle': '🕯️', 'candles': '🕯️',
            'ваза': '🏺', 'вазы': '🏺', 'vase': '🏺', 'vases': '🏺',
            'горшок': '🪴', 'горшки': '🪴', 'pot': '🪴', 'pots': '🪴',
            'ковер': '🪞', 'ковры': '🪞', 'carpet': '🪞', 'rug': '🪞',
            
            # Спорт
            'гантели': '🏋️', 'гантель': '🏋️', 'dumbbell': '🏋️', 'weights': '🏋️',
            'скакалка': '🪢', 'скакалки': '🪢', 'rope': '🪢', 'jump rope': '🪢',
            'велосипед': '🚲', 'велосипеды': '🚲', 'bicycle': '🚲', 'bike': '🚲',
            'ролики': '🛼', 'ролик': '🛼', 'skates': '🛼', 'skate': '🛼',
            
            # Книги и канцелярия
            'книга': '📚', 'книги': '📚', 'book': '📚', 'books': '📚',
            'тетрадь': '📓', 'тетради': '📓', 'notebook': '📓', 'notebooks': '📓',
            'ручка': '✏️', 'ручки': '✏️', 'pen': '✏️', 'pens': '✏️',
            'карандаш': '✏️', 'карандаши': '✏️', 'pencil': '✏️', 'pencils': '✏️',
            'маркер': '🖍️', 'маркеры': '🖍️', 'marker': '🖍️', 'markers': '🖍️',
            
            # Красота и здоровье
            'крем': '🧴', 'кремы': '🧴', 'cream': '🧴', 'creams': '🧴',
            'шампунь': '🧴', 'шампуни': '🧴', 'shampoo': '🧴', 'shampoos': '🧴',
            'мыло': '🧼', 'мыла': '🧼', 'soap': '🧼', 'soaps': '🧼',
            'зубная': '🦷', 'зубной': '🦷', 'tooth': '🦷', 'dental': '🦷',
            'щетка': '🪥', 'щетки': '🪥', 'brush': '🪥', 'brushes': '🪥',
            
            # Кухня
            'тарелка': '🍽️', 'тарелки': '🍽️', 'plate': '🍽️', 'plates': '🍽️',
            'чашка': '☕', 'чашки': '☕', 'cup': '☕', 'cups': '☕',
            'ложка': '🥄', 'ложки': '🥄', 'spoon': '🥄', 'spoons': '🥄',
            'вилка': '🍴', 'вилки': '🍴', 'fork': '🍴', 'forks': '🍴',
            'нож': '🔪', 'ножи': '🔪', 'knife': '🔪', 'knives': '🔪',
            
            # Автомобиль
            'автомобиль': '🚗', 'автомобили': '🚗', 'car': '🚗', 'cars': '🚗',
            'машина': '🚗', 'машины': '🚗', 'auto': '🚗', 'vehicle': '🚗',
            'шина': '🛞', 'шины': '🛞', 'tire': '🛞', 'tyre': '🛞',
            'диск': '🛞', 'диски': '🛞', 'wheel': '🛞', 'rim': '🛞',
        }
        
        # Ищем совпадения в названии товара
        for keyword, emoji in product_type_map.items():
            if keyword in name_lower:
                return emoji
        
        return '📦'  # По умолчанию коробка
    
    def get_color_emoji(self, color: str) -> str:
        """Получить смайлик по цвету товара"""
        color_map = {
            'красный': '🔴', 'red': '🔴',
            'синий': '🔵', 'blue': '🔵',
            'зеленый': '🟢', 'green': '🟢',
            'желтый': '🟡', 'yellow': '🟡',
            'оранжевый': '🟠', 'orange': '🟠',
            'фиолетовый': '🟣', 'purple': '🟣',
            'розовый': '🩷', 'pink': '🩷',
            'фуксия': '🟣', 'fuchsia': '🟣',
            'коричневый': '🟤', 'brown': '🟤',
            'черный': '⚫', 'black': '⚫',
            'белый': '⚪', 'white': '⚪',
            'серый': '🔘', 'gray': '🔘', 'grey': '🔘',
            'золотой': '🟨', 'gold': '🟨',
            'серебряный': '⚪', 'silver': '⚪',
            'радужный': '🌈', 'радужная': '🌈', 'радужное': '🌈', 'rainbow': '🌈',
            'разноцветный': '🌈', 'разноцветная': '🌈', 'разноцветное': '🌈', 'multicolor': '🌈'
        }
        
        return color_map.get(color, '')  # Возвращаем пустую строку, если цвет не найден
    
    def extract_color_from_product(self, product_data: dict, product_name: str) -> str:
        """Извлечь цвет товара из API или из названия"""
        # Сначала пытаемся получить цвет из API
        color_image = product_data.get('color_image', [])
        if color_image:
            return color_image[0] if isinstance(color_image, list) else str(color_image)
        
        # Если цвета нет в API, ищем в названии
        if not product_name or product_name == 'N/A':
            return 'N/A'
        
        name_lower = product_name.lower()
        
        # Список цветов для поиска (учитываем е/ё, й/и)
        color_patterns = {
            'красн': 'красный',
            'син': 'синий', 
            'голуб': 'голубой',
            'зелен': 'зеленый',
            'желт': 'желтый',
            'оранж': 'оранжевый',
            'фиолет': 'фиолетовый',
            'розов': 'розовый',
            'фукси': 'фуксия',
            'коричнев': 'коричневый',
            'черн': 'черный',
            'бел': 'белый',
            'сер': 'серый',
            'золот': 'золотой',
            'серебр': 'серебряный',
            'радужн': 'радужный',
            'разноцветн': 'разноцветный',
            'multicolor': 'разноцветный',
            'rainbow': 'радужный',
            'red': 'красный',
            'blue': 'синий',
            'green': 'зеленый',
            'yellow': 'желтый',
            'orange': 'оранжевый',
            'purple': 'фиолетовый',
            'pink': 'розовый',
            'fuchsia': 'фуксия',
            'brown': 'коричневый',
            'black': 'черный',
            'white': 'белый',
            'gray': 'серый',
            'grey': 'серый',
            'gold': 'золотой',
            'silver': 'серебряный'
        }
        
        for pattern, color in color_patterns.items():
            if pattern in name_lower:
                return color
        
        return 'N/A'
    
    def show_all_products_menu(self, chat_id: int, page: int = 0):
        """Показать все товары на продаже"""
        self.bot.send_message(chat_id, "⏳ Загружаю все товары на продаже...")
        
        result = self.ozon_api.get_all_products()
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении товаров: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        products = result.get("result", {}).get("items", [])
        
        if not products:
            text = "📦 <b>Все товары</b>\n\n❌ Товары не найдены"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Пагинация - по 10 товаров на страницу
        items_per_page = 10
        total_pages = (len(products) + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(products))
        page_products = products[start_idx:end_idx]
        
        text = f"📦 <b>Все товары на продаже ({len(products)})</b>\n"
        text += f"📄 Страница {page + 1} из {total_pages}\n\n"
        
        keyboard = types.InlineKeyboardMarkup()
        
        # Получаем детальную информацию о товарах на текущей странице
        product_ids = [int(p.get('product_id', 0)) for p in page_products if p.get('product_id')]
        
        if product_ids:
            url = f"{self.ozon_api.base_url}/v3/product/info/list"
            payload = {
                "product_id": product_ids
            }
            
            try:
                response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                response.raise_for_status()
                detailed_result = response.json()
                detailed_products = detailed_result.get("items", [])
                
                # Создаем словарь для быстрого поиска
                product_details = {str(p.get('id', '')): p for p in detailed_products}
                
            except Exception as e:
                logger.error(f"Ошибка при получении деталей товаров: {e}")
                product_details = {}
        else:
            product_details = {}
        
        # Добавляем товары на текущей странице
        for product in page_products:
            product_id = str(product.get('product_id', ''))
            detailed_product = product_details.get(product_id, {})
            
            product_name = detailed_product.get('name', 'N/A')
            
            # Получаем эмодзи для типа товара и цвета
            type_emoji = self.get_product_type_emoji(product_name)
            color = self.extract_color_from_product(detailed_product, product_name)
            color_emoji = self.get_color_emoji(color.lower())
            
            # Объединяем эмодзи (тип + цвет)
            main_emoji = type_emoji
            if color_emoji:
                main_emoji = f"{type_emoji}{color_emoji}"
            
            # Обрезаем название для кнопки
            short_name = product_name[:20] + "..." if len(product_name) > 20 else product_name
            button_text = f"{main_emoji} {short_name}"
            
            keyboard.row(types.InlineKeyboardButton(
                button_text,
                callback_data=f"item_detail_{product_id}"
            ))
        
        # Добавляем навигацию
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️", callback_data=f"products_page_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("➡️", callback_data=f"products_page_{page+1}"))
        
        if nav_buttons:
            keyboard.row(*nav_buttons)
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_products_by_status(self, chat_id: int, status: str):
        """Показать товары по статусу заказа"""
        status_text = "на сборку" if status == "awaiting_packaging" else "готовые к отгрузке"
        self.bot.send_message(chat_id, f"⏳ Загружаю товары {status_text}...")
        
        if status == "awaiting_packaging":
            result = self.ozon_api.get_orders_for_packaging()
        else:
            result = self.ozon_api.get_orders_awaiting_deliver()
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении заказов: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        orders = result.get("result", {}).get("postings", [])
        
        if not orders:
            text = f"📦 <b>Товары {status_text}</b>\n\n❌ Заказы не найдены"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Собираем все товары из всех заказов
        all_products = {}
        for order in orders:
            posting_number = order.get("posting_number", "")
            products = order.get("products", [])
            
            for product in products:
                sku = product.get('sku', '')
                if sku:
                    product_name = product.get('name', 'N/A')
                    quantity = product.get('quantity', 1)
                    color = product.get('color', '').lower()
                    
                    if sku not in all_products:
                        all_products[sku] = {
                            'name': product_name,
                            'total_quantity': 0,
                            'color': color,
                            'orders': []
                        }
                    
                    all_products[sku]['total_quantity'] += quantity
                    all_products[sku]['orders'].append(posting_number)
        
        text = f"📦 <b>Товары {status_text}</b>\n\n"
        
        keyboard = types.InlineKeyboardMarkup()
        
        for sku, product_info in list(all_products.items())[:10]:  # Показываем первые 10 товаров
            product_name = product_info['name']
            total_quantity = product_info['total_quantity']
            color = product_info['color']
            
            # Выбираем смайлик по цвету
            color_emoji = self.get_color_emoji(color)
            
            # Обрезаем название товара для кнопки
            short_name = product_name[:20] + "..." if len(product_name) > 20 else product_name
            
            text += f"{color_emoji} <b>{short_name}</b> x{total_quantity}\n"
            
            # Добавляем кнопку для каждого товара
            keyboard.row(types.InlineKeyboardButton(
                f"{color_emoji} {short_name}", 
                callback_data=f"product_info_{sku}"
            ))
        
        if len(all_products) > 10:
            text += f"\n... и еще {len(all_products) - 10} товаров"
        
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_product_details(self, chat_id: int, product_id: str):
        """Показать детали товара"""
        self.bot.send_message(chat_id, f"⏳ Загружаю детали товара {product_id}...")
        
        # Получаем детали товара через правильный API
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "product_id": [int(product_id)]
        }
        
        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            
            # Логируем ответ для отладки
            logger.debug(f"Ответ API для товара {product_id}: {response.status_code}")
            logger.debug(f"Содержимое ответа: {response.text[:500]}...")
            
            result = response.json()
            
            # Логируем тип и содержимое result
            logger.debug(f"Тип result: {type(result)}")
            logger.debug(f"Содержимое result: {result}")
            
            # Проверяем, что result - это словарь
            if not isinstance(result, dict):
                logger.error(f"Неожиданный тип результата: {type(result)}, значение: {result}")
                text = f"📦 <b>Товар {product_id}</b>\n\n❌ Ошибка формата ответа API"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            if not result.get("items"):
                text = f"📦 <b>Товар {product_id}</b>\n\n❌ Товар не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            # Проверяем, что items - это список
            items = result.get("items", [])
            if not items or len(items) == 0:
                text = f"📦 <b>Товар {product_id}</b>\n\n❌ Товар не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            product = items[0]
            
            # Проверяем, что product - это словарь
            if not isinstance(product, dict):
                logger.error(f"Product не является словарем: {type(product)}, значение: {product}")
                text = f"📦 <b>Товар {product_id}</b>\n\n❌ Ошибка формата данных товара"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            logger.debug(f"Product получен успешно: {type(product)}")
            logger.debug(f"Product содержимое: {product}")
            
            # Безопасно получаем поля товара
            product_name = product.get('name', 'N/A') if isinstance(product, dict) else 'N/A'
            logger.debug(f"product_name получен: {product_name}")
            
            sku = product.get('sku', 'N/A') if isinstance(product, dict) else 'N/A'
            logger.debug(f"sku получен: {sku}")
            
            offer_id = product.get('offer_id', 'N/A') if isinstance(product, dict) else 'N/A'
            logger.debug(f"offer_id получен: {offer_id}")
            
            # Получаем цвет из характеристик
            color = "N/A"
            if isinstance(product, dict):
                color_image = product.get('color_image', [])
                if color_image:
                    color = color_image[0] if isinstance(color_image, list) else str(color_image)
            
            # Получаем цену
            price = "N/A"
            if isinstance(product, dict):
                if 'marketing_price' in product:
                    price = product['marketing_price']
                elif 'price' in product:
                    price = product['price']
            
            # Получаем остатки
            stock = "N/A"
            if isinstance(product, dict) and 'stocks' in product and product['stocks']:
                stocks_data = product['stocks']
                if isinstance(stocks_data, dict) and 'stocks' in stocks_data:
                    # Новый формат API
                    stock_items = stocks_data['stocks']
                    if isinstance(stock_items, list):
                        total_stock = sum(stock_item.get('present', 0) for stock_item in stock_items)
                        stock = str(total_stock)
                elif isinstance(stocks_data, list):
                    # Старый формат API
                    total_stock = sum(stock_item.get('present', 0) for stock_item in stocks_data)
                    stock = str(total_stock)
            
            # Получаем эмодзи для типа товара и цвета
            type_emoji = self.get_product_type_emoji(product_name)
            color_emoji = self.get_color_emoji(color.lower())
            
            # Объединяем эмодзи (тип + цвет)
            main_emoji = type_emoji
            if color_emoji:
                main_emoji = f"{type_emoji}{color_emoji}"
            
            # Получаем дополнительную информацию
            old_price = "N/A"
            currency = "RUB"
            status = "N/A"
            created_at = "N/A"
            images = []
            
            if isinstance(product, dict):
                old_price = product.get('old_price', 'N/A')
                currency = product.get('currency_code', 'RUB')
                status_info = product.get('statuses', {})
                if isinstance(status_info, dict):
                    status = status_info.get('status_name', 'N/A')
                created_at = product.get('created_at', 'N/A')
                if created_at != 'N/A':
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        created_at = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        pass
                
                # Получаем изображения товара
                images = product.get('images', [])
                if not images:
                    # Пробуем получить primary_image
                    primary_images = product.get('primary_image', [])
                    if primary_images:
                        images = primary_images
            
            text = f"{main_emoji} <b>Товар {product_id}</b>\n\n"
            text += f"{main_emoji} <b>Название:</b> {product_name}\n"
            text += f"🏷️ <b>SKU:</b> {sku}\n"
            text += f"📋 <b>Offer ID:</b> {offer_id}\n"
            if color != 'N/A':
                text += f"{color_emoji} <b>Цвет:</b> {color}\n"
            text += f"💰 <b>Цена:</b> {price} {currency}\n"
            if old_price != 'N/A' and old_price != '':
                text += f"💸 <b>Старая цена:</b> {old_price} {currency}\n"
            text += f"📦 <b>Остаток:</b> {stock}\n"
            text += f"📊 <b>Статус:</b> {status}\n"
            text += f"📅 <b>Создан:</b> {created_at}\n"
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("📊 Штрихкод", callback_data=f"barcode_{product_id}"))
            keyboard.row(types.InlineKeyboardButton("📦 Изменить остаток", callback_data=f"edit_stock_{product_id}"))
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            
            # Отправляем сообщение с информацией и фотографиями в одном сообщении
            if images and len(images) > 0:
                try:
                    # Создаем медиагруппу с фотографиями
                    media_group = []
                    
                    # Первая фотография с текстом
                    first_photo = types.InputMediaPhoto(
                        media=images[0],
                        caption=text,
                        parse_mode="HTML"
                    )
                    media_group.append(first_photo)
                    
                    # Остальные фотографии без подписей (максимум 9, так как первая уже есть)
                    for image_url in images[1:10]:  # До 10 фотографий всего
                        media_group.append(types.InputMediaPhoto(media=image_url))
                    
                    # Отправляем медиагруппу
                    sent_messages = self.bot.send_media_group(chat_id, media_group)
                    
                    # Добавляем клавиатуру к первому сообщению
                    if sent_messages and len(sent_messages) > 0:
                        try:
                            self.bot.edit_message_reply_markup(
                                chat_id=chat_id,
                                message_id=sent_messages[0].message_id,
                                reply_markup=keyboard
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении клавиатуры: {e}")
                            # Если не удалось добавить клавиатуру, отправляем отдельное сообщение с кнопками
                            self.bot.send_message(chat_id, "Выберите действие:", reply_markup=keyboard)
                        
                except Exception as e:
                    logger.error(f"Ошибка при отправке медиагруппы: {e}")
                    # Если не удалось отправить медиагруппу, отправляем обычное сообщение
                    self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            else:
                # Если нет фотографий, отправляем только текст
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                logger.debug(f"Нет изображений для товара {product_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при получении товара: {e}")
            text = f"❌ Ошибка при получении товара: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def get_product_barcode_by_id(self, chat_id: int, product_id: str):
        """Получить штрихкод товара с красивым изображением"""
        self.bot.send_message(chat_id, f"⏳ Получаю штрихкод для товара {product_id}...")
        
        # Сначала пробуем найти товар по SKU
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "sku": [int(product_id)]
        }
        
        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            # Если не найден по SKU, пробуем по product_id
            if not result.get("items"):
                payload = {
                    "product_id": [int(product_id)]
                }
                response = requests.post(url, headers=self.ozon_api.headers, json=payload)
                response.raise_for_status()
                result = response.json()
            
            if not result.get("items"):
                text = f"📊 <b>Штрихкод товара {product_id}</b>\n\n❌ Товар не найден ни по SKU, ни по Product ID"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            product = result["items"][0]
            product_name = product.get('name', 'N/A')
            sku = str(product.get('sku', ''))
            barcodes = product.get('barcodes', [])
            
            if not barcodes:
                text = f"📊 <b>Штрихкод товара {product_id}</b>\n\n❌ Штрихкоды не найдены"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            # Генерируем изображения для каждого штрихкода
            for i, barcode in enumerate(barcodes, 1):
                barcode_img = self.generate_barcode_image(barcode, product_name, sku, 1, "")
                
                if barcode_img:
                    # Отправляем изображение штрихкода
                    barcode_img.name = f"barcode_{product_id}_{i}.png"
                    
                    caption = f"📊 Штрихкод {i} для товара {product_id}\n📦 {product_name}\n🏷️ {barcode}"
                    self.bot.send_document(
                        chat_id=chat_id,
                        document=barcode_img,
                        caption=caption
                    )
                else:
                    # Если не удалось сгенерировать изображение, отправляем текстом
                    text = f"📊 <b>Штрихкод {i} товара {product_id}</b>\n\n"
                    text += f"📦 <b>Название:</b> {product_name}\n"
                    text += f"🏷️ <b>SKU:</b> {sku}\n"
                    text += f"📊 <b>Штрихкод:</b> {barcode}\n"
                    
                    self.bot.send_message(chat_id, text, parse_mode="HTML")
            
            # Возвращаемся в меню
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, "✅ Штрихкоды отправлены!", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при получении штрихкода: {e}")
            text = f"❌ Ошибка при получении штрихкода: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def get_order_barcodes(self, chat_id: int, posting_number: str):
        """Получить штрихкоды всех товаров заказа"""
        self.bot.send_message(chat_id, f"⏳ Получаю штрихкоды для всех товаров заказа {posting_number}...")
        
        # Получаем детали заказа
        result = self.ozon_api.get_order_details(posting_number)
        
        if "error" in result:
            error_text = f"❌ Ошибка при получении деталей заказа: {result['error']}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
            return
        
        order = result.get("result", {})
        products = order.get("products", [])
        
        if not products:
            text = f"📊 <b>Штрихкоды заказа {posting_number}</b>\n\n❌ Товары не найдены"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        # Получаем детальную информацию о товарах для получения штрихкодов
        sku_list = [str(product.get('sku', '')) for product in products if product.get('sku')]
        
        if not sku_list:
            text = f"📊 <b>Штрихкоды заказа {posting_number}</b>\n\n❌ SKU товаров не найдены"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            return
        
        try:
            url = f"{self.ozon_api.base_url}/v3/product/info/list"
            payload = {"sku": sku_list}
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            detailed_result = response.json()
            detailed_products = detailed_result.get("items", [])
            
            # Создаем словарь для быстрого поиска товаров по SKU
            products_by_sku = {str(p.get('sku', '')): p for p in detailed_products}
            
            # Генерируем штрихкоды для каждого товара
            barcodes_sent = 0
            
            for product in products:
                sku = str(product.get('sku', ''))
                product_name = product.get('name', 'N/A')
                quantity = product.get('quantity', 1)
                
                if sku in products_by_sku:
                    detailed_product = products_by_sku[sku]
                    barcodes = detailed_product.get('barcodes', [])
                    
                    if barcodes:
                        # Генерируем изображения для каждого штрихкода
                        for i, barcode in enumerate(barcodes, 1):
                            barcode_img = self.generate_barcode_image(barcode, product_name, sku, quantity, posting_number)
                            
                            if barcode_img:
                                # Отправляем изображение штрихкода
                                barcode_img.name = f"barcode_{posting_number}_{sku}_{i}.png"
                                
                                caption = f"📊 Штрихкод {i} для товара из заказа {posting_number}\n📦 {product_name}\n🏷️ SKU: {sku}\n📊 Штрихкод: {barcode}\n📦 Количество: {quantity}"
                                self.bot.send_document(
                                    chat_id=chat_id,
                                    document=barcode_img,
                                    caption=caption
                                )
                                barcodes_sent += 1
                            else:
                                # Если не удалось сгенерировать изображение, отправляем текстом
                                text = f"📊 <b>Штрихкод {i} товара из заказа {posting_number}</b>\n\n"
                                text += f"📦 <b>Название:</b> {product_name}\n"
                                text += f"🏷️ <b>SKU:</b> {sku}\n"
                                text += f"📊 <b>Штрихкод:</b> {barcode}\n"
                                text += f"📦 <b>Количество:</b> {quantity}\n"
                                
                                self.bot.send_message(chat_id, text, parse_mode="HTML")
                                barcodes_sent += 1
                    else:
                        # Если нет штрихкодов
                        text = f"📊 <b>Товар без штрихкода</b>\n\n"
                        text += f"📦 <b>Название:</b> {product_name}\n"
                        text += f"🏷️ <b>SKU:</b> {sku}\n"
                        text += f"📦 <b>Количество:</b> {quantity}\n"
                        text += f"❌ <b>Штрихкоды не найдены</b>\n"
                        
                        self.bot.send_message(chat_id, text, parse_mode="HTML")
            
            # Возвращаемся в меню
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 К заказу", callback_data=f"order_{posting_number}"))
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            
            if barcodes_sent > 0:
                self.bot.send_message(chat_id, f"✅ Отправлено {barcodes_sent} штрихкодов для заказа {posting_number}!", reply_markup=keyboard)
            else:
                self.bot.send_message(chat_id, f"❌ Штрихкоды не найдены для заказа {posting_number}", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при получении штрихкодов заказа: {e}")
            text = f"❌ Ошибка при получении штрихкодов заказа: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def get_combined_barcode_label(self, chat_id: int, posting_number: str):
        """Получить штрихкоды + этикетку в одном файле"""
        self.bot.send_message(chat_id, f"⏳ Создаю комбинированный файл для заказа {posting_number}...")
        
        try:
            # Получаем детали заказа
            result = self.ozon_api.get_order_details(posting_number)
            
            if "error" in result:
                error_text = f"❌ Ошибка при получении деталей заказа: {result['error']}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, error_text, reply_markup=keyboard)
                return
            
            order = result.get("result", {})
            products = order.get("products", [])
            
            if not products:
                text = f"❌ Товары не найдены для заказа {posting_number}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Получаем умную этикетку заказа
            label_result = self.ozon_api.get_package_label([posting_number])
            
            if "error" in label_result or "file_content" not in label_result:
                text = f"❌ Не удалось получить этикетку для заказа {posting_number}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Получаем информацию о заказе для названия товара
            product_name = "Товар"
            if products:
                product_name = products[0].get('name', 'Товар')
            
            # Генерируем умную этикетку
            smart_label = self.generate_smart_label(label_result["file_content"], product_name, posting_number, products)
            
            if not smart_label:
                text = f"❌ Не удалось сгенерировать умную этикетку для заказа {posting_number}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Получаем штрихкоды товаров
            sku_list = [str(product.get('sku', '')) for product in products if product.get('sku')]
            
            if not sku_list:
                text = f"❌ SKU товаров не найдены для заказа {posting_number}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Получаем детальную информацию о товарах
            url = f"{self.ozon_api.base_url}/v3/product/info/list"
            payload = {"sku": sku_list}
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            detailed_result = response.json()
            detailed_products = detailed_result.get("items", [])
            
            products_by_sku = {str(p.get('sku', '')): p for p in detailed_products}
            
            # Создаем комбинированное изображение
            combined_image = self.create_combined_barcode_label_image(
                posting_number, 
                products, 
                products_by_sku, 
                smart_label
            )
            
            if combined_image:
                # Отправляем комбинированное изображение
                combined_image.name = f"combined_{posting_number}.png"
                
                caption = f"📊📦 Комбинированный файл для заказа {posting_number}\n"
                caption += f"📦 Содержит: штрихкоды товаров + этикетка заказа"
                
                self.bot.send_document(
                    chat_id=chat_id,
                    document=combined_image,
                    caption=caption
                )
                
                # Возвращаемся в меню
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 К заказу", callback_data=f"order_{posting_number}"))
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                
                self.bot.send_message(chat_id, "✅ Комбинированный файл отправлен!", reply_markup=keyboard)
            else:
                text = f"❌ Не удалось создать комбинированный файл для заказа {posting_number}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка при создании комбинированного файла: {e}")
            text = f"❌ Ошибка при создании комбинированного файла: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def create_combined_barcode_label_image(self, posting_number: str, products: list, products_by_sku: dict, smart_label_bytesio):
        """Создать комбинированное изображение штрихкодов + умной этикетки"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            
            # Конвертируем умную этикетку из BytesIO в PIL Image
            smart_label_bytesio.seek(0)
            smart_label_img = Image.open(smart_label_bytesio)
            
            # Получаем размеры умной этикетки
            label_width, label_height = smart_label_img.size
            
            # Создаем штрихкоды для товаров
            barcode_images = []
            product_names = []
            
            for product in products:
                sku = str(product.get('sku', ''))
                product_name = product.get('name', 'N/A')
                quantity = product.get('quantity', 1)
                
                if sku in products_by_sku:
                    detailed_product = products_by_sku[sku]
                    barcodes = detailed_product.get('barcodes', [])
                    
                    if barcodes:
                        # Берем первый штрихкод
                        barcode = barcodes[0]
                        
                        # Генерируем изображение штрихкода для комбинированного изображения
                        barcode_img = self.generate_barcode_image_for_combined(barcode, product_name, sku)
                        
                        if barcode_img:
                            # Конвертируем BytesIO в PIL Image
                            barcode_img.seek(0)
                            barcode_pil = Image.open(barcode_img)
                            barcode_images.append(barcode_pil)
                            product_names.append(f"{product_name} x{quantity}")
            
            if not barcode_images:
                logger.error("Не удалось создать штрихкоды")
                return None
            
            # Рассчитываем размеры итогового изображения
            barcode_width = max(img.width for img in barcode_images)
            barcode_height = sum(img.height for img in barcode_images)
            
            # Добавляем отступы между штрихкодами
            padding = 20
            total_barcode_height = barcode_height + (len(barcode_images) - 1) * padding
            
            # Размеры итогового изображения - используем ширину этикетки как основу
            total_width = label_width  # Используем точную ширину этикетки без лишних отступов
            total_height = label_height + total_barcode_height + 20  # Минимальные отступы сверху и снизу
            
            # Создаем итоговое изображение
            combined_img = Image.new('RGB', (total_width, total_height), 'white')
            
            # Размещаем умную этикетку сверху по центру
            label_x = 0  # Этикетка занимает всю ширину
            combined_img.paste(smart_label_img, (label_x, 10))
            
            # Размещаем штрихкоды снизу - по центру под этикеткой
            current_y = label_height + 10
            
            for i, (barcode_img, product_name) in enumerate(zip(barcode_images, product_names)):
                # Размещаем штрихкод по центру под этикеткой
                barcode_x = (total_width - barcode_img.width) // 2
                combined_img.paste(barcode_img, (barcode_x, current_y))
                current_y += barcode_img.height + padding
            
            # Конвертируем в bytes с максимальным качеством
            img_bytes = BytesIO()
            combined_img.save(img_bytes, format='PNG', quality=100, optimize=False)  # Максимальное качество
            img_bytes.seek(0)
            
            # Включаем умную обрезку для удаления лишнего пространства
            img_bytes = self.smart_crop_image(img_bytes)
            
            return img_bytes
            
        except ImportError:
            logger.error("Библиотека PIL не установлена")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании комбинированного изображения: {e}")
            return None
    
    def show_edit_stock_menu(self, chat_id: int, product_id: str):
        """Показать меню для изменения остатка товара"""
        self.bot.send_message(chat_id, f"⏳ Загружаю информацию о товаре {product_id}...")
        
        # Получаем информацию о товаре
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "product_id": [int(product_id)]
        }
        
        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if not result.get("items"):
                text = f"❌ Товар {product_id} не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            product = result["items"][0]
            product_name = product.get('name', 'N/A')
            offer_id = product.get('offer_id', '')
            sku = str(product.get('sku', ''))
            
            # Получаем текущие остатки FBS
            fbs_stocks = self.ozon_api.get_fbs_stocks([sku])
            current_stock = 0
            
            if not fbs_stocks.get("error") and fbs_stocks.get("result"):
                for stock_info in fbs_stocks["result"]:
                    if str(stock_info.get('sku', '')) == sku:
                        current_stock = stock_info.get('present', 0)
                        break
            
            # Получаем эмодзи для товара
            type_emoji = self.get_product_type_emoji(product_name)
            
            text = f"{type_emoji} <b>Изменение остатка товара</b>\n\n"
            text += f"{type_emoji} <b>Название:</b> {product_name}\n"
            text += f"🏷️ <b>SKU:</b> {sku}\n"
            text += f"📋 <b>Offer ID:</b> {offer_id}\n"
            text += f"📦 <b>Текущий остаток FBS:</b> {current_stock}\n\n"
            text += f"Выберите новое количество:"
            
            keyboard = types.InlineKeyboardMarkup()
            
            # Кнопки с популярными значениями остатков
            stock_values = [0, 1, 5, 10, 20, 50, 100]
            for i in range(0, len(stock_values), 2):
                row_buttons = []
                for j in range(2):
                    if i + j < len(stock_values):
                        value = stock_values[i + j]
                        row_buttons.append(types.InlineKeyboardButton(
                            f"{value}", 
                            callback_data=f"update_stock_{product_id}_{value}"
                        ))
                keyboard.row(*row_buttons)
            
            # Кнопка для ввода произвольного значения
            keyboard.row(types.InlineKeyboardButton("✏️ Ввести вручную", callback_data=f"manual_stock_{product_id}"))
            keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"item_detail_{product_id}"))
            
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре: {e}")
            text = f"❌ Ошибка при получении информации о товаре: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def update_product_stock(self, chat_id: int, product_id: str, new_stock: int):
        """Обновить остаток товара"""
        self.bot.send_message(chat_id, f"⏳ Обновляю остаток товара {product_id} до {new_stock}...")
        
        # Получаем информацию о товаре
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "product_id": [int(product_id)]
        }
        
        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if not result.get("items"):
                text = f"❌ Товар {product_id} не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            product = result["items"][0]
            offer_id = product.get('offer_id', '')
            
            if not offer_id:
                text = f"❌ Не найден Offer ID для товара {product_id}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Обновляем остаток через API
            # Используем стандартный warehouse_id для FBS (обычно это 1020003080073000)
            warehouse_id = 1020003080073000
            
            update_result = self.ozon_api.update_product_stocks(offer_id, warehouse_id, new_stock)
            
            if "error" in update_result:
                text = f"❌ Ошибка при обновлении остатка: {update_result['error']}"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard)
                return
            
            # Проверяем результат обновления
            result_items = update_result.get("result", [])
            if result_items and len(result_items) > 0:
                item = result_items[0]
                if item.get("updated", False):
                    text = f"✅ <b>Остаток успешно обновлен!</b>\n\n"
                    text += f"📦 Товар: {product_id}\n"
                    text += f"📋 Offer ID: {offer_id}\n"
                    text += f"📦 Новый остаток: {new_stock}\n"
                    text += f"🏪 Склад: FBS\n"
                else:
                    text = f"❌ Не удалось обновить остаток товара"
            else:
                text = f"❌ Неожиданный ответ от API"
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 К товару", callback_data=f"item_detail_{product_id}"))
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении остатка: {e}")
            text = f"❌ Ошибка при обновлении остатка: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def show_product_from_order(self, chat_id: int, sku: str, posting_number: str):
        """Показать детали товара из заказа"""
        self.bot.send_message(chat_id, f"⏳ Загружаю детали товара {sku}...")
        
        # Получаем информацию о товаре по SKU
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "sku": [sku]
        }
        
        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if not result.get("items"):
                text = f"📦 <b>Товар {sku}</b>\n\n❌ Товар не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"products_{posting_number}"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return
            
            product = result["items"][0]
            product_name = product.get('name', 'N/A')
            product_id = product.get('product_id', 'N/A')
            offer_id = product.get('offer_id', 'N/A')
            
            text = f"📦 <b>Товар из заказа {posting_number}</b>\n\n"
            text += f"🏷️ <b>SKU:</b> {sku}\n"
            text += f"📦 <b>Название:</b> {product_name}\n"
            text += f"🆔 <b>Product ID:</b> {product_id}\n"
            text += f"📋 <b>Offer ID:</b> {offer_id}\n"
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("📊 Штрихкод", callback_data=f"barcode_{sku}"))
            keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"products_{posting_number}"))
            
            self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка при получении товара: {e}")
            text = f"❌ Ошибка при получении товара: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"products_{posting_number}"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def generate_barcode_image_for_combined(self, barcode: str, product_name: str, sku: str):
        """Генерировать ОГРОМНЫЙ штрихкод для комбинированного изображения с увеличенным текстом"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from barcode import Code128
            from barcode.writer import ImageWriter
            from io import BytesIO
            
            # Создаем штрихкод Code128 с автоподгонкой под ширину 1202 пикселя
            code = Code128(barcode, writer=ImageWriter())
            
            # СТРОГО ОГРАНИЧИВАЕМ ШИРИНУ ДО 1202 ПИКСЕЛЕЙ!
            MAX_WIDTH = 1202
            
            # Настройки для качественного штрихкода с хорошей контрастностью
            options = {
                'module_width': 1.0,  # Увеличенный размер модуля для лучшей читаемости
                'module_height': 50.0,  # Увеличенная высота штрихкода
                'quiet_zone': 4.0,  # Нормальные тихие зоны для контрастности
                'font_size': 0,  # Убираем встроенный текст, будем добавлять свой
                'text_distance': 0,  # Убираем расстояние до текста
                'background': 'white',
                'foreground': 'black',
                'write_text': False,  # Не показываем встроенный текст
            }
            
            # Генерируем изображение штрихкода с настройками
            barcode_img = code.render(writer_options=options)
            
            # Получаем размеры штрихкода
            width, height = barcode_img.size
            
            # Если штрихкод все еще слишком широкий, масштабируем его с сохранением качества
            if width > MAX_WIDTH:
                scale_factor = MAX_WIDTH / width
                new_width = MAX_WIDTH
                new_height = int(height * scale_factor)
                # Используем высококачественное масштабирование для сохранения контрастности
                barcode_img = barcode_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = new_width, new_height
            
            # Создаем изображение для комбинированного файла - используем максимальную ширину
            text_height = 300  # Уменьшенная высота для текста
            padding_horizontal = 0  # НЕ увеличиваем ширину - используем оригинальную
            padding_vertical = 5  # МИНИМАЛЬНЫЕ отступы сверху и снизу
            img_width = MAX_WIDTH  # Используем максимальную ширину для лучшего качества
            img_height = height + text_height + padding_vertical * 2
            
            # Создаем изображение с высоким разрешением
            img = Image.new('RGB', (img_width, img_height), 'white')
            
            # Вставляем штрихкод по центру изображения для равномерного распределения
            barcode_x = (img_width - width) // 2  # Центрируем штрихкод
            img.paste(barcode_img, (barcode_x, padding_vertical))
    
            # Добавляем текст с улучшенным форматированием
            draw = ImageDraw.Draw(img)
            
            def draw_text_with_smart_fit(draw, text, x, y, max_width, max_height, font_family="arial", color='black'):
                """ИСПРАВЛЕННАЯ функция - БОЛЬШОЙ текст и БЕЗ отступов с контролем переполнения"""
                
                # Пробуем БОЛЬШИЕ размеры шрифта
                font_sizes = [35, 30, 25, 20, 18, 16, 14, 12, 10]
                
                for font_size in font_sizes:
                    try:
                        # Создаем шрифт
                        font = ImageFont.truetype(font_family, font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                    
                    # Разбиваем текст на строки с контролем переполнения
                    words = text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        test_width = draw.textlength(test_line, font=font)
                        
                        # СТРОГО контролируем ширину - не даем тексту выходить за границы!
                        if test_width <= max_width - 20:  # Оставляем запас 20 пикселей для безопасности
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                                current_line = word
                            else:
                                # Если даже одно слово не помещается, обрезаем его
                                if draw.textlength(word, font=font) > max_width - 20:
                                    # Обрезаем слово до максимальной ширины
                                    truncated_word = word
                                    while draw.textlength(truncated_word + "...", font=font) > max_width - 20 and len(truncated_word) > 3:
                                        truncated_word = truncated_word[:-1]
                                    lines.append(truncated_word + "...")
                                    current_line = ""
                                else:
                                    current_line = word
                    
                    if current_line:
                        lines.append(current_line)
                    
                    # Проверяем, помещается ли текст по высоте
                    line_height = font_size  # БЕЗ отступов между строками!
                    total_height = len(lines) * line_height
                    
                    # Если помещается - рисуем СРАЗУ
                    if total_height <= max_height and len(lines) <= 3:  # До 3 строк
                        for i, line in enumerate(lines):
                            line_width = draw.textlength(line, font=font)
                            # Центрируем БЕЗ отступов
                            line_x = x + (max_width - line_width) // 2
                            line_y = y + i * font_size  # БЕЗ отступов!
                            draw.text((line_x, line_y), line, fill=color, font=font)
                        return True
                
                # Если ничего не подошло - рисуем БОЛЬШИМ шрифтом
                try:
                    font = ImageFont.truetype(font_family, 16)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                    except:
                        font = ImageFont.load_default()
                
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                # Рисуем с БОЛЬШИМ шрифтом БЕЗ отступов
                for i, line in enumerate(lines[:2]):  # Максимум 2 строки
                    line_width = draw.textlength(line, font=font)
                    line_x = x + (max_width - line_width) // 2
                    line_y = y + i * 16  # БЕЗ отступов!
                    draw.text((line_x, line_y), line, fill=color, font=font)
                
                return True
            
            def wrap_text_to_fit(text, font, max_width, padding=5):
                """Разбивает текст на строки, чтобы он поместился в заданную ширину"""
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    if test_width <= max_width - padding:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                return lines
            
            # Подготавливаем тексты без эмодзи
            barcode_text = f"Штрихкод: {barcode}"
            sku_text = f"SKU: {sku}"
            product_text = product_name
            
            # Рисуем текст с БОЛЬШИМ размером и БЕЗ отступов
            text_start_y = height + padding_vertical + 5  # МИНИМАЛЬНЫЕ отступы
            text_height = 250  # Меньше места, но БОЛЬШЕ текст
            
            # Рисуем штрихкод с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, barcode_text, 
                0, text_start_y, 
                width, text_height // 3,
                font_family="arial"
            )
            
            # Рисуем SKU с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, sku_text, 
                0, text_start_y + text_height // 3, 
                width, text_height // 3,
                font_family="arial"
            )
            
            # Рисуем название товара с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, product_text, 
                0, text_start_y + 2 * text_height // 3, 
                width, text_height // 3,
                font_family="arial"
            )
            
            # Рамку убрали для более компактного вида
            
            # Конвертируем в bytes с максимальным качеством для термопринтера
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG', quality=100, optimize=False)  # Максимальное качество без оптимизации
            img_bytes.seek(0)
            
            return img_bytes
            
        except ImportError:
            logger.error("Библиотеки PIL и python-barcode не установлены")
            return None
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения штрихкода: {e}")
            return None

    def shorten_product_name(self, product_name: str, max_length: int = 4) -> str:
        """Сократить название товара до указанной длины"""
        if not product_name or product_name == 'N/A':
            return 'Товар'
        
        # Убираем эмодзи и специальные символы
        import re
        clean_name = re.sub(r'[^\w\s]', '', product_name)
        
        # Разбиваем на слова
        words = clean_name.split()
        
        if not words:
            return 'Товар'
        
        # Если название короткое, возвращаем как есть
        if len(clean_name) <= max_length:
            return clean_name
        
        # Берем первые слова до достижения максимальной длины
        result = ""
        for word in words:
            if len(result + word) <= max_length:
                result += word
            else:
                break
        
        # Если ничего не получилось, берем первые символы
        if not result:
            result = clean_name[:max_length]
        
        return result
    
    def shorten_product_name_for_barcode(self, product_name: str, max_length: int = 20) -> str:
        """Сократить название товара для штрихкода с сохранением цвета"""
        if not product_name or product_name == 'N/A':
            return 'Товар'
        
        # Убираем эмодзи, но сохраняем все остальное включая цвета
        import re
        clean_name = re.sub(r'[^\w\s\-]', '', product_name)
        
        # Если название короткое, возвращаем как есть
        if len(clean_name) <= max_length:
            return clean_name
        
        # Разбиваем на слова
        words = clean_name.split()
        
        if not words:
            return clean_name[:max_length]
        
        # Сначала пытаемся найти цвет в названии
        color_words = ['красный', 'синий', 'голубой', 'зеленый', 'желтый', 'оранжевый', 
                      'фиолетовый', 'розовый', 'фуксия', 'коричневый', 'черный', 'белый', 
                      'серый', 'золотой', 'серебряный', 'радужный', 'разноцветный']
        
        color_found = None
        for word in words:
            if word.lower() in color_words:
                color_found = word
                break
        
        # Если цвет найден, стараемся его сохранить
        if color_found:
            # Убираем цвет из списка слов
            words_without_color = [w for w in words if w.lower() != color_found.lower()]
            
            # Берем слова по порядку, пока не достигнем максимальной длины минус цвет
            result = ""
            color_length = len(color_found) + 1  # +1 для пробела
            
            for word in words_without_color:
                test_result = result + (" " if result else "") + word
                if len(test_result) + color_length <= max_length:
                    result = test_result
                else:
                    break
            
            # Добавляем цвет в конец
            if result:
                return f"{result} {color_found}"
            else:
                return color_found
        
        # Если цвет не найден, используем старую логику с улучшенными сокращениями
        result = ""
        for word in words:
            test_result = result + (" " if result else "") + word
            if len(test_result) <= max_length:
                result = test_result
            else:
                break
        
        # Если ничего не получилось, создаем сокращения с точками
        if not result:
            # Создаем сокращения слов с точками
            shortened_words = []
            current_length = 0
            
            for word in words:
                if len(word) > 4:  # Сокращаем только длинные слова
                    # Берем первые 3-4 символа + точка
                    short_word = word[:3] + "."
                    if current_length + len(short_word) + 1 <= max_length:
                        shortened_words.append(short_word)
                        current_length += len(short_word) + 1
                    else:
                        break
                else:
                    # Короткие слова оставляем как есть
                    if current_length + len(word) + 1 <= max_length:
                        shortened_words.append(word)
                        current_length += len(word) + 1
                    else:
                        break
            
            result = " ".join(shortened_words)
        
        # Если все еще ничего не получилось, берем первые символы
        if not result:
            result = clean_name[:max_length]
        
        return result
    
    def generate_barcode_image(self, barcode: str, product_name: str, sku: str, quantity: int = 1, posting_number: str = ""):
        """Генерировать улучшенное изображение штрихкода с высоким качеством для универсального сканирования"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from barcode import Code128
            from barcode.writer import ImageWriter
            from io import BytesIO
            
            # Создаем штрихкод Code128 с улучшенными параметрами
            code = Code128(barcode, writer=ImageWriter())
            
            # Настройки для комбинированного изображения - большой штрихкод как на этикетке
            options = {
                'module_width': 0.8,  # Значительно увеличиваем для размера как на этикетке
                'module_height': 40.0,  # Увеличиваем высоту в 2 раза
                'quiet_zone': 6.0,  # Большие тихие зоны
                'font_size': 0,  # Убираем встроенный текст, будем добавлять свой
                'text_distance': 0,  # Убираем расстояние до текста
                'background': 'white',
                'foreground': 'black',
                'write_text': False,  # Не показываем встроенный текст
            }
            
            # Генерируем изображение штрихкода с настройками
            barcode_img = code.render(writer_options=options)
            
            # Получаем размеры штрихкода
            width, height = barcode_img.size
            
            # Создаем изображение для комбинированного файла - сохраняем оригинальную ширину
            text_height = 300  # ОЧЕНЬ большая высота для текста
            padding_horizontal = 0  # НЕ увеличиваем ширину - используем оригинальную
            padding_vertical = 30  # Большие отступы сверху и снизу
            img_width = width  # Сохраняем оригинальную ширину штрихкода
            img_height = height + text_height + padding_vertical * 2
            
            # Создаем изображение с высоким разрешением
            img = Image.new('RGB', (img_width, img_height), 'white')
            
            # Вставляем штрихкод без горизонтальных отступов (используем всю ширину)
            img.paste(barcode_img, (0, padding_vertical))

            # Добавляем текст с улучшенным форматированием
            draw = ImageDraw.Draw(img)
            
            # ОЧЕНЬ маленькие шрифты для строгого соблюдения границ штрихкода
            try:
                # Используем четкие шрифты очень маленького размера
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
            except:
                try:
                    font_large = ImageFont.truetype("arial.ttf", 12)
                    font_medium = ImageFont.truetype("arial.ttf", 10)
                    font_small = ImageFont.truetype("arial.ttf", 8)
                except:
                    try:
                        font_large = ImageFont.truetype("LiberationSans-Bold.ttf", 12)
                        font_medium = ImageFont.truetype("LiberationSans-Regular.ttf", 10)
                        font_small = ImageFont.truetype("LiberationSans-Regular.ttf", 8)
                    except:
                        # Используем стандартные шрифты
                        font_large = ImageFont.load_default()
                        font_medium = ImageFont.load_default()
                        font_small = ImageFont.load_default()

            # Умная адаптация текста под размеры изображения
            def wrap_text_to_fit(text, font, max_width, padding=5):
                """Разбивает текст на строки, чтобы он поместился в заданную ширину"""
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    if test_width <= max_width - padding:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                return lines
            
            def draw_text_with_smart_fit(draw, text, x, y, max_width, max_height, font_family="arial", color='black'):
                """ИСПРАВЛЕННАЯ функция - БОЛЬШОЙ текст и БЕЗ отступов"""
                
                # Пробуем БОЛЬШИЕ размеры шрифта
                font_sizes = [40, 35, 30, 25, 20, 18, 16, 14, 12, 10]
                
                for font_size in font_sizes:
                    try:
                        # Создаем шрифт
                        font = ImageFont.truetype(font_family, font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                    
                    # Разбиваем текст на строки БЕЗ отступов
                    words = text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        test_width = draw.textlength(test_line, font=font)
                        
                        # Используем ВСЮ ширину - БЕЗ отступов!
                        if test_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                                current_line = word
                            else:
                                lines.append(word)
                    
                    if current_line:
                        lines.append(current_line)
                    
                    # Проверяем, помещается ли текст по высоте
                    line_height = font_size  # БЕЗ отступов между строками!
                    total_height = len(lines) * line_height
                    
                    # Если помещается - рисуем СРАЗУ
                    if total_height <= max_height and len(lines) <= 3:  # До 3 строк
                        for i, line in enumerate(lines):
                            line_width = draw.textlength(line, font=font)
                            # Центрируем БЕЗ отступов
                            line_x = x + (max_width - line_width) // 2
                            line_y = y + i * font_size  # БЕЗ отступов!
                            draw.text((line_x, line_y), line, fill=color, font=font)
                        return True
                
                # Если ничего не подошло - рисуем БОЛЬШИМ шрифтом
                try:
                    font = ImageFont.truetype(font_family, 18)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
                    except:
                        font = ImageFont.load_default()
                
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                # Рисуем с БОЛЬШИМ шрифтом БЕЗ отступов
                for i, line in enumerate(lines[:2]):  # Максимум 2 строки
                    line_width = draw.textlength(line, font=font)
                    line_x = x + (max_width - line_width) // 2
                    line_y = y + i * 18  # БЕЗ отступов!
                    draw.text((line_x, line_y), line, fill=color, font=font)
                
                return True
            
            # Подготавливаем тексты без эмодзи
            barcode_text = f"Штрихкод: {barcode}"
            sku_text = f"SKU: {sku}"
            
            # Используем полное название товара для штрихкода
            product_text = f"{product_name} x{quantity}"
            
            # Рисуем текст с БОЛЬШИМ размером и БЕЗ отступов
            text_start_y = height + padding_vertical + 2  # МИНИМАЛЬНЫЕ отступы
            text_height = 150  # Еще меньше места для текста
            
            # Рисуем штрихкод с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, barcode_text, 
                0, text_start_y, 
                img_width, text_height // 3,
                font_family="arial"
            )
            
            # Рисуем SKU с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, sku_text, 
                0, text_start_y + text_height // 3, 
                img_width, text_height // 3,
                font_family="arial"
            )
            
            # Рисуем название товара с БОЛЬШИМ текстом
            draw_text_with_smart_fit(
                draw, product_text, 
                0, text_start_y + 2 * text_height // 3, 
                img_width, text_height // 3,
                font_family="arial"
            )
            
            # Рамку убрали для более компактного вида
            
            # Конвертируем в bytes с максимальным качеством для термопринтера
            img_bytes = BytesIO()
            img.save(img_bytes, format='PNG', quality=100, optimize=False)  # Максимальное качество без оптимизации
            img_bytes.seek(0)
            
            return img_bytes
            
        except ImportError:
            logger.error("Библиотеки PIL и python-barcode не установлены")
            return None
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения штрихкода: {e}")
            return None
    
    def generate_smart_label(self, pdf_content: bytes, product_name: str, posting_number: str, products_info: list = None):
        """Умная генерация этикетки: конвертация PDF в PNG, поворот против часовой стрелки, добавление названия товара"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            from io import BytesIO
            
            # Открываем PDF из bytes
            pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
            
            if pdf_document.page_count == 0:
                logger.error("PDF не содержит страниц")
                return None
            
            # Получаем первую страницу
            page = pdf_document[0]
            
            # Конвертируем PDF этикетки в изображение с высоким разрешением
            mat = fitz.Matrix(4.0, 4.0)  # Умеренное увеличение разрешения
            pix = page.get_pixmap(matrix=mat)
            
            # Конвертируем в PIL Image
            img_data = pix.tobytes("png")
            pdf_img = Image.open(BytesIO(img_data))
            
            # Закрываем PDF документ
            pdf_document.close()
            
            # Поворачиваем против часовой стрелки (на 90 градусов)
            rotated_img = pdf_img.rotate(90, expand=True)
            
            # Получаем размеры повернутого изображения
            pdf_width, pdf_height = rotated_img.size
            
            # СТРОГО ОГРАНИЧИВАЕМ ШИРИНУ ДО 1202 ПИКСЕЛЕЙ!
            MAX_WIDTH = 1202
            if pdf_width > MAX_WIDTH:
                pdf_width = MAX_WIDTH
            
            # Создаем новое изображение с дополнительным местом для текста
            text_height = 200  # Уменьшенное место для текста
            total_height = pdf_height + text_height
            
            # Создаем итоговое изображение
            final_img = Image.new('RGB', (pdf_width, total_height), 'white')
            
            # Вставляем повернутое изображение PDF
            final_img.paste(rotated_img, (0, 0))
            
            # Добавляем текст с названием товара
            draw = ImageDraw.Draw(final_img)
            
            # ОЧЕНЬ маленькие шрифты для строгого соблюдения границ PDF
            try:
                # Используем четкие шрифты очень маленького размера
                font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
                font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            except:
                try:
                    # Альтернативные шрифты
                    font_large = ImageFont.truetype("arial.ttf", 16)
                    font_medium = ImageFont.truetype("arial.ttf", 14)
                    font_small = ImageFont.truetype("arial.ttf", 12)
                except:
                    try:
                        # Еще один вариант
                        font_large = ImageFont.truetype("LiberationSans-Bold.ttf", 16)
                        font_medium = ImageFont.truetype("LiberationSans-Regular.ttf", 14)
                        font_small = ImageFont.truetype("LiberationSans-Regular.ttf", 12)
                    except:
                        # Используем стандартные шрифты с большим размером
                        font_large = ImageFont.load_default()
                        font_medium = ImageFont.load_default()
                        font_small = ImageFont.load_default()
            
            def draw_text_with_smart_fit(draw, text, x, y, max_width, max_height, font_family="arial", color='black'):
                """ИСПРАВЛЕННАЯ функция - БОЛЬШОЙ текст и БЕЗ отступов с контролем переполнения"""
                
                # Пробуем БОЛЬШИЕ размеры шрифта
                font_sizes = [50, 45, 40, 35, 30, 25, 20, 18, 16, 14, 12]
                
                for font_size in font_sizes:
                    try:
                        # Создаем шрифт
                        font = ImageFont.truetype(font_family, font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                    
                    # Разбиваем текст на строки с контролем переполнения
                    words = text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        test_line = current_line + (" " if current_line else "") + word
                        test_width = draw.textlength(test_line, font=font)
                        
                        # СТРОГО контролируем ширину - не даем тексту выходить за границы!
                        if test_width <= max_width - 20:  # Оставляем запас 20 пикселей для безопасности
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                                current_line = word
                            else:
                                # Если даже одно слово не помещается, обрезаем его
                                if draw.textlength(word, font=font) > max_width - 20:
                                    # Обрезаем слово до максимальной ширины
                                    truncated_word = word
                                    while draw.textlength(truncated_word + "...", font=font) > max_width - 20 and len(truncated_word) > 3:
                                        truncated_word = truncated_word[:-1]
                                    lines.append(truncated_word + "...")
                                    current_line = ""
                                else:
                                    current_line = word
                    
                    if current_line:
                        lines.append(current_line)
                    
                    # Проверяем, помещается ли текст по высоте
                    line_height = font_size  # БЕЗ отступов между строками!
                    total_height = len(lines) * line_height
                    
                    # Если помещается - рисуем СРАЗУ
                    if total_height <= max_height and len(lines) <= 4:  # До 4 строк
                        for i, line in enumerate(lines):
                            line_width = draw.textlength(line, font=font)
                            # Центрируем БЕЗ отступов
                            line_x = x + (max_width - line_width) // 2
                            line_y = y + i * font_size  # БЕЗ отступов!
                            draw.text((line_x, line_y), line, fill=color, font=font)
                        return True
                
                # Если ничего не подошло - рисуем БОЛЬШИМ шрифтом
                try:
                    font = ImageFont.truetype(font_family, 20)
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    # СТРОГО контролируем ширину - не даем тексту выходить за границы!
                    if test_width <= max_width - 10:  # Оставляем небольшой запас
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            # Если даже одно слово не помещается, обрезаем его
                            if draw.textlength(word, font=font) > max_width - 10:
                                # Обрезаем слово до максимальной ширины
                                truncated_word = word
                                while draw.textlength(truncated_word + "...", font=font) > max_width - 10 and len(truncated_word) > 3:
                                    truncated_word = truncated_word[:-1]
                                lines.append(truncated_word + "...")
                            else:
                                lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                # Рисуем с БОЛЬШИМ шрифтом БЕЗ отступов
                for i, line in enumerate(lines[:3]):  # Максимум 3 строки
                    line_width = draw.textlength(line, font=font)
                    line_x = x + (max_width - line_width) // 2
                    line_y = y + i * 20  # БЕЗ отступов!
                    draw.text((line_x, line_y), line, fill=color, font=font)
                
                return True
            
            def wrap_text_to_fit(text, font, max_width, padding=5):
                """Разбивает текст на строки, чтобы он поместился в заданную ширину"""
                words = text.split()
                lines = []
                current_line = ""
                
                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    test_width = draw.textlength(test_line, font=font)
                    
                    if test_width <= max_width - padding:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                            current_line = word
                        else:
                            lines.append(word)
                
                if current_line:
                    lines.append(current_line)
                
                return lines
            
            # Подготавливаем текст без эмодзи
            if products_info and len(products_info) > 0:
                # Создаем информацию о товарах
                total_items = sum(p.get('quantity', 1) for p in products_info)
                
                if len(products_info) == 1:
                    # Один товар - показываем с цветом словами
                    product = products_info[0]
                    full_name = product.get('name', 'Товар')
                    color = self.extract_color_from_product({}, full_name)
                    
                    # Создаем короткое название с цветом словами
                    if color != 'N/A' and color.lower() in full_name.lower():
                        # Если цвет найден в названии, создаем короткое название
                        short_name = self.shorten_product_name_for_barcode(full_name.replace(color.lower(), ''), 25).strip()
                        if short_name:
                            display_name = f"{short_name} {color}"
                        else:
                            display_name = color
                    else:
                        display_name = self.shorten_product_name_for_barcode(full_name, 30)
                    
                    product_text = f"Заказ {total_items} товар: {display_name}"
                elif len(products_info) <= 3:
                    # Несколько товаров - показываем все с цветами словами
                    product_names = []
                    for p in products_info:
                        # Извлекаем цвет из названия товара
                        full_name = p.get('name', 'Товар')
                        color = self.extract_color_from_product({}, full_name)
                        
                        # Создаем короткое название с цветом словами
                        if color != 'N/A' and color.lower() in full_name.lower():
                            # Если цвет найден в названии, создаем короткое название
                            short_name = self.shorten_product_name_for_barcode(full_name.replace(color.lower(), ''), 6).strip()
                            if short_name:
                                display_name = f"{short_name} {color}"
                            else:
                                display_name = color
                        else:
                            display_name = self.shorten_product_name_for_barcode(full_name, 8)
                        
                        quantity = p.get('quantity', 1)
                        product_names.append(f"{display_name} x{quantity}")
                    
                    products_str = ", ".join(product_names)
                    product_text = f"Заказ {total_items} товаров: {products_str}"
                else:
                    # Много товаров - показываем первые 2 с цветами словами и общее количество
                    product_names = []
                    for p in products_info[:2]:
                        # Извлекаем цвет из названия товара
                        full_name = p.get('name', 'Товар')
                        color = self.extract_color_from_product({}, full_name)
                        
                        # Создаем короткое название с цветом словами
                        if color != 'N/A' and color.lower() in full_name.lower():
                            short_name = self.shorten_product_name_for_barcode(full_name.replace(color.lower(), ''), 6).strip()
                            if short_name:
                                display_name = f"{short_name} {color}"
                            else:
                                display_name = color
                        else:
                            display_name = self.shorten_product_name_for_barcode(full_name, 8)
                        
                        quantity = p.get('quantity', 1)
                        product_names.append(f"{display_name} x{quantity}")
                    
                    products_str = ", ".join(product_names)
                    remaining = len(products_info) - 2
                    product_text = f"Заказ {total_items} товаров: {products_str} +{remaining}"
            else:
                # Fallback к старому формату с цветом
                # Извлекаем цвет из названия товара
                color = self.extract_color_from_product({}, product_name)
                
                # Создаем короткое название с цветом словами
                if color != 'N/A' and color.lower() in product_name.lower():
                    # Если цвет найден в названии, создаем короткое название
                    short_name = self.shorten_product_name_for_barcode(product_name.replace(color.lower(), ''), 10).strip()
                    if short_name:
                        product_text = f"Заказ: {short_name} {color}"
                    else:
                        product_text = f"Заказ: {color}"
                else:
                    short_name = self.shorten_product_name_for_barcode(product_name, 15)
                    product_text = f"Заказ: {short_name}"
            
            order_text = f"Заказ: {posting_number}"
            
            # Рисуем текст с автоматической подгонкой
            text_start_y = pdf_height + 20  # Минимальные отступы
            text_height = 400  # Достаточно места для текста
            
            # Рисуем название товара с УМНОЙ автоподгонкой
            draw_text_with_smart_fit(
                draw, product_text, 
                0, text_start_y, 
                pdf_width, text_height // 2,
                font_family="arial"
            )
            
            # Рисуем номер заказа с УМНОЙ автоподгонкой
            draw_text_with_smart_fit(
                draw, order_text, 
                0, text_start_y + text_height // 2, 
                pdf_width, text_height // 2,
                font_family="arial"
            )
            
            # Конвертируем в bytes
            img_bytes = BytesIO()
            final_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Включаем умную обрезку для удаления лишнего пространства
            img_bytes = self.smart_crop_image(img_bytes)
            
            return img_bytes
            
        except ImportError:
            logger.error("Библиотеки PIL или PyMuPDF не установлены")
            return None
        except Exception as e:
            logger.error(f"Ошибка при генерации умной этикетки: {e}")
            return None

    def smart_crop_image(self, img_bytes):
        """Умная обрезка изображения - убираем пустое пространство справа и слева"""
        try:
            from PIL import Image
            from io import BytesIO
            
            # Открываем изображение
            img_bytes.seek(0)
            img = Image.open(img_bytes)
            
            # Получаем размеры
            width, height = img.size
            
            # Находим левую границу содержимого
            left_boundary = 0
            for x in range(width):
                has_content = False
                for y in range(0, height, max(1, height // 20)):
                    pixel = img.getpixel((x, y))
                    if isinstance(pixel, tuple) and len(pixel) >= 3:
                        r, g, b = pixel[:3]
                        if r < 250 or g < 250 or b < 250:
                            has_content = True
                            break
                    elif isinstance(pixel, int) and pixel < 250:
                        has_content = True
                        break
                
                if has_content:
                    left_boundary = max(0, x - 10)  # Добавляем небольшой отступ
                    break
            
            # Находим правую границу содержимого
            right_boundary = width
            for x in range(width - 1, -1, -1):
                has_content = False
                for y in range(0, height, max(1, height // 20)):
                    pixel = img.getpixel((x, y))
                    if isinstance(pixel, tuple) and len(pixel) >= 3:
                        r, g, b = pixel[:3]
                        if r < 250 or g < 250 or b < 250:
                            has_content = True
                            break
                    elif isinstance(pixel, int) and pixel < 250:
                        has_content = True
                        break
                
                if has_content:
                    right_boundary = min(width, x + 10)  # Добавляем небольшой отступ
                    break
            
            # Обрезаем изображение только если есть что обрезать
            if left_boundary > 0 or right_boundary < width - 10:
                cropped_img = img.crop((left_boundary, 0, right_boundary, height))
                
                # Сохраняем обрезанное изображение
                new_img_bytes = BytesIO()
                cropped_img.save(new_img_bytes, format='PNG', quality=100, optimize=False)
                new_img_bytes.seek(0)
                return new_img_bytes
            else:
                # Если нечего обрезать, возвращаем оригинал
                img_bytes.seek(0)
                return img_bytes
            
        except Exception as e:
            logger.error(f"Ошибка при умной обрезке изображения: {e}")
            # В случае ошибки возвращаем оригинал
            img_bytes.seek(0)
            return img_bytes
    
    def get_real_product_barcode(self, chat_id: int, sku: str):
        """Получить настоящий штрихкод товара через API"""
        self.bot.send_message(chat_id, f"⏳ Получаю штрихкод для товара {sku}...")

        # Сначала получаем информацию о товаре по SKU
        url = f"{self.ozon_api.base_url}/v3/product/info/list"
        payload = {
            "sku": [sku]
        }

        try:
            response = requests.post(url, headers=self.ozon_api.headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if not result.get("items"):
                text = f"📊 <b>Штрихкод товара {sku}</b>\n\n❌ Товар не найден"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return

            product = result["items"][0]
            product_id = product.get('id', '')
            product_name = product.get('name', 'N/A')
            barcodes = product.get('barcodes', [])

            if not barcodes:
                text = f"📊 <b>Штрихкод товара {sku}</b>\n\n❌ Штрихкоды не найдены"
                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
                self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
                return

            # Генерируем изображения для каждого штрихкода
            for i, barcode in enumerate(barcodes, 1):
                barcode_img = self.generate_barcode_image(barcode, product_name, sku, 1, "")
                
                if barcode_img:
                    # Отправляем изображение штрихкода
                    barcode_img.name = f"barcode_{sku}_{i}.png"
                    
                    caption = f"📊 Штрихкод {i} для товара {sku}\n📦 {product_name}\n🏷️ {barcode}"
                    self.bot.send_document(
                        chat_id=chat_id,
                        document=barcode_img,
                        caption=caption
                    )
                else:
                    # Если не удалось сгенерировать изображение, отправляем текстом
                    text = f"📊 <b>Штрихкод {i} товара {sku}</b>\n\n"
                    text += f"📦 <b>Название:</b> {product_name}\n"
                    text += f"🆔 <b>Product ID:</b> {product_id}\n"
                    text += f"📊 <b>Штрихкод:</b> {barcode}\n"
                    
                    self.bot.send_message(chat_id, text, parse_mode="HTML")

            # Возвращаемся в меню
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, "✅ Штрихкоды отправлены!", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Ошибка при получении штрихкода: {e}")
            text = f"❌ Ошибка при получении штрихкода: {e}"
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
            self.bot.send_message(chat_id, text, reply_markup=keyboard)
    
    def show_notifications_menu(self, chat_id: int):
        """Показать меню уведомлений"""
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("▶️ Запустить мониторинг", callback_data="start_monitoring"))
        keyboard.row(types.InlineKeyboardButton("⏹️ Остановить мониторинг", callback_data="stop_monitoring"))
        keyboard.row(types.InlineKeyboardButton("📊 Статус мониторинга", callback_data="monitoring_status"))
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        text = (
            "🔔 <b>Управление уведомлениями</b>\n\n"
            "Здесь вы можете управлять мониторингом новых заказов на сборку:\n\n"
            "• <b>Запустить мониторинг</b> - начать отслеживание новых заказов\n"
            "• <b>Остановить мониторинг</b> - прекратить отслеживание\n"
            "• <b>Статус мониторинга</b> - проверить состояние системы"
        )
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def show_stats(self, chat_id: int):
        """Показать статистику"""
        # Получаем статистику по заказам
        packaging_result = self.ozon_api.get_orders_for_packaging(limit=1000)
        delivery_result = self.ozon_api.get_orders_awaiting_deliver(limit=1000)
        
        packaging_count = 0
        delivery_count = 0
        
        if not packaging_result.get("error"):
            packaging_count = len(packaging_result.get("result", {}).get("postings", []))
        
        if not delivery_result.get("error"):
            delivery_count = len(delivery_result.get("result", {}).get("postings", []))
        
        text = f"📊 <b>Статистика заказов</b>\n\n"
        text += f"📦 Заказов на сборку: <b>{packaging_count}</b>\n"
        text += f"🚚 Готовых к отгрузке: <b>{delivery_count}</b>\n"
        text += f"🔔 Обработано уведомлений: <b>{self.order_monitor.get_processed_orders_count()}</b>\n\n"
        text += f"📅 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🔙 Главное меню", callback_data="main_menu"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def start_monitoring(self, chat_id: int):
        """Запустить мониторинг"""
        if self.order_monitor.is_running:
            self.bot.send_message(chat_id, "✅ Мониторинг уже запущен")
            return
        
        self.order_monitor.start_monitoring()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data="notifications"))
        
        self.bot.send_message(
            chat_id,
            "✅ Мониторинг запущен!\n\n"
            "Теперь вы будете получать уведомления о новых заказах на сборку каждые 5 минут.",
            reply_markup=keyboard
        )
    
    def stop_monitoring(self, chat_id: int):
        """Остановить мониторинг"""
        if not self.order_monitor.is_running:
            self.bot.send_message(chat_id, "❌ Мониторинг не запущен")
            return
        
        self.order_monitor.stop_monitoring()
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data="notifications"))
        
        self.bot.send_message(chat_id, "⏹️ Мониторинг остановлен", reply_markup=keyboard)
    
    def show_monitoring_status(self, chat_id: int):
        """Показать статус мониторинга"""
        status = "🟢 Активен" if self.order_monitor.is_running else "🔴 Остановлен"
        processed_count = self.order_monitor.get_processed_orders_count()
        
        text = (
            f"📊 <b>Статус мониторинга</b>\n\n"
            f"Состояние: {status}\n"
            f"Обработано заказов: {processed_count}\n"
            f"Интервал проверки: 5 минут\n"
            f"Последняя проверка: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.row(types.InlineKeyboardButton("🔙 Назад", callback_data="notifications"))
        
        self.bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
    
    def run(self):
        """Запуск бота"""
        # Проверяем конфигурацию
        if not Config.validate():
            logger.error("Конфигурация неверна, завершение работы")
            return
        
        Config.print_config()
        
        logger.info("Запуск Ozon Seller Bot на telebot...")
        
        # Запускаем мониторинг автоматически
        self.order_monitor.start_monitoring()
        
        # Запускаем бота
        self.bot.polling(none_stop=True)

def main():
    """Главная функция"""
    bot = OzonBot()
    bot.run()

if __name__ == "__main__":
    main()