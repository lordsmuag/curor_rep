from __future__ import annotations

from datetime import datetime, timezone

from asset_aggregator.brokers.futu_client import FutuClient
from asset_aggregator.brokers.ths_client import ThsClient
from asset_aggregator.config import AppSettings
from asset_aggregator.models import BrokerAssets, TotalAssets


def _demo_brokers() -> list[BrokerAssets]:
    now = datetime.now(timezone.utc)
    return [
        BrokerAssets(
            broker="futu",
            total_assets=128450.55,
            currency="HKD",
            cash=12000.0,
            market_value=116450.55,
            accounts=[{"acc_id": 0, "total_assets": 128450.55}],
            source="demo",
            fetched_at=now,
        ),
        BrokerAssets(
            broker="tonghuashun",
            total_assets=203340.12,
            currency="CNY",
            cash=15340.12,
            market_value=188000.0,
            accounts=[{"total_assets": 203340.12}],
            source="demo",
            fetched_at=now,
        ),
    ]


def aggregate_assets(settings: AppSettings | None = None) -> TotalAssets:
    settings = settings or AppSettings()
    brokers: list[BrokerAssets] = []

    if settings.demo:
        brokers.extend(_demo_brokers())
    else:
        if settings.futu.enabled:
            brokers.append(FutuClient(settings.futu).fetch())
        if settings.ths.enabled:
            brokers.append(ThsClient(settings.ths).fetch())

    return TotalAssets(
        report_currency=settings.report_currency,
        brokers=brokers,
        fx_rates=settings.parsed_fx_rates(),
        fetched_at=datetime.now(timezone.utc),
    )
