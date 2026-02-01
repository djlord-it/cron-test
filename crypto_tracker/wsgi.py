import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from config import Config
from store import Database
from webhook import create_app
from easycron import EasyCronClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

config = Config.from_env()
db = Database(config.database_url)
db.connect()

schema_path = Path(__file__).parent / "schema.sql"
if schema_path.exists():
    try:
        db.init_schema(str(schema_path))
        logger.info("Schema initialized")
    except Exception as e:
        logger.info(f"Schema already exists or error: {e}")

if os.environ.get("REGISTER_JOB", "true").lower() == "true":
    client = EasyCronClient(config)
    if client.health_check():
        existing_jobs = client.list_jobs()
        for job in existing_jobs:
            if job.get("name") == "crypto-tracker":
                client.delete_job(job.get("id"))

        job = client.register_job(
            name="crypto-tracker",
            cron_expression=config.cron_expression,
            timezone="UTC",
        )
        if job:
            logger.info(f"Registered job: {job.get('id')}")
    else:
        logger.warning("EasyCron not available, skipping job registration")

app = create_app(db, config.webhook_secret)
