from __future__ import annotations

import argparse
import json
import sys

from asset_aggregator.aggregator import aggregate_assets
from asset_aggregator.config import load_settings


def _format_money(value: float | None, currency: str) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f} {currency}"


def print_report(as_json: bool = False) -> int:
    settings = load_settings()
    result = aggregate_assets(settings)

    if as_json:
        print(result.model_dump_json(indent=2))
        return 0 if all(b.ok for b in result.brokers) else 2

    print("=== 资产汇总 / Asset Total ===")
    print(f"报告币种: {result.report_currency}")
    print(f"时间: {result.fetched_at.isoformat()}")
    print()

    exit_code = 0
    for item in result.brokers:
        print(f"[{item.broker}] source={item.source}")
        if item.error:
            exit_code = 2
            print(f"  错误: {item.error}")
            continue
        converted = result.converted_total(item)
        print(f"  总资产: {_format_money(item.total_assets, item.currency)}")
        if item.cash is not None:
            print(f"  现金:   {_format_money(item.cash, item.currency)}")
        if item.market_value is not None:
            print(f"  市值:   {_format_money(item.market_value, item.currency)}")
        if converted is not None and item.currency != result.report_currency:
            print(f"  折合:   {_format_money(converted, result.report_currency)}")
        elif item.currency != result.report_currency:
            print(f"  折合:   缺少汇率 {item.currency}/{result.report_currency}")
            exit_code = 2
        if item.accounts:
            print(f"  账户数: {len(item.accounts)}")
        print()

    if result.missing_fx:
        print(f"缺少汇率: {', '.join(result.missing_fx)}")
        print("请在 .env 设置 FX_RATES，例如 FX_RATES=HKD/CNY=0.92,USD/CNY=7.2")
        print()

    ok_count = sum(1 for b in result.brokers if b.ok and result.converted_total(b) is not None)
    if ok_count:
        print(f"合计 ({result.report_currency}): {result.total:,.2f}")
    else:
        print("合计: 暂无可用数据")
        exit_code = 2

    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query and sum Futu + Tonghuashun account assets",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use built-in demo numbers (no live broker connection)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.demo:
        import os

        os.environ["DEMO"] = "true"
    code = print_report(as_json=args.json)
    sys.exit(code)


if __name__ == "__main__":
    main()
