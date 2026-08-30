from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FutuSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FUTU_", extra="ignore")

    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 11111
    # REAL or SIMULATE
    trd_env: Literal["REAL", "SIMULATE"] = "REAL"
    # NONE = all markets known to OpenD; or HK / US / CN / SG / JP / AU
    filter_trdmarket: str = "NONE"
    security_firm: str = "FUTUSECURITIES"
    # Optional unlock PIN for trade API (query-only often works without unlock)
    trade_password: str | None = None
    # Report currency preference when querying multi-currency accounts
    currency: str = "HKD"
    # Convert Futu totals into report currency using this rate (FUTU_CCY -> REPORT)
    # e.g. HKD/CNY = 0.92. Leave empty and set FX_RATES instead.
    to_cny_rate: float | None = None


class ThsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="THS_", extra="ignore")

    enabled: bool = True
    # http | file | env
    mode: Literal["http", "file", "env"] = "file"
    # Local bridge, e.g. THSAutoTrader / custom Flask: GET returns JSON with 总资产
    http_url: str = "http://127.0.0.1:5000/balance"
    http_timeout: float = 10.0
    # Snapshot JSON path when OpenD/THS client cannot be reached from this machine
    snapshot_path: str = "data/ths_snapshot.json"
    # Direct override: THS_TOTAL_ASSETS=123456.78
    total_assets: float | None = None
    currency: str = "CNY"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    report_currency: str = "CNY"
    # Comma-separated FX pairs, e.g. "HKD/CNY=0.92,USD/CNY=7.2"
    fx_rates: str = ""
    demo: bool = False

    futu: FutuSettings = Field(default_factory=FutuSettings)
    ths: ThsSettings = Field(default_factory=ThsSettings)

    def parsed_fx_rates(self) -> dict[str, float]:
        rates: dict[str, float] = {}
        raw = self.fx_rates.strip()
        if raw:
            for part in raw.split(","):
                part = part.strip()
                if not part or "=" not in part:
                    continue
                key, value = part.split("=", 1)
                rates[key.strip()] = float(value.strip())
        if self.futu.to_cny_rate is not None:
            rates.setdefault(f"{self.futu.currency}/CNY", self.futu.to_cny_rate)
            rates.setdefault(self.futu.currency, self.futu.to_cny_rate)
        return rates


def load_settings() -> AppSettings:
    return AppSettings()
