[README.md](https://github.com/user-attachments/files/30640214/README.md)
# tether-price-tracker# ETH Price Tracker 🔔

A small automated bot that tracks the Ethereum (ETH/USD) price and sends a Telegram alert whenever the price moves more than 1% since the last check — no server required, runs entirely on GitHub Actions.

## How it works

1. A scheduled GitHub Actions workflow runs the script every hour.
2. The script fetches the current ETH/USD price from the [CoinGecko](https://www.coingecko.com/en/api) public API.
3. It compares the price to the last recorded value (stored in `last_price.json`).
4. If the change exceeds the configured threshold, it sends a Telegram message via the Bot API.
5. The new price is committed back to the repository for the next run.

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
├── last_price.json             # stores the last known price
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

The alert threshold can be adjusted in `track_price.py`:

```python
PRICE_CHANGE_THRESHOLD = 1.0  # percent
```

## Notes

This project originally targeted a different price source, but pivoted to CoinGecko after discovering the original source was inaccessible from GitHub-hosted runners. This turned out to be a good example of adapting a project around a real infrastructure constraint rather than working around it.
