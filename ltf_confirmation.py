# ============================================================
# THE GHOST IN THE MACHINE
# File: ltf_confirmation.py
# Purpose: Confirm entry on 5M/1M after 1H zone is active
#          Looks for micro MSS, micro FVG, micro OB
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from mt5_connection import connect, get_candles, disconnect

# --- SETTINGS ---
LTF_TIMEFRAMES = {
    "5M": mt5.TIMEFRAME_M5,
    "1M": mt5.TIMEFRAME_M1
}
LTF_LOOKBACK = 20

# --- DETECT MICRO MSS ---
def detect_ltf_mss(symbol, direction, timeframe, lookback=LTF_LOOKBACK):
    df = get_candles(symbol, timeframe, lookback)
    if df is None or len(df) < 5:
        return None

    last_close = df['close'].iloc[-2]
    last_time  = df.index[-2]

    if direction == "BULLISH":
        swing_high = df['high'].iloc[:-2].max()
        swing_high_time = df['high'].iloc[:-2].idxmax()
        confirmed = last_close > swing_high
        return {
            "type"      : "MICRO_MSS_BULLISH",
            "level"     : round(swing_high, 5),
            "level_time": swing_high_time,
            "close"     : round(last_close, 5),
            "candle"    : last_time,
            "confirmed" : confirmed
        }

    if direction == "BEARISH":
        swing_low = df['low'].iloc[:-2].min()
        swing_low_time = df['low'].iloc[:-2].idxmin()
        confirmed = last_close < swing_low
        return {
            "type"      : "MICRO_MSS_BEARISH",
            "level"     : round(swing_low, 5),
            "level_time": swing_low_time,
            "close"     : round(last_close, 5),
            "candle"    : last_time,
            "confirmed" : confirmed
        }
    return None

# --- DETECT MICRO FVG ---
def detect_ltf_fvg(symbol, direction, timeframe, lookback=LTF_LOOKBACK):
    df = get_candles(symbol, timeframe, lookback)
    if df is None or len(df) < 3:
        return []

    current_price = (df['high'].iloc[-1] + df['low'].iloc[-1]) / 2
    fvgs = []

    for i in range(1, len(df) - 1):
        c1 = df.iloc[i - 1]
        c3 = df.iloc[i + 1]

        if direction == "BULLISH":
            if c3['low'] > c1['high']:
                fvg_high = c3['low']
                fvg_low  = c1['high']
                price_in = fvg_low <= current_price <= fvg_high
                fvgs.append({
                    "type"    : "MICRO_BULLISH_FVG",
                    "high"    : round(fvg_high, 5),
                    "low"     : round(fvg_low, 5),
                    "time"    : df.index[i],
                    "price_in": price_in
                })

        elif direction == "BEARISH":
            if c3['high'] < c1['low']:
                fvg_high = c1['low']
                fvg_low  = c3['high']
                price_in = fvg_low <= current_price <= fvg_high
                fvgs.append({
                    "type"    : "MICRO_BEARISH_FVG",
                    "high"    : round(fvg_high, 5),
                    "low"     : round(fvg_low, 5),
                    "time"    : df.index[i],
                    "price_in": price_in
                })

    return fvgs[-3:] if fvgs else []

# --- DETECT MICRO OB ---
def detect_ltf_ob(symbol, direction, timeframe, lookback=LTF_LOOKBACK):
    df = get_candles(symbol, timeframe, lookback)
    if df is None or len(df) < 3:
        return []

    current_price = (df['high'].iloc[-1] + df['low'].iloc[-1]) / 2
    obs = []

    for i in range(len(df) - 2):
        c  = df.iloc[i]
        nc = df.iloc[i + 1]

        if direction == "BULLISH":
            if c['close'] < c['open'] and nc['close'] > nc['open']:
                mean     = (c['high'] + c['low']) / 2
                price_in = c['low'] <= current_price <= c['high']
                obs.append({
                    "type"    : "MICRO_BULLISH_OB",
                    "high"    : round(c['high'], 5),
                    "low"     : round(c['low'], 5),
                    "mean"    : round(mean, 5),
                    "time"    : df.index[i],
                    "price_in": price_in
                })

        elif direction == "BEARISH":
            if c['close'] > c['open'] and nc['close'] < nc['open']:
                mean     = (c['high'] + c['low']) / 2
                price_in = c['low'] <= current_price <= c['high']
                obs.append({
                    "type"    : "MICRO_BEARISH_OB",
                    "high"    : round(c['high'], 5),
                    "low"     : round(c['low'], 5),
                    "mean"    : round(mean, 5),
                    "time"    : df.index[i],
                    "price_in": price_in
                })

    return obs[-3:] if obs else []

# --- FULL LTF CONFIRMATION SCAN ---
def confirm_ltf_entry(symbol, direction):
    print(f"\n{'=' * 55}")
    print(f"  LTF CONFIRMATION -- {symbol} -- {direction}")
    print(f"{'=' * 55}")

    confirmed_signals = []

    for tf_name, tf in LTF_TIMEFRAMES.items():
        print(f"\n  [{tf_name}] Scanning...")

        mss = detect_ltf_mss(symbol, direction, tf)
        if mss:
            status = "CONFIRMED" if mss['confirmed'] else "NOT YET"
            print(f"    Micro MSS    : {status} -- level {mss['level']} | close {mss['close']}")

        fvgs = detect_ltf_fvg(symbol, direction, tf)
        fvg_active = any(f['price_in'] for f in fvgs)
        print(f"    Micro FVGs   : {len(fvgs)} found | Price in FVG: {fvg_active}")
        for f in fvgs:
            marker = " <- PRICE HERE" if f['price_in'] else ""
            print(f"      {f['low']} -- {f['high']} | {f['time']}{marker}")

        obs = detect_ltf_ob(symbol, direction, tf)
        ob_active = any(o['price_in'] for o in obs)
        print(f"    Micro OBs    : {len(obs)} found | Price in OB: {ob_active}")
        for o in obs:
            marker = " <- PRICE HERE" if o['price_in'] else ""
            print(f"      {o['low']} -- {o['high']} | Mean: {o['mean']}{marker}")

        mss_ok = mss and mss['confirmed']
        ltf_confirmed = mss_ok or fvg_active or ob_active
        status = "CONFIRMED" if ltf_confirmed else "WAITING"
        print(f"\n    [{tf_name}] LTF Signal: {status}")

        if ltf_confirmed:
            confirmed_signals.append({
                "timeframe": tf_name,
                "mss"      : mss_ok,
                "fvg"      : fvg_active,
                "ob"       : ob_active
            })

    print(f"\n  {'=' * 50}")
    if confirmed_signals:
        print(f"  >>> LTF ENTRY CONFIRMED on: {[s['timeframe'] for s in confirmed_signals]}")
    else:
        print(f'  >>> No LTF confirmation yet -- monitoring')
