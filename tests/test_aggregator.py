from __future__ import annotations

import json
from pathlib import Path

from asset_aggregator.aggregator import aggregate_assets
from asset_aggregator.brokers.ths_client import ThsClient, _pick_total
from asset_aggregator.config import AppSettings, ThsSettings
from asset_aggregator.models import BrokerAssets, TotalAssets


def test_pick_total_chinese_keys():
    total, detail = _pick_total({"总资产": 100.5, "可用金额": 10})
    assert total == 100.5
    assert detail["可用金额"] == 10


def test_pick_total_nested_data():
    total, _ = _pick_total({"status": "success", "data": {"total_assets": 88.0}})
    assert total == 88.0


def test_ths_from_file(tmp_path: Path):
    snap = tmp_path / "ths.json"
    snap.write_text(
        json.dumps({"总资产": 12345.67, "股票市值": 10000, "可用金额": 2345.67}),
        encoding="utf-8",
    )
    client = ThsClient(ThsSettings(mode="file", snapshot_path=str(snap)))
    result = client.fetch()
    assert result.ok
    assert result.total_assets == 12345.67
    assert result.market_value == 10000


def test_ths_from_env():
    client = ThsClient(ThsSettings(mode="env", total_assets=999.0))
    result = client.fetch()
    assert result.ok
    assert result.total_assets == 999.0


def test_aggregate_demo_with_fx():
    settings = AppSettings(
        demo=True,
        report_currency="CNY",
        fx_rates="HKD/CNY=0.9",
    )
    total = aggregate_assets(settings)
    assert len(total.brokers) == 2
    futu = next(b for b in total.brokers if b.broker == "futu")
    ths = next(b for b in total.brokers if b.broker == "tonghuashun")
    assert abs(total.converted_total(futu) - 128450.55 * 0.9) < 1e-6
    assert total.converted_total(ths) == 203340.12
    assert abs(total.total - (128450.55 * 0.9 + 203340.12)) < 1e-6


def test_total_assets_missing_fx():
    total = TotalAssets(
        report_currency="CNY",
        brokers=[
            BrokerAssets(broker="futu", total_assets=100, currency="HKD"),
            BrokerAssets(broker="tonghuashun", total_assets=200, currency="CNY"),
        ],
        fx_rates={},
    )
    assert total.missing_fx == ["HKD"]
    assert total.total == 200
