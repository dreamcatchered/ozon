# OzonSellerBot

Telegram bot for Ozon seller order monitoring.

Get notified about new orders on your Ozon seller account directly in Telegram. Track statuses and view details without opening Seller Cabinet.

## Features

- New order notifications in Telegram
- Order status tracking
- Configurable check interval
- Ozon Seller API integration

## Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=flat&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)

## Setup

```bash
pip install -r requirements.txt
```

Set environment variables:
```env
BOT_TOKEN=your_bot_token
OZON_API_KEY=your_ozon_api_key
OZON_CLIENT_ID=your_ozon_client_id
ADMIN_CHAT_ID=your_telegram_id
```

Get credentials in [Ozon Seller Cabinet](https://seller.ozon.ru) → Settings → API keys.

```bash
python run_bot.py
```

## Contact

Telegram: [@dreamcatch_r](https://t.me/dreamcatch_r)
