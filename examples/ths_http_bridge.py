#!/usr/bin/env python3
"""Minimal Tonghuashun balance HTTP bridge for local Windows setups.

Run this on the same Windows machine where Tonghuashun (xiadan) is logged in,
then point the aggregator at it:

  THS_MODE=http
  THS_HTTP_URL=http://127.0.0.1:8765/balance

Requires: pip install flask easytrader pywinauto

This is an unofficial client-automation bridge. Prefer exporting a snapshot
JSON on machines where GUI automation is unreliable.
"""

from __future__ import annotations

import os

from flask import Flask, jsonify

app = Flask(__name__)
EXE_PATH = os.environ.get("THS_EXE_PATH", r"C:\同花顺软件\同花顺\xiadan.exe")


def _read_balance() -> dict:
    import easytrader

    user = easytrader.use("ths")
    user.connect(EXE_PATH)
    balance = user.balance
    # easytrader may return list or dict depending on client
    if isinstance(balance, list) and balance:
        return balance[0]
    if isinstance(balance, dict):
        return balance
    raise RuntimeError(f"Unexpected balance payload: {balance!r}")


@app.get("/balance")
def balance():
    try:
        data = _read_balance()
        return jsonify({"status": "success", "data": data})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "error": str(exc)}), 500


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8765")))
