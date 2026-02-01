import hashlib
import hmac
import json
import logging

from flask import Flask, jsonify, request

from .analyzer import analyze_price_change
from .fetcher import fetch_all
from .store import Database

logger = logging.getLogger(__name__)


def create_app(db: Database, webhook_secret: str) -> Flask:
    app = Flask(__name__)
    app.config["db"] = db
    app.config["webhook_secret"] = webhook_secret

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/webhook", methods=["POST"])
    def webhook():
        # Verify HMAC signature
        signature = request.headers.get("X-EasyCron-Signature", "")
        if not verify_signature(webhook_secret, request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({"error": "invalid signature"}), 401

        # Parse webhook payload
        try:
            payload = request.get_json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            return jsonify({"error": "invalid payload"}), 400

        execution_id = payload.get("execution_id", "unknown")
        job_id = payload.get("job_id", "unknown")
        scheduled_at = payload.get("scheduled_at")
        fired_at = payload.get("fired_at")

        logger.info(f"Received webhook: execution={execution_id}, job={job_id}")

        # Log the execution
        db.log_execution(
            execution_id=execution_id,
            job_id=job_id,
            scheduled_at=scheduled_at,
            fired_at=fired_at,
            status="processing",
        )

        try:
            # Fetch data from APIs
            data = fetch_all()

            # Save to database
            snapshot_id = db.save_snapshot(data)

            # Analyze for price changes
            analyze_price_change(db, snapshot_id)

            # Update execution status
            db.update_execution_status(execution_id, "completed")

            result = {
                "status": "ok",
                "snapshot_id": snapshot_id,
                "btc_usd": data.crypto.btc_usd,
                "eth_usd": data.crypto.eth_usd,
                "eur_rate": data.rates.eur,
            }
            logger.info(f"Execution {execution_id} completed: {json.dumps(result)}")
            return jsonify(result)

        except Exception as e:
            logger.error(f"Execution {execution_id} failed: {e}")
            db.update_execution_status(execution_id, "failed", str(e))
            return jsonify({"error": str(e)}), 500

    return app


def verify_signature(secret: str, body: bytes, signature: str) -> bool:
    if not signature:
        return False

    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)
