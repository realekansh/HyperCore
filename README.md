# HyperCore

HyperCore is a minimal Telegram core for userbot-first deployments with optional bot polling support. V0.3.0 is scoped to proving that the core boots, loads commands, persists sudo users, performs git-based updates, and restarts cleanly in a real Telegram environment.

## Requirements

- Python 3.11
- telethon
- python-telegram-bot
- Git
- Bash for `bash startup`

Install the Telegram libraries before running the core.

```bash
pip install telethon python-telegram-bot
```

## Configuration

Edit the single root `.env` file.

Required:

- `API_ID`
- `API_HASH`

Optional:

- `BOT_TOKEN`
- `DATABASE_URL`
- `LOG_CHANNEL`

Notes:

- Core engine values live in `hypercore/core/config.py` and are not controlled by `.env`.
- `DATABASE_URL` supports SQLite paths in V0.3.0, for example `sqlite:///hypercore.db`.
- Logging is console-only in V0.3.0.

## Run

```bash
bash startup
```

You can also run the module directly.

```bash
python -m hypercore
```

## Commands

- `.ping`
- `.uptime`
- `.stats`
- `.addsudo <user_id>` or reply with `.addsudo`
- `.rmsudo <user_id>` or reply with `.rmsudo`
- `.vsudos`
- `.update -core`
- `.restart`
- `.shutdown`

## Runtime Notes

- The userbot is the primary runtime and determines the owner account.
- The bot runtime starts only when `BOT_TOKEN` is configured.
- Updates use `git pull --ff-only`.
- Restart uses full process replacement through `python -m hypercore`.
