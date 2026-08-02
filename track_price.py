"""
Tether (USDT/IRT) Price Tracker
--------------------------------
Fetches the current USDT price in Toman from Nobitex's public API,
compares it to the last known price, and sends a Telegram alert
if the price moved more than PRICE_CHANGE_THRESHOLD percent.

Runs on a schedule via GitHub Actions (see .github/workflows/check_price.yml).
"""

import json
import os
import sys
import requests

# ==============================
# CONFIG
# ==============================

NOBITEX_URL = "https://api.nobitex.ir/market/stats"
PRICE_FILE = "last_price.json"

# Alert if price changes by more than this percentage since last check
PRICE_CHANGE_THRESHOLD = 1.0  # percent

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ==============================
# FUNCTIONS
# ==============================

def get_current_price():
    """Fetch the current USDT/IRT price from Nobitex."""

    response = requests.post(
        NOBITEX_URL,
        data={"srcCurrency": "usdt", "dstCurrency": "rls"},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    stats = data["stats"]["usdt-rls"]

    # Nobitex returns Rial, convert to Toman (divide by 10)
    price_toman = float(stats["latest"]) / 10

    return round(price_toman)


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
    """Send a message via the Telegram bot."""

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are missing. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )
    response.raise_for_status()


def percent_change(old_price, new_price):
    """Calculate percentage change between two prices."""

    if old_price == 0:
        return 0

    return ((new_price - old_price) / old_price) * 100


# ==============================
# MAIN
# ==============================

def main():

    try:
        current_price = get_current_price()
    except Exception as e:
        print(f"Failed to fetch price: {e}")
        sys.exit(1)

    print(f"Current USDT price: {current_price:,} Toman")

    last_price = load_last_price()

    if last_price is None:
        print("No previous price found. Saving current price as baseline.")
        save_price(current_price)
        return

    change = percent_change(last_price, current_price)

    print(f"Last price: {last_price:,} Toman | Change: {change:.2f}%")

    if abs(change) >= PRICE_CHANGE_THRESHOLD:

        direction = "📈 افزایش" if change > 0 else "📉 کاهش"

        message = (
            f"{direction} قیمت تتر\n\n"
            f"قیمت قبلی: {last_price:,} تومان\n"
            f"قیمت فعلی: {current_price:,} تومان\n"
            f"تغییر: {change:.2f}%"
        )

        send_telegram_message(message)
        print("Alert sent.")

    else:
        print("Change below threshold. No alert sent.")

    save_price(current_price)


if __name__ == "__main__":
    main()
