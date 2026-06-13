#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日剧本生成器
----------------
拉取 SPX / SPY / QQQ 日线 + VIX,计算关键价位(轴心点)、预期波动区间与情景树,
输出 playbook.json,供网页读取。

数据源(全部免费、无需 API key):
  - 主:yfinance(Yahoo Finance)
  - 备:Stooq 的 CSV 接口(只用 Python 标准库,云端 IP 更稳)
若两者都失败,会保留上一次的 playbook.json 不动,避免页面变空。

用法:
  python scripts/generate_playbook.py          # 真实拉数据
  python scripts/generate_playbook.py --mock    # 用内置示例数据(不联网,用于测试)
"""

import json
import sys
import math
import datetime as dt
import urllib.request

# ----------------------------------------------------------------------------
# 配置:想加/减标的,改这里即可。keyRound = 关键行权价取整步长。
# ----------------------------------------------------------------------------
TICKERS = [
    {"sym": "SPX", "name": "S&P 500 指数 · 现金结算期权", "yf": "^GSPC", "stooq": "^spx",  "keyRound": 25},
    {"sym": "SPY", "name": "S&P 500 ETF",                "yf": "SPY",   "stooq": "spy.us", "keyRound": 5},
    {"sym": "QQQ", "name": "纳指 100 ETF",                "yf": "QQQ",   "stooq": "qqq.us", "keyRound": 5},
]
VIX_YF, VIX_STOOQ = "^VIX", "^vix"

# 内置示例数据(--mock 用):锚定 2026-06 真实 SPX/VIX 量级
MOCK = {
    "vix": 19.0,
    "rows": {
        "SPX": [{"date": "2026-06-11", "high": 7488.0, "low": 7351.0, "close": 7394.30},
                {"date": "2026-06-12", "high": 7456.40, "low": 7363.01, "close": 7414.60}],
        "SPY": [{"date": "2026-06-11", "high": 748.8, "low": 735.1, "close": 739.43},
                {"date": "2026-06-12", "high": 745.64, "low": 736.30, "close": 741.46}],
        "QQQ": [{"date": "2026-06-11", "high": 626.0, "low": 612.5, "close": 620.05},
                {"date": "2026-06-12", "high": 627.10, "low": 614.30, "close": 622.40}],
    },
}


# ----------------------------------------------------------------------------
# 数据获取(失败时抛异常,由上层捕获后切换数据源)
# ----------------------------------------------------------------------------
def fetch_yf_one(symbol):
    import yfinance as yf  # 延迟导入:--mock 模式无需安装 yfinance
    df = yf.Ticker(symbol).history(period="10d", interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise ValueError(f"yfinance 返回空数据: {symbol}")
    rows = []
    for idx, r in df.iterrows():
        rows.append({"date": idx.strftime("%Y-%m-%d"),
                     "high": float(r["High"]), "low": float(r["Low"]), "close": float(r["Close"])})
    return rows


def fetch_stooq_one(stooq_sym):
    url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    lines = raw.strip().splitlines()
    if len(lines) < 2:
        raise ValueError(f"Stooq 返回空数据: {stooq_sym}")
    rows = []
    for line in lines[1:]:                       # 跳过表头 Date,Open,High,Low,Close,Volume
        p = line.split(",")
        if len(p) < 5:
            continue
        try:
            rows.append({"date": p[0], "high": float(p[2]), "low": float(p[3]), "close": float(p[4])})
        except ValueError:
            continue
    if not rows:
        raise ValueError(f"Stooq 数据无法解析: {stooq_sym}")
    return rows[-10:]


def get_all_data():
    """返回 (rows_by_sym, vix, source)。先试 yfinance,整体失败再整体退到 Stooq。"""
    # --- 尝试 yfinance ---
    try:
        rows = {t["sym"]: fetch_yf_one(t["yf"]) for t in TICKERS}
        vix = fetch_yf_one(VIX_YF)[-1]["close"]
        return rows, vix, "yfinance"
    except Exception as e:
        print(f"[warn] yfinance 整体失败,切换 Stooq:{e}", file=sys.stderr)

    # --- 退到 Stooq ---
    try:
        rows = {t["sym"]: fetch_stooq_one(t["stooq"]) for t in TICKERS}
        vix = fetch_stooq_one(VIX_STOOQ)[-1]["close"]
        return rows, vix, "stooq"
    except Exception as e:
        print(f"[error] Stooq 也失败:{e}", file=sys.stderr)
        raise


# ----------------------------------------------------------------------------
# 计算:轴心点 + 预期波动 + 关键价 + 情景文字
# ----------------------------------------------------------------------------
def compute_one(t, rows, vix):
    last = rows[-1]                              # 最近完成的一个交易日(盘前跑即昨日)
    H, L, C = last["high"], last["low"], last["close"]
    prev_close = rows[-2]["close"] if len(rows) >= 2 else C

    PP = (H + L + C) / 3.0
    R1, S1 = 2 * PP - L, 2 * PP - H
    R2, S2 = PP + (H - L), PP - (H - L)

    ref = C                                      # 参考价 = 最近收盘(日线版本)
    daily_sigma = (vix / 100.0) / math.sqrt(252)
    em = ref * daily_sigma                        # ±1σ 预期波动
    key = round(ref / t["keyRound"]) * t["keyRound"]

    return {
        "sym": t["sym"], "name": t["name"],
        "ref": round(ref, 2), "prevClose": round(prev_close, 2),
        "chg": round(ref - prev_close, 2),
        "chgPct": round((ref - prev_close) / prev_close * 100, 2) if prev_close else 0.0,
        "PP": round(PP, 2), "R1": round(R1, 2), "R2": round(R2, 2),
        "S1": round(S1, 2), "S2": round(S2, 2),
        "emUp": round(ref + em, 2), "emDn": round(ref - em, 2),
        "key": round(key, 2), "keyNote": "整数关口 · 高 OI(示例,待接期权链)",
        "sessionDate": last["date"],
    }


def build_playbook(rows_by_sym, vix, source):
    tickers = [compute_one(t, rows_by_sym[t["sym"]], vix) for t in TICKERS]
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_date": tickers[0]["sessionDate"] if tickers else None,
        "vix": round(vix, 2),
        # v1 没有期权链 → Gamma 状态留空,网页显示"需 GEX 数据"。接入 OI 后再填。
        "regime": None,
        "data_source": source,
        "tickers": tickers,
    }


# ----------------------------------------------------------------------------
def main():
    mock = "--mock" in sys.argv
    if mock:
        rows_by_sym, vix, source = MOCK["rows"], MOCK["vix"], "mock"
        print("[info] 使用内置示例数据(--mock)")
    else:
        rows_by_sym, vix, source = get_all_data()
        print(f"[info] 数据源:{source},VIX={vix:.2f}")

    playbook = build_playbook(rows_by_sym, vix, source)
    with open("playbook.json", "w", encoding="utf-8") as f:
        json.dump(playbook, f, ensure_ascii=False, indent=2)
    print(f"[ok] 已写出 playbook.json — {len(playbook['tickers'])} 个标的,"
          f"会话日 {playbook['session_date']}")


if __name__ == "__main__":
    main()
