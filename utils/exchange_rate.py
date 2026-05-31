# -*- coding: utf-8 -*-
"""Currency exchange rate fetching utility."""

import requests
import time
from functools import lru_cache


# Primary and fallback URLs for the exchange rate API
_API_URLS = [
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json",
    "https://latest.currency-api.pages.dev/v1/currencies/usd.min.json",
]

# Timeout for each request (seconds)
_REQUEST_TIMEOUT = 5


@lru_cache(maxsize=1)
def get_usd_to_uzs_rate() -> float:
    """
    Fetch the latest USD to UZS (Uzbek Som) exchange rate.
    Returns the number of UZS per 1 USD.
    Uses primary jsDelivr CDN with Cloudflare fallback.
    Raises an exception if all sources fail.
    """
    last_error = None
    for url in _API_URLS:
        try:
            resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            rate = data.get("usd", {}).get("uzs")
            if rate and isinstance(rate, (int, float)) and rate > 0:
                return float(rate)
        except Exception as e:
            last_error = e
            time.sleep(0.5)
            continue
    raise RuntimeError(
        f"Failed to fetch USD→UZS exchange rate from all sources. Last error: {last_error}"
    )


def som_to_usd(som_amount: float, rate: float = None) -> float:
    """Convert Uzbek Som (UZS) to USD using the given exchange rate."""
    if rate is None:
        rate = get_usd_to_uzs_rate()
    if rate <= 0:
        raise ValueError(f"Invalid exchange rate: {rate}")
    return som_amount / rate
