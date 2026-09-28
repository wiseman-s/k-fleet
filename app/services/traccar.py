"""Thin client for the Traccar REST API.

We only need two endpoints for the MVP:
  - /api/devices     (list all devices and their online status)
  - /api/positions   (latest known position for every device)
"""
import logging
from typing import List, Dict, Any
import httpx

from app.core.config import TRACCAR_URL, TRACCAR_TOKEN

logger = logging.getLogger(__name__)

HEADERS = {"Authorization": f"Bearer {TRACCAR_TOKEN}"}
TIMEOUT = 10.0


def fetch_devices() -> List[Dict[str, Any]]:
    url = f"{TRACCAR_URL}/api/devices"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("Traccar fetch_devices failed: %s", e)
        return []


def fetch_positions() -> List[Dict[str, Any]]:
    url = f"{TRACCAR_URL}/api/positions"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("Traccar fetch_positions failed: %s", e)
        return []


def fetch_positions_for_device(traccar_device_id: str) -> List[Dict[str, Any]]:
    """Not used in the MVP poller, but useful for history queries."""
    all_devices = fetch_devices()
    device = next(
        (d for d in all_devices if str(d.get("id")) == str(traccar_device_id) or d.get("uniqueId") == traccar_device_id),
        None,
    )
    if not device:
        return []
    url = f"{TRACCAR_URL}/api/positions?deviceId={device['id']}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("Traccar fetch_positions_for_device failed: %s", e)
        return []