"""
Ethereum (ETH/USD) Price Tracker
----------------------------------
Fetches the current ETH price in USD from CoinGecko's public API,
compares it to the last known price, and sends a Telegram alert
if the price moved more than PRICE_CHANGE_THRESHOLD percent since
the last check, OR more than DAILY_CHANGE_THRESHOLD since the start
of the day (Tehran time).

Also sends one daily summary message per day, any time at or after
DAILY_SUMMARY_HOUR (Tehran time) -- whichever run happens to be the
first one that day at or past that hour. This way, if GitHub Actions
skips the exact scheduled run at that hour (which it sometimes does),
the next run later that day still catches it, instead of losing the
whole day's summary.

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

# Alert if price changes by more than this percentage since the last check
PRICE_CHANGE_THRESHOLD = 1.0  # percent

# Alert if price changes by more than this percentage since today's reference price
DAILY_CHANGE_THRESHOLD = 1.0  # percent

# Hour (24h, Tehran time) at or after which a daily summary is sent (once per day)
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


def get_tehran_now():
    """
    Return the current time in Tehran, falling back to naive UTC
    if the timezone database isn't available for any reason.
    This must never crash the script.
    """

    try:
        return datetime.now(ZoneInfo("Asia/Tehran"))
    except Exception as e:
        print(f"Warning: could not load Asia/Tehran timezone ({e}). Falling back to UTC.")
        return datetime.utcnow()


def load_state():
    """
    Read the previously saved state:
    {
      "price": <last checked price>,
      "day_reference_price": <price at the start of today>,
      "day_reference_date": "YYYY-MM-DD" (Tehran date),
      "last_summary_date": "YYYY-MM-DD" (last date a daily summary was sent)
    }
    Returns a dict with defaults if the file doesn't exist yet.
    """

    if not os.path.exists(PRICE_FILE):
        return {
            "price": None,
            "day_reference_price": None,
            "day_reference_date": None,
            "last_summary_date": None,
        }

    with open(PRICE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {
            "price": data.get("price"),
            "day_reference_price": data.get("day_reference_price"),
            "day_reference_date": data.get("day_reference_date"),
            "last_summary_date": data.get("last_summary_date"),
        }


def save_state(state):
    """Save the current state for the next run. Always called, no matter what else happens."""

    with open(PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
    """Send a Markdown-formatted message via the Telegram bot. Never raises on failure."""

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials are missing. Skipping notification.")
        return

    try:
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
    except Exception as e:
        print(f"Warning: failed to send Telegram message: {e}")


def percent_change(old_price, new_price):
    """Calculate percentage change between two prices."""

    if not old_price:
        return 0

    return ((new_price - old_price) / old_price) * 100


def format_change(change):
    """Format a percentage change with an explicit + sign for positive values."""

    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}%"


# ==============================
# MAIN
# ==============================

def main():

    state = load_state()
    tehran_now = get_tehran_now()
    today_str = tehran_now.strftime("%Y-%m-%d")

    try:
        current_price = get_current_price()
    except Exception as e:
        print(f"Failed to fetch price: {e}")
        sys.exit(1)

    print(f"Current ETH price: ${current_price:,}")
# ==============================
# TELEGRAM TEST MESSAGE
# Remove this block after confirming Telegram works.
# ==============================

send_telegram_message(
    f"✅ *Test Message*\n\n"
    f"ربات با موفقیت اجرا شد.\n"
    f"💰 Current ETH Price: *${current_price:,}*"
)

print("Test Telegram message sent.")

last_price = state["price"]

    # Reset the daily reference price if it's a new day (Tehran time)
    if state["day_reference_date"] != today_str:
        print("New day detected. Resetting daily reference price.")
        state["day_reference_price"] = current_price
        state["day_reference_date"] = today_str

    day_reference_price = state["day_reference_price"]

    alert_sent = False

    if last_price is not None:

        hourly_change = percent_change(last_price, current_price)
        daily_change = percent_change(day_reference_price, current_price)

        print(f"Last price: ${last_price:,} | Hourly change: {hourly_change:.2f}%")
        print(f"Today's reference: ${day_reference_price:,} | Daily change: {daily_change:.2f}%")

        triggered_change = None
        change_label = None

        if abs(hourly_change) >= PRICE_CHANGE_THRESHOLD:
            triggered_change = hourly_change
            change_label = "نسبت به چک قبلی"
        elif abs(daily_change) >= DAILY_CHANGE_THRESHOLD:
            triggered_change = daily_change
            change_label = "نسبت به ابتدای امروز"

        if triggered_change is not None:

            header = "📈 *افزایش قیمت اتریوم*" if triggered_change > 0 else "📉 *کاهش قیمت اتریوم*"

            message = (
                f"{header}\n\n"
                f"💰 قیمت قبلی: `${last_price:,}`\n"
                f"🔔 قیمت فعلی: *${current_price:,}*\n"
                f"📊 تغییر ({change_label}): *{format_change(triggered_change)}*"
            )

            send_telegram_message(message)
            alert_sent = True
            print("Threshold alert sent.")

        # Daily summary: sent once per day, any run at or after DAILY_SUMMARY_HOUR.
        # Using "last_summary_date" (not an exact hour match) means a skipped
        # scheduled run doesn't cost you the whole day's summary -- the next
        # run that day, whenever it happens, will still catch it.
        already_sent_today = state["last_summary_date"] == today_str
        past_summary_hour = tehran_now.hour >= DAILY_SUMMARY_HOUR

        if not already_sent_today and past_summary_hour:

            trend_emoji = "📈" if daily_change > 0 else "📉" if daily_change < 0 else "➖"

            message = (
                f"📋 *خلاصه‌ی روزانه*\n\n"
                f"💎 قیمت فعلی اتریوم: *${current_price:,}*\n"
                f"{trend_emoji} تغییر نسبت به ابتدای امروز: *{format_change(daily_change)}*\n\n"
                f"✅ ربات فعاله و در حال رصده"
            )

            send_telegram_message(message)
            state["last_summary_date"] = today_str
            print("Daily summary sent.")

        elif not alert_sent:
            print("No threshold crossed and not summary time yet. No alert sent.")

    else:
        print("No previous price found. Saving current price as baseline.")

    # Always save the latest state, no matter what happened above.
    state["price"] = current_price
    save_state(state)


if __name__ == "__main__":
    main()
