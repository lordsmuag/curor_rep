from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class BrokerAssets(BaseModel):
    """Normalized assets for one brokerage."""

    broker: str
    total_assets: float
    currency: str = "CNY"
    cash: float | None = None
    market_value: float | None = None
    accounts: list[dict[str, Any]] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    source: str = "api"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class TotalAssets(BaseModel):
    """Sum across brokers, converted to a report currency when rates are provided."""

    report_currency: str = "CNY"
    brokers: list[BrokerAssets] = Field(default_factory=list)
    fx_rates: dict[str, float] = Field(default_factory=dict)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def converted_total(self, item: BrokerAssets) -> float | None:
        if item.error is not None:
            return None
        if item.currency == self.report_currency:
            return item.total_assets
        rate = self.fx_rates.get(f"{item.currency}/{self.report_currency}")
        if rate is None:
            rate = self.fx_rates.get(item.currency)
        if rate is None:
            return None
        return item.total_assets * rate

    @property
    def total(self) -> float:
        values = [v for v in (self.converted_total(b) for b in self.brokers) if v is not None]
        return sum(values)

    @property
    def missing_fx(self) -> list[str]:
        missing: list[str] = []
        for item in self.brokers:
            if item.error is not None:
                continue
            if item.currency == self.report_currency:
                continue
            if self.converted_total(item) is None:
                missing.append(item.currency)
        return missing


class AssetSnapshot(BaseModel):
    """Optional on-disk snapshot used when live APIs are unavailable."""

    broker: str
    total_assets: float
    currency: str = "CNY"
    cash: float | None = None
    market_value: float | None = None
    updated_at: datetime | None = None
