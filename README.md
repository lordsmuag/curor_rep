# 富途 + 同花顺 资产总额汇总

本工具通过 **富途官方 OpenAPI（OpenD）** 拉取富途资产，并通过 **同花顺本地桥接 / 快照文件 / 环境变量** 读取同花顺资产，然后按统一币种汇总。

> 重要限制：同花顺**没有**面向个人账户的公开远程 API。官方可用的是客户端 UI 自动化（Windows）或你自己导出的数字。本仓库不破解、不绕过同花顺登录。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cp data/ths_snapshot.example.json data/ths_snapshot.json
```

演示模式（无需任何券商连接）：

```bash
assets --demo
# 或
DEMO=true assets --json
```

## 富途（Futu OpenAPI）

1. 安装并登录 [OpenD](https://openapi.futunn.com/futu-api-doc/)（Windows / macOS / Linux）。
2. 在本机确认 OpenD 监听 `127.0.0.1:11111`（或改 `.env` 里的 `FUTU_HOST` / `FUTU_PORT`）。
3. 在富途牛牛 / OpenD 中开启 API 权限，并允许本机（或你的运行机器）访问。
4. 设置：

```env
FUTU_ENABLED=true
FUTU_HOST=127.0.0.1
FUTU_PORT=11111
FUTU_TRD_ENV=REAL
FUTU_CURRENCY=HKD
FX_RATES=HKD/CNY=0.92,USD/CNY=7.20
```

查询使用 `get_acc_list` + `accinfo_query`，读取 `total_assets`。

若此 Cloud Agent / 服务器无法访问你电脑上的 OpenD，请在 **安装了 OpenD 的那台机器** 上运行 `assets`，或把 OpenD 安全地暴露给该运行环境（不推荐公网裸奔）。

## 同花顺（三种接入）

### 方式 A：快照文件（推荐起步）

从同花顺客户端「查询 → 资金股票」抄总资产，写入 `data/ths_snapshot.json`：

```json
{
  "currency": "CNY",
  "总资产": 200134.09,
  "可用金额": 197264.69,
  "股票市值": 2869.4
}
```

```env
THS_MODE=file
THS_SNAPSHOT_PATH=data/ths_snapshot.json
```

### 方式 B：本地 HTTP 桥（Windows）

在已登录同花顺下单程序的 Windows 电脑上：

```bash
pip install flask easytrader pywinauto
set THS_EXE_PATH=C:\同花顺软件\同花顺\xiadan.exe
python examples/ths_http_bridge.py
```

聚合端配置：

```env
THS_MODE=http
THS_HTTP_URL=http://127.0.0.1:8765/balance
```

### 方式 C：环境变量

```env
THS_MODE=env
THS_TOTAL_ASSETS=200134.09
```

## 运行

```bash
assets
assets --json
```

输出示例：

```text
=== 资产汇总 / Asset Total ===
[futu] ...
[tonghuashun] ...
合计 (CNY): 321234.56
```

## 测试

```bash
pytest -q
```

## 安全说明

- 不要把 `.env`、交易密码、真实 `ths_snapshot.json` 提交到 Git。
- 不要把 OpenD / 同花顺桥对公网开放。
- 本工具默认只做**只读查询**；同花顺桥示例也只暴露余额接口。
