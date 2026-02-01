import json
import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .fetcher import AggregatedData

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._conn = None

    def connect(self):
        self._conn = psycopg2.connect(self.database_url)
        self._conn.autocommit = False
        logger.info("Database connected")

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    @contextmanager
    def cursor(self):
        cur = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def init_schema(self, schema_path: str):
        with open(schema_path) as f:
            schema_sql = f.read()

        with self.cursor() as cur:
            cur.execute(schema_sql)
        logger.info("Schema initialized")

    def save_snapshot(self, data: AggregatedData) -> int:
        sql = """
            INSERT INTO price_snapshots
                (source, btc_usd, eth_usd, eur_rate, gbp_rate, jpy_rate, raw_data)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        with self.cursor() as cur:
            cur.execute(
                sql,
                (
                    data.source,
                    data.crypto.btc_usd,
                    data.crypto.eth_usd,
                    data.rates.eur,
                    data.rates.gbp,
                    data.rates.jpy,
                    json.dumps(data.raw_data),
                ),
            )
            row = cur.fetchone()
            snapshot_id = row["id"]

        logger.info(f"Saved snapshot {snapshot_id}")
        return snapshot_id

    def get_latest_snapshot(self) -> Optional[dict]:
        sql = "SELECT * FROM price_snapshots ORDER BY fetched_at DESC LIMIT 1"
        with self.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()

    def get_previous_snapshot(self) -> Optional[dict]:
        sql = "SELECT * FROM price_snapshots ORDER BY fetched_at DESC LIMIT 1 OFFSET 1"
        with self.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()

    def save_alert(
        self,
        asset: str,
        previous_price: float,
        current_price: float,
        change_pct: float,
        snapshot_id: int,
    ):
        sql = """
            INSERT INTO price_alerts
                (asset, previous_price, current_price, change_pct, snapshot_id)
            VALUES
                (%s, %s, %s, %s, %s)
        """
        with self.cursor() as cur:
            cur.execute(
                sql, (asset, previous_price, current_price, change_pct, snapshot_id)
            )
        logger.warning(
            f"ALERT: {asset} changed {change_pct:.2f}% (${previous_price:.2f} -> ${current_price:.2f})"
        )

    def log_execution(
        self,
        execution_id: str,
        job_id: str,
        scheduled_at: Optional[str] = None,
        fired_at: Optional[str] = None,
        status: str = "pending",
        error_message: Optional[str] = None,
    ):
        sql = """
            INSERT INTO execution_log
                (execution_id, job_id, scheduled_at, fired_at, status, error_message)
            VALUES
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (execution_id) DO UPDATE SET
                status = EXCLUDED.status,
                error_message = EXCLUDED.error_message
        """
        with self.cursor() as cur:
            cur.execute(
                sql,
                (execution_id, job_id, scheduled_at, fired_at, status, error_message),
            )

    def update_execution_status(
        self, execution_id: str, status: str, error_message: Optional[str] = None
    ):
        sql = """
            UPDATE execution_log
            SET status = %s, error_message = %s
            WHERE execution_id = %s
        """
        with self.cursor() as cur:
            cur.execute(sql, (status, error_message, execution_id))
