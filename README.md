# AlphaMedia News Bot

Telegram-controlled AI news bot for tracking real news, filtering noise, summarizing it with Claude or DeepSeek, and drafting an article or X thread.

Example workflow:

1. Send `/watch Prediction Markets` to the Telegram bot.
2. The bot periodically checks configured sources such as X recent search, Bloomberg RSS-style feeds, Yahoo Finance ticker feeds, and any extra RSS feeds you add.
3. It filters weak matches, deduplicates known items, and asks the configured LLM to summarize the strongest signals.
4. Send `/article Prediction Markets` or press a saved-goal button to draft a longer post plus an X-ready thread.

## What is included

- Telegram commands and inline buttons.
- Source adapters for X recent search and RSS feeds.
- Yahoo Finance ticker feed support.
- Bloomberg feed support through RSS/feed URLs you configure. For full Bloomberg News or Terminal-quality feeds, use a licensed Bloomberg API/feed and add it as an RSS adapter or a new provider.
- Claude and DeepSeek clients behind the same interface.
- SQLite storage for saved goals and dedupe.
- A `stub` LLM mode so the bot can be tested before API keys are added.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Create a Telegram bot with BotFather, then set:

```bash
TELEGRAM_BOT_TOKEN=...
```

Choose an LLM provider:

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
LLM_MODEL=claude-sonnet-4-5
```

or:

```bash
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
LLM_MODEL=deepseek-chat
```

Optional X support:

```bash
X_BEARER_TOKEN=...
```

Run the bot:

```bash
alphamedia-newsbot
```

## Telegram commands

- `/start` shows the main controls.
- `/search <topic>` runs an immediate news search and summary.
- `/article <topic>` runs a search and drafts a longer article plus an X thread.
- `/watch <topic>` saves a recurring topic.
- `/goals` lists saved topics with buttons.
- `/unwatch <topic>` removes a saved topic.

## Source configuration

`RSS_FEEDS` accepts comma-separated feed specs:

```bash
RSS_FEEDS=Bloomberg Markets|https://feeds.bloomberg.com/markets/news.rss,My Feed|https://example.com/search?q={topic_q}&format=rss
```

Use `{topic}` for raw topic insertion and `{topic_q}` for URL-encoded topics.

Yahoo Finance feeds are generated from tickers:

```bash
YAHOO_FINANCE_SYMBOLS=SPY,QQQ,HOOD,COIN,BTC-USD
```

## Local CLI smoke test

```bash
newsbot-cli search "Prediction Markets"
newsbot-cli article "Prediction Markets"
```

With `LLM_PROVIDER=stub`, this exercises the whole pipeline without paid API keys.

## Notes on "real news"

This project avoids scraping paywalled or restricted sites. X uses the official API when `X_BEARER_TOKEN` is present. Bloomberg should be connected via a permitted RSS/feed URL or licensed data product. Yahoo Finance is read through public ticker RSS feeds.
