# Crypto Tracker

A cryptocurrency and exchange rate tracker that automatically fetches prices on a schedule using [EasyCron](https://github.com/djlord-it/easy-cron).

## What It Does

- Fetches BTC and ETH prices from CoinGecko API
- Fetches USD exchange rates (EUR, GBP, JPY) from ExchangeRate-API
- Stores historical price snapshots in PostgreSQL
- Detects significant price movements (>1%) and creates alerts

## How EasyCron Helped

EasyCron is a distributed cron job scheduler that handles all the scheduling complexity for us. We register a job via REST API, and EasyCron sends HTTP webhooks to our app when it's time to fetch data.

### What We Didn't Have to Build

| Feature | Without EasyCron | With EasyCron |
|---------|------------------|---------------|
| Cron parsing | Build or import a cron parser | Handled by EasyCron |
| Job scheduling | Run a scheduler thread/process | Just receive webhooks |
| Retry logic | Implement exponential backoff | Built-in (4 attempts with backoff) |
| Execution tracking | Build logging infrastructure | EasyCron tracks every execution |
| Timezone handling | Parse IANA timezones | Pass timezone string to API |
| Missed job recovery | Complex state management | EasyCron guarantees delivery |
| Failure isolation | Handle scheduler crashes | Scheduler is separate service |

### Our Integration Code

The entire EasyCron integration is ~150 lines:

- **`easycron.py`** - HTTP client to register/list/delete jobs
- **`webhook.py`** - Flask endpoint that receives triggers and verifies HMAC signatures

Everything else is business logic: fetching prices, storing data, analyzing changes.

## Quick Start

### 1. Set up EasyCron

```bash
# Download binary (macOS Apple Silicon example)
curl -L https://github.com/djlord-it/easy-cron/releases/download/v1.0.0/easycron-darwin-arm64 -o easycron
chmod +x easycron

# Create database and apply schema
createdb easycron
curl -s https://raw.githubusercontent.com/djlord-it/easy-cron/main/schema/001_initial.sql | psql easycron

# Start EasyCron
DATABASE_URL="postgres://localhost/easycron?sslmode=disable" ./easycron serve
```

### 2. Set up Crypto Tracker

```bash
# Install dependencies
pip install -r crypto_tracker/requirements.txt

# Create database
createdb crypto_tracker

# Initialize schema
python -m crypto_tracker init-db

# Start the tracker
python -m crypto_tracker serve
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgres://localhost/crypto_tracker` | PostgreSQL connection |
| `EASYCRON_URL` | `http://localhost:8080` | EasyCron server URL |
| `WEBHOOK_HOST` | `http://localhost` | Host for webhook callbacks |
| `WEBHOOK_PORT` | `9090` | Port for webhook server |
| `WEBHOOK_SECRET` | `my-secret-key` | HMAC secret for signature verification |
| `CRON_EXPRESSION` | `* * * * *` | How often to fetch (every minute by default) |

## Commands

```bash
python -m crypto_tracker serve    # Start webhook server and register job
python -m crypto_tracker fetch    # Run a single fetch (for testing)
python -m crypto_tracker jobs     # List registered EasyCron jobs
python -m crypto_tracker init-db  # Initialize database schema
```

## Architecture

```
┌─────────────┐  webhook   ┌─────────────┐  save   ┌─────────────────┐
│  EasyCron   │ ─────────► │   Crypto    │ ──────► │   PostgreSQL    │
│  Scheduler  │            │   Tracker   │         │    Database     │
└─────────────┘            └─────────────┘         └─────────────────┘
                                  │
                                  │ fetch prices
                                  ▼
                           ┌─────────────┐
                           │  CoinGecko  │
                           │ ExchangeAPI │
                           └─────────────┘
```

1. EasyCron triggers our webhook based on the cron schedule
2. Crypto Tracker fetches prices from external APIs
3. Data is stored in PostgreSQL with timestamp
4. Price changes are analyzed and alerts are created if needed

## Why This Approach Works

**Separation of concerns** - Our app focuses on fetching and analyzing data. Scheduling is someone else's job.

**Reliability** - EasyCron retries failed webhook deliveries automatically. If our app crashes and restarts, jobs keep running.

**Simplicity** - No scheduler threads, no cron libraries, no retry logic. Just a webhook endpoint.

## Resources

- [EasyCron README](https://github.com/djlord-it/easy-cron/blob/main/README.md) - Setup and API documentation
- [EasyCron Operators Guide](https://github.com/djlord-it/easy-cron/blob/main/OPERATORS.md) - Deployment and operational details
