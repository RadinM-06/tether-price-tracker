
"""
Ethereum (ETH/USD) Price Tracker
----------------------------------
Fetches the current ETH price in USD from CoinGecko's public API,
compares it to the last known price, and sends a Telegram alert
if the price moved more than PRICE_CHANGE_THRESHOLD percent.

Also sends a daily summary message once a day at DAILY_SUMMARY_HOUR
(Tehran time), regardless of whether the price crossed the threshold,
so you know the bot is alive even on quiet days.

Runs on a schedule via GitHub Actions (see .github/workflows/check_price.yml).
"""

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

# ==============================
# CONFIG
# ==============================

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
PRICE_FILE = "last_price.json"

# Alert if price changes by more than this percentage since last check
PRICE_CHANGE_THRESHOLD = 1.0  # percent

# Hour (24h, Tehran time) at which a daily summary is always sent
DAILY_SUMMARY_HOUR = 22

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ==============================
# FUNCTIONS
# ==============================

def get_current_price():
    """Fetch the current ETH/USD price from CoinGecko."""

    response = requests.get(
        COINGECKO_URL,
        params={"ids": "ethereum", "vs_currencies": "usd"},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    price_usd = float(data["ethereum"]["usd"])

    return round(price_usd, 2)


def load_last_price():
    """Read the previously saved price, if any."""

    if not os.path.exists(PRICE_FILE):
        return None

    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("price")


def save_price(price):
    """Save the current price for the next run."""

    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump({"price": price}, f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
    """Send a Markdown-formatted message via the Telegram bot."""

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
        },
        timeout=10,
    )
    response.raise_for_status()


def percent_change(old_price, new_price):
    """Calculate percentage change between two prices."""

    if old_price == 0:
        return 0

    return ((new_price - old_price) / old_price) * 100


def format_change(change):
    """Format a percentage change with an explicit + sign for positive values."""

    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}%"


def is_daily_summary_time():
    """Check whether it's currently the configured daily summary hour (Tehran time)."""

    tehran_now = datetime.now(ZoneInfo("Asia/Tehran"))
    return tehran_now.hour == DAILY_SUMMARY_HOUR


# ==============================
# MAIN
# ==============================

def main():

    try:
        current_price = get_current_price()
    except Exception as e:
        print(f"Failed to fetch price: {e}")
        sys.exit(1)

    print(f"Current ETH price: ${current_price:,}")

    last_price = load_last_price()

    if last_price is None:
        print("No previous price found. Saving current price as baseline.")
        save_price(current_price)
        return

    change = percent_change(last_price, current_price)

    print(f"Last price: ${last_price:,} | Change: {change:.2f}%")

    alert_sent = False

    if abs(change) >= PRICE_CHANGE_THRESHOLD:

        if change > 0:
            header = "📈 *افزایش قیمت اتریوم*"
        else:
            header = "📉 *کاهش قیمت اتریوم*"

        message = (
            f"{header}\n\n"
            f"💰 قیمت قبلی: `${last_price:,}`\n"
            f"🔔 قیمت فعلی: *${current_price:,}*\n"
            f"📊 تغییر: *{format_change(change)}*"
        )

        send_telegram_message(message)
        alert_sent = True
        print("Threshold alert sent.")

    # Daily summary: sent once a day regardless of the threshold,
    # so you know the bot is alive even without a big price move.
    if not alert_sent and is_daily_summary_time():

        trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"

        message = (
            f"📋 *خلاصه‌ی روزانه*\n\n"
            f"💎 قیمت فعلی اتریوم: *${current_price:,}*\n"
            f"{trend_emoji} تغییر نسبت به چک قبلی: *{format_change(change)}*\n\n"
            f"✅ ربات فعاله و در حال رصده"
        )

        send_telegram_message(message)
        print("Daily summary sent.")

    if not alert_sent and not is_daily_summary_time():
        print("Change below threshold. No alert sent.")

    save_price(current_price)


if __name__ == "__main__":
    main()
