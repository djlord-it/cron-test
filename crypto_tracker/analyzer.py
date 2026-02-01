import logging

from store import Database

logger = logging.getLogger(__name__)

ALERT_THRESHOLD_PCT = 1.0


def analyze_price_change(db: Database, current_snapshot_id: int) -> None:
    current = db.get_latest_snapshot()
    previous = db.get_previous_snapshot()

    if not current or not previous:
        logger.info("Not enough data for price change analysis")
        return

    for asset, key in [("BTC", "btc_usd"), ("ETH", "eth_usd")]:
        if current.get(key) and previous.get(key):
            change = calculate_change_pct(float(previous[key]), float(current[key]))
            if abs(change) >= ALERT_THRESHOLD_PCT:
                db.save_alert(
                    asset=asset,
                    previous_price=float(previous[key]),
                    current_price=float(current[key]),
                    change_pct=change,
                    snapshot_id=current_snapshot_id,
                )
            else:
                logger.info(f"{asset} change: {change:.2f}% (below threshold)")


def calculate_change_pct(old_value: float, new_value: float) -> float:
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100
