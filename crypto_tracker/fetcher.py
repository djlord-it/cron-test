import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


@dataclass
class CryptoPrice:
    btc_usd: Optional[float] = None
    eth_usd: Optional[float] = None


@dataclass
class ExchangeRates:
    eur: Optional[float] = None
    gbp: Optional[float] = None
    jpy: Optional[float] = None


@dataclass
class AggregatedData:
    crypto: CryptoPrice
    rates: ExchangeRates
    source: str
    raw_data: dict


def fetch_coincap() -> Optional[CryptoPrice]:
    try:
        btc_resp = requests.get("https://api.coincap.io/v2/assets/bitcoin", timeout=REQUEST_TIMEOUT)
        btc_resp.raise_for_status()
        btc_price = float(btc_resp.json()["data"]["priceUsd"])

        eth_resp = requests.get("https://api.coincap.io/v2/assets/ethereum", timeout=REQUEST_TIMEOUT)
        eth_resp.raise_for_status()
        eth_price = float(eth_resp.json()["data"]["priceUsd"])

        prices = CryptoPrice(btc_usd=btc_price, eth_usd=eth_price)
        logger.info(f"CoinCap: BTC=${prices.btc_usd:.2f}, ETH=${prices.eth_usd:.2f}")
        return prices
    except Exception as e:
        logger.error(f"CoinCap fetch failed: {e}")
        return None


def fetch_coingecko() -> Optional[CryptoPrice]:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "bitcoin,ethereum", "vs_currencies": "usd"}

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        prices = CryptoPrice(
            btc_usd=data.get("bitcoin", {}).get("usd"),
            eth_usd=data.get("ethereum", {}).get("usd"),
        )

        logger.info(f"CoinGecko: BTC=${prices.btc_usd:.2f}, ETH=${prices.eth_usd:.2f}")
        return prices
    except Exception as e:
        logger.error(f"CoinGecko fetch failed: {e}")
        return None


def fetch_exchange_rates() -> Optional[ExchangeRates]:
    url = "https://open.er-api.com/v6/latest/USD"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        rates_data = data.get("rates", {})
        rates = ExchangeRates(
            eur=rates_data.get("EUR"),
            gbp=rates_data.get("GBP"),
            jpy=rates_data.get("JPY"),
        )

        logger.info(f"ExchangeRates: EUR={rates.eur}, GBP={rates.gbp}, JPY={rates.jpy}")
        return rates
    except Exception as e:
        logger.error(f"ExchangeRate-API fetch failed: {e}")
        return None


def fetch_all() -> AggregatedData:
    raw_data = {}

    crypto = fetch_coincap()
    source = "coincap"

    if crypto is None:
        crypto = fetch_coingecko()
        source = "coingecko"

    if crypto is None:
        crypto = CryptoPrice()
        source = "none"

    raw_data["crypto_source"] = source
    raw_data["btc_usd"] = crypto.btc_usd
    raw_data["eth_usd"] = crypto.eth_usd

    rates = fetch_exchange_rates()
    if rates is None:
        rates = ExchangeRates()

    raw_data["eur_rate"] = rates.eur
    raw_data["gbp_rate"] = rates.gbp
    raw_data["jpy_rate"] = rates.jpy

    return AggregatedData(
        crypto=crypto,
        rates=rates,
        source=source,
        raw_data=raw_data,
    )
