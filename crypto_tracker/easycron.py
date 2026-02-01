import logging
from typing import Optional

import requests

from .config import Config

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class EasyCronClient:
    def __init__(self, config: Config):
        self.base_url = config.easycron_url.rstrip("/")
        self.config = config

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=REQUEST_TIMEOUT)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"EasyCron health check failed: {e}")
            return False

    def register_job(
        self,
        name: str = "crypto-tracker",
        cron_expression: Optional[str] = None,
        timezone: str = "UTC",
    ) -> Optional[dict]:
        url = f"{self.base_url}/jobs"
        payload = {
            "name": name,
            "cron_expression": cron_expression or self.config.cron_expression,
            "timezone": timezone,
            "webhook_url": self.config.webhook_url,
            "webhook_secret": self.config.webhook_secret,
        }

        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            job = resp.json()
            logger.info(f"Registered job: id={job.get('id')}, name={job.get('name')}")
            return job
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Failed to register job: {e.response.status_code} - {e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to register job: {e}")
            return None

    def list_jobs(self) -> list:
        url = f"{self.base_url}/jobs"
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            jobs = resp.json()
            return jobs if isinstance(jobs, list) else jobs.get("jobs", [])
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

    def delete_job(self, job_id: str) -> bool:
        url = f"{self.base_url}/jobs/{job_id}"
        try:
            resp = requests.delete(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            logger.info(f"Deleted job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False
