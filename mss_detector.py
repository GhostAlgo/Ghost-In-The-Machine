# ============================================================
# THE GHOST IN THE MACHINE
# File: mss_detector.py
# Purpose: Detect Market Structure Shift (MSS) on 1H
#          Second condition of every valid trade setup
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from mt5_connection import connect, get_candles, disconnect

# --- SETTINGS ---
SWING_LOOKBACK = 10  # Candles to look back for swing high/low

# --- FIND MOST RECENT SWING HIGH ---
def get_swing_high(df, lookback):
    highs = df['high'].values
    # Find the highest point in the lookback window
    swing_idx = highs[-lookback:].argmax()
    swing_high = highs[-lookback:][swing_idx]
    swing_time = df.index[-lookback:][swing_idx]
    return swing_high, swing_time

# --- FIND MOST RECENT SWING LOW ---
def get_swing_low(df, lookback):
    lows = df['low'].values
    # Find the lowest point in the lookback window
    swing_idx = lows[-lookback:].argmin()
    swing_low = lows[-lookback:][swing_idx]
    swing_time = df.index[-lookback:][swing_idx]
    return swing_low, swing_time

# --- DETECT MSS ---
def detect_mss(symbol, sweep_direction):
    """
    sweep_direction: 'sell_side' = looking for bullish MSS
                     'buy_side'  = looking for bearish MSS
    """
    df = get_candles(symbol, mt5.TIMEFRAME_H1, SWING_LOOKBACK + 5)
    if df is None or len(df) < SWING_LOOKBACK + 2:
        return None

    # Most recent CLOSED candle
    last_close = df['close'].iloc[-2]
    last_high  = df['high'].iloc[-2]
    last_low   = df['low'].iloc[-2]
    last_time  = df.index[-2]

    if sweep_direction == "sell_side":
        # After sell-side sweep → look for BULLISH MSS
        # Price must close ABOVE the most recent swing high
        swing_high, swing_time = get_swing_high(df.iloc[:-2], SWING_LOOKBACK)
        mss_confirmed = last_close > swing_high
        return {
            "symbol"       : symbol,
            "direction"    : "BULLISH",
            "swing_level"  : swing_high,
            "swing_time"   : swing_time,
            "break_candle" : last_time,
            "break_close"  : last_close,
            "confirmed"    : mss_confirmed
        }

    if sweep_direction == "buy_side":
        # After buy-side sweep → look for BEARISH MSS
        # Price must close BELOW the most recent swing low
        swing_low, swing_time = get_swing_low(df.iloc[:-2], SWING_LOOKBACK)
        mss_confirmed = last_close < swing_low
        return {
            "symbol"       : symbol,
            "direction"    : "BEARISH",
            "swing_level"  : swing_low,
            "swing_time"   : swing_time,
            "break_candle" : last_time,
            "break_close"  : last_close,
            "confirmed"    : mss_confirmed
        }

    return None

# --- PRINT MSS RESULT ---
def print_mss(result):
    if result is None:
        return
    status = "✅ CONFIRMED" if result['confirmed'] else "⏳ NOT YET"
    print(f"\n  MSS {result['direction']} — {status}")
    print(f"    Swing Level  : {result['swing_level']}")
    print(f"    Swing Time   : {result['swing_time']}")
    print(f"    Break Candle : {result['break_candle']}")
    print(f"    Close        : {result['break_close']}")

# --- RUN FULL MSS SCAN ---
def scan_mss(symbol, sweeps):
    print(f"\n{'=' * 55}")
    print(f"  MSS DETECTOR — {symbol}")
    print(f"{'=' * 55}")

    if not sweeps:
        print(f"  No sweeps to check MSS for.")
        return []

    confirmed_setups = []

    for sweep in sweeps:
        print(f"\n  Checking MSS after {sweep['type']} at {sweep['level_name']} ({sweep['level']})")
        result = detect_mss(symbol, "sell_side" if sweep['type'] == "SELL_SIDE_SWEEP" else "buy_side")
        print_mss(result)

        if result and result['confirmed']:
            confirmed_setups.append({
                "symbol"   : symbol,
                "direction": result['direction'],
                "sweep"    : sweep,
                "mss"      : result
            })
            print(f"\n  🚨 SETUP CONFIRMED — {result['direction']} on {symbol}")
            print(f"     Sweep  : {sweep['level_name']} at {sweep['level']}")
            print(f"     MSS    : Close {result['break_close']} broke swing {result['swing_level']}")

    return confirmed_setups

# --- RUN TEST ---
if __name__ == "__main__":
    from sweep_detector import detect_sweeps
    if connect():
        for symbol in ["XAUUSD.sim", "EURUSD.sim", "GBPUSD.sim", "AUDUSD.sim"]:
            sweeps = detect_sweeps(symbol)
            scan_mss(symbol, sweeps)
        disconnect()