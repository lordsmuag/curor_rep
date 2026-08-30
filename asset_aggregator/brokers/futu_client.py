from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from asset_aggregator.brokers.base import BrokerClient
from asset_aggregator.config import FutuSettings
from asset_aggregator.models import BrokerAssets


def _enum_attr(module: Any, name: str, value: str) -> Any:
    enum_cls = getattr(module, name)
    try:
        return getattr(enum_cls, value)
    except AttributeError as exc:
        raise ValueError(f"Invalid {name}.{value}") from exc


class FutuClient(BrokerClient):
    name = "futu"

    def __init__(self, settings: FutuSettings):
        self.settings = settings

    def fetch(self) -> BrokerAssets:
        try:
            import futu as ft
        except ImportError as exc:
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error=f"futu-api not installed: {exc}",
            )

        trd_env = _enum_attr(ft, "TrdEnv", self.settings.trd_env)
        security_firm = _enum_attr(ft, "SecurityFirm", self.settings.security_firm)
        filter_market = _enum_attr(ft, "TrdMarket", self.settings.filter_trdmarket)
        currency = _enum_attr(ft, "Currency", self.settings.currency)

        ctx = None
        try:
            ctx = ft.OpenSecTradeContext(
                filter_trdmarket=filter_market,
                host=self.settings.host,
                port=self.settings.port,
                security_firm=security_firm,
            )

            if self.settings.trade_password:
                ret, data = ctx.unlock_trade(self.settings.trade_password)
                if ret != ft.RET_OK:
                    return BrokerAssets(
                        broker=self.name,
                        total_assets=0.0,
                        currency=self.settings.currency,
                        error=f"unlock_trade failed: {data}",
                    )

            ret, acc_list = ctx.get_acc_list()
            if ret != ft.RET_OK:
                return BrokerAssets(
                    broker=self.name,
                    total_assets=0.0,
                    currency=self.settings.currency,
                    error=f"get_acc_list failed: {acc_list}",
                )

            accounts: list[dict[str, Any]] = []
            total = 0.0
            cash_sum = 0.0
            mv_sum = 0.0
            has_cash = False
            has_mv = False

            # Prefer real accounts matching requested env
            rows = acc_list.to_dict(orient="records") if hasattr(acc_list, "to_dict") else []
            for row in rows:
                acc_id = int(row.get("acc_id", 0) or 0)
                # Skip mismatched sim/real when column present
                trd_env_col = str(row.get("trd_env", "") or "")
                if trd_env_col and trd_env_col != self.settings.trd_env:
                    continue

                ret, funds = ctx.accinfo_query(
                    trd_env=trd_env,
                    acc_id=acc_id,
                    refresh_cache=True,
                    currency=currency,
                )
                if ret != ft.RET_OK:
                    accounts.append(
                        {
                            "acc_id": acc_id,
                            "error": str(funds),
                            "meta": {k: row.get(k) for k in row},
                        }
                    )
                    continue

                fund_row = funds.iloc[0].to_dict() if hasattr(funds, "iloc") else dict(funds)
                assets = float(fund_row.get("total_assets") or 0.0)
                cash = fund_row.get("cash")
                market_val = fund_row.get("market_val")
                total += assets
                if cash is not None:
                    cash_sum += float(cash)
                    has_cash = True
                if market_val is not None:
                    mv_sum += float(market_val)
                    has_mv = True
                accounts.append(
                    {
                        "acc_id": acc_id,
                        "total_assets": assets,
                        "cash": float(cash) if cash is not None else None,
                        "market_val": float(market_val) if market_val is not None else None,
                        "currency": self.settings.currency,
                        "meta": {
                            k: row.get(k)
                            for k in (
                                "trd_env",
                                "acc_type",
                                "uni_card_num",
                                "card_num",
                                "security_firm",
                                "sim_acc_type",
                            )
                            if k in row
                        },
                    }
                )

            if not accounts:
                return BrokerAssets(
                    broker=self.name,
                    total_assets=0.0,
                    currency=self.settings.currency,
                    error="No matching Futu accounts returned by OpenD",
                    raw={"acc_list": rows},
                )

            return BrokerAssets(
                broker=self.name,
                total_assets=total,
                currency=self.settings.currency,
                cash=cash_sum if has_cash else None,
                market_value=mv_sum if has_mv else None,
                accounts=accounts,
                source="futu-opend",
                fetched_at=datetime.now(timezone.utc),
            )
        except Exception as exc:  # noqa: BLE001 - surface connection errors cleanly
            return BrokerAssets(
                broker=self.name,
                total_assets=0.0,
                currency=self.settings.currency,
                error=f"Futu OpenD error: {exc}",
            )
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:  # noqa: BLE001
                    pass
