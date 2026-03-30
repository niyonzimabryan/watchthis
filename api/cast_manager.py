from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import pychromecast
from pychromecast.controllers.dashcast import DashCastController

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "cast_config.json"

# Cache discovered devices to avoid repeated 5-8s scans
_device_cache: list[dict[str, Any]] = []
_cache_ts: float = 0
_CACHE_TTL = 300  # 5 minutes


def _load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_config(data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def _scan_sync(timeout: float = 8.0) -> list[dict[str, Any]]:
    """Blocking Chromecast scan. Run in executor."""
    global _device_cache, _cache_ts

    if _device_cache and (time.time() - _cache_ts) < _CACHE_TTL:
        return _device_cache

    services, browser = pychromecast.discovery.discover_chromecasts(timeout=timeout)
    pychromecast.discovery.stop_discovery(browser)

    devices = []
    for service in services:
        devices.append({
            "name": service.friendly_name,
            "ip": str(service.host),
            "port": service.port,
            "model": service.model_name,
            "uuid": str(service.uuid),
        })

    _device_cache = devices
    _cache_ts = time.time()
    return devices


def _cast_url_sync(device_name: str, url: str, timeout: float = 10.0) -> bool:
    """Blocking cast via DashCast. Run in executor."""
    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[device_name]
    )
    if not chromecasts:
        pychromecast.discovery.stop_discovery(browser)
        logger.warning("Device '%s' not found on network", device_name)
        return False

    cast = chromecasts[0]
    cast.wait(timeout=timeout)

    dc = DashCastController()
    cast.register_handler(dc)

    dc.load_url(url, force=True)

    # Give DashCast a moment to load
    cast.socket_client.disconnect()
    pychromecast.discovery.stop_discovery(browser)
    return True


def _stop_cast_sync(device_name: str, timeout: float = 10.0) -> bool:
    """Blocking stop cast. Run in executor."""
    chromecasts, browser = pychromecast.get_listed_chromecasts(
        friendly_names=[device_name]
    )
    if not chromecasts:
        pychromecast.discovery.stop_discovery(browser)
        return False

    cast = chromecasts[0]
    cast.wait(timeout=timeout)
    cast.quit_app()
    cast.socket_client.disconnect()
    pychromecast.discovery.stop_discovery(browser)
    return True


class CastManager:
    def get_saved_device(self) -> str | None:
        config = _load_config()
        return config.get("device_name")

    def save_device(self, name: str) -> None:
        config = _load_config()
        config["device_name"] = name
        _save_config(config)

    async def scan_devices(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(_scan_sync)

    async def cast_url(self, url: str, device_name: str | None = None) -> bool:
        target = device_name or self.get_saved_device()
        if not target:
            logger.error("No device specified and no saved device")
            return False

        # Save on first successful use
        if not self.get_saved_device():
            self.save_device(target)

        try:
            return await asyncio.to_thread(_cast_url_sync, target, url)
        except Exception:
            logger.exception("Failed to cast to '%s'", target)
            return False

    async def stop_cast(self, device_name: str | None = None) -> bool:
        target = device_name or self.get_saved_device()
        if not target:
            return False
        try:
            return await asyncio.to_thread(_stop_cast_sync, target)
        except Exception:
            logger.exception("Failed to stop cast on '%s'", target)
            return False

    async def has_device(self) -> bool:
        return self.get_saved_device() is not None
