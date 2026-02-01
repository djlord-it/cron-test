#!/usr/bin/env python3
"""Crypto Tracker - Aggregates cryptocurrency and exchange rate data using EasyCron."""

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from config import Config
from easycron import EasyCronClient
from fetcher import fetch_all
from store import Database
from webhook import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_serve(config: Config, db: Database):
    db.connect()
    client = EasyCronClient(config)
    if not client.health_check():
        logger.error("EasyCron server is not healthy. Is it running?")
        sys.exit(1)

    existing_jobs = client.list_jobs()
    for existing_job in existing_jobs:
        if existing_job.get("name") == "crypto-tracker":
            job_id = existing_job.get("id")
            logger.info(f"Removing existing job: {job_id}")
            client.delete_job(job_id)

    job = client.register_job(
        name="crypto-tracker",
        cron_expression=config.cron_expression,
        timezone="UTC",
    )
    if not job:
        logger.error("Failed to register job with EasyCron")
        sys.exit(1)

    logger.info(f"Job registered: {job.get('id')}")
    logger.info(f"Cron expression: {config.cron_expression}")
    logger.info(f"Webhook URL: {config.webhook_url}")

    app = create_app(db, config.webhook_secret)
    logger.info(f"Starting webhook server on port {config.webhook_port}")

    try:
        app.run(host="0.0.0.0", port=config.webhook_port, debug=False)
    finally:
        db.close()


def cmd_fetch(config: Config, db: Database):
    db.connect()
    try:
        logger.info("Fetching data from APIs...")
        data = fetch_all()
        snapshot_id = db.save_snapshot(data)

        result = {
            "snapshot_id": snapshot_id,
            "source": data.source,
            "btc_usd": data.crypto.btc_usd,
            "eth_usd": data.crypto.eth_usd,
            "eur_rate": data.rates.eur,
            "gbp_rate": data.rates.gbp,
            "jpy_rate": data.rates.jpy,
        }
        print(json.dumps(result, indent=2))
    finally:
        db.close()


def cmd_jobs(config: Config):
    client = EasyCronClient(config)

    if not client.health_check():
        logger.error("EasyCron server is not healthy")
        sys.exit(1)

    jobs = client.list_jobs()
    if not jobs:
        print("No jobs registered")
        return

    print(f"Found {len(jobs)} job(s):\n")
    for job in jobs:
        print(f"  ID: {job.get('id')}")
        print(f"  Name: {job.get('name')}")
        print(f"  Cron: {job.get('cron_expression')}")
        print(f"  Enabled: {job.get('enabled')}")
        print(f"  Webhook: {job.get('webhook_url')}")
        print()


def cmd_init_db(config: Config, db: Database):
    db.connect()

    schema_path = Path(__file__).parent / "schema.sql"
    if not schema_path.exists():
        logger.error(f"Schema file not found: {schema_path}")
        sys.exit(1)

    try:
        db.init_schema(str(schema_path))
        logger.info("Database schema initialized successfully")
    finally:
        db.close()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Crypto Tracker - Price aggregation with EasyCron",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.add_parser("serve", help="Start webhook server and register job")
    subparsers.add_parser("fetch", help="Run a single fetch (for testing)")
    subparsers.add_parser("jobs", help="List registered EasyCron jobs")
    subparsers.add_parser("init-db", help="Initialize database schema")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = Config.from_env()
    db = Database(config.database_url)

    if args.command == "serve":
        cmd_serve(config, db)
    elif args.command == "fetch":
        cmd_fetch(config, db)
    elif args.command == "jobs":
        cmd_jobs(config)
    elif args.command == "init-db":
        cmd_init_db(config, db)


if __name__ == "__main__":
    main()
