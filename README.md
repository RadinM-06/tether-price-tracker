[README-2.md](https://github.com/user-attachments/files/30656064/README-2.md)
# ETH Price Tracker 🔔

A small automated bot that tracks the Ethereum (ETH/USD) price and sends a Telegram alert when the price moves significantly — either compared to the last check, or compared to the start of the day. It also sends a daily summary so you know it's alive even on quiet days. No server required, runs entirely on GitHub Actions.

## How it works

1. A scheduled GitHub Actions workflow runs the script every hour.
2. The script fetches the current ETH/USD price from the [CoinGecko](https://www.coingecko.com/en/api) public API.
3. It compares the price to:
   - the last recorded check (hourly change), and
   - the first recorded price of the current day, Tehran time (daily change)
4. If either change exceeds its threshold, it sends a Telegram alert.
5. Once a day, at a configured hour (Tehran time), it sends a summary message regardless of the thresholds, so you always know the bot is running.
6. The new price/state is committed back to the repository for the next run.

## Built With

- Python 3
- [Requests](https://docs.python-requests.org/)
- [CoinGecko API](https://www.coingecko.com/en/api) — price data
- [Telegram Bot API](https://core.telegram.org/bots/api) — notifications
- GitHub Actions — scheduling & automation

## Project Structure

```
tether-price-tracker/
├── track_price.py              # main script
├── requirements.txt            # dependencies
├── last_price.json             # stores the last price + daily reference price
└── .github/workflows/
    └── check_price.yml         # scheduled workflow (runs hourly)
```

## Setup

1. Fork or clone this repository.
2. Create a Telegram bot via [@BotFather](https://t.me/BotFather) and get your bot token.
3. Get your Telegram chat ID (message your bot, then check `https://api.telegram.org/bot<TOKEN>/getUpdates`).
4. In your repo, go to **Settings → Secrets and variables → Actions** and add:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Run the workflow manually once (**Actions → Check Tether Price → Run workflow**) to set the baseline price.

After that, it runs automatically every hour.

## Configuration

All of these can be adjusted at the top of `track_price.py`:

```python
PRICE_CHANGE_THRESHOLD = 1.0   # alert if price changes this much vs. the last check (%)
DAILY_CHANGE_THRESHOLD = 1.0   # alert if price changes this much vs. today's reference price (%)
DAILY_SUMMARY_HOUR = 22        # hour (Tehran time) to always send a daily summary
```

The cron schedule (`.github/workflows/check_price.yml`) is offset a few minutes past the hour rather than exactly on it, since GitHub Actions scheduled runs are best-effort and tend to be more reliable off the top of the hour.

## Notes

This project originally targeted a different price source, but pivoted to CoinGecko after discovering the original source was inaccessible from GitHub-hosted runners. This turned out to be a good example of adapting a project around a real infrastructure constraint rather than working around it.
