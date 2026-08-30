from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from asset_aggregator.brokers.base import BrokerClient
from asset_aggregator.config import ThsSettings
from asset_aggregator.models import BrokerAssets


def _pick_total(payload: dict[str, Any]) -> tuple[float | None, dict[str, Any]]:
    """Extract total assets from common THS / bridge response shapes."""
    candidates = (
        "总资产",
        "total_assets",
        "totalAssets",
        "资产总额",
        "净资产",
    )
    data = payload.get("data", payload)
    if isinstance(data, list) and data:
        data = data[0]
    if not isinstance(data, dict):
        return None, {"payload": payload}

    for key in candidates:
        if key in data and data[key] is not None:
            return float(data[key]), data

    # Nested balance object
    balance = data.get("balance")
    if isinstance(balance, dict):
        for key in candidates:
            if key in balance and balance[key] is not None:
                return float(balance[key]), balance

    return None, data if isinstance(data, dict) else {"payload": payload}


class ThsClient(BrokerClient):
    name = "tonghuashun"

    def __init__(self, settings: ThsSettings):
        self.settings = settings

    def fetch(self) -> BrokerAssets:
        mode = self.settings.mode
        try:
            if mode == "env":
                return self._from_env()
            if mode == "http":
                return self._from_http()
            if mode == "file":
                return self._from_file()
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error=f"Unknown THS mode: {mode}",
            )
        except Exception as exc:  # noqa: BLE001
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error=f"Tonghuashun fetch error: {exc}",
            )

    def _from_env(self) -> BrokerAssets:
        if self.settings.total_assets is None:
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error="THS_TOTAL_ASSETS is not set",
                source="env",
            )
        return BrokerAssets(
            broker=self.name,
            total_assets=float(self.settings.total_assets),
            currency=self.settings.currency,
            source="env",
            fetched_at=datetime.now(timezone.utc),
        )

    def _from_http(self) -> BrokerAssets:
        resp = requests.get(self.settings.http_url, timeout=self.settings.http_timeout)
        resp.raise_for_status()
        payload = resp.json()
        total, detail = _pick_total(payload if isinstance(payload, dict) else {"data": payload})
        if total is None:
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error="Could not find 总资产/total_assets in HTTP response",
                raw={"payload": payload},
                source="http",
            )
        cash = detail.get("可用金额", detail.get("cash"))
        market_value = detail.get("股票市值", detail.get("market_value", detail.get("参考市值")))
        return BrokerAssets(
            broker=self.name,
            total_assets=total,
            currency=self.settings.currency,
            cash=float(cash) if cash is not None else None,
            market_value=float(market_value) if market_value is not None else None,
            accounts=[{"total_assets": total, "detail": detail}],
            raw={"payload": payload},
            source="http",
            fetched_at=datetime.now(timezone.utc),
        )

    def _from_file(self) -> BrokerAssets:
        path = Path(self.settings.snapshot_path)
        if not path.exists():
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error=(
                    f"Snapshot not found: {path}. "
                    "Export from Tonghuashun or set THS_MODE=http / THS_MODE=env."
                ),
                source="file",
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("THS snapshot must be a JSON object")
        total, detail = _pick_total(payload)
        if total is None and "total_assets" in payload:
            total = float(payload["total_assets"])
            detail = payload
        if total is None:
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error="Could not find 总资产/total_assets in snapshot file",
                raw={"payload": payload},
                source="file",
            )
        cash = detail.get("可用金额", detail.get("cash"))
        market_value = detail.get("股票市值", detail.get("market_value", detail.get("参考市值")))
        return BrokerAssets(
            broker=self.name,
            total_assets=total,
            currency=payload.get("currency", self.settings.currency),
            cash=float(cash) if cash is not None else None,
            market_value=float(market_value) if market_value is not None else None,
            accounts=[{"total_assets": total, "detail": detail}],
            raw={"payload": payload},
            source="file",
            fetched_at=datetime.now(timezone.utc),
        )
