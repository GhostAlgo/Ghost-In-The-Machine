# ============================================================
# THE GHOST IN THE MACHINE
# File: sweep_detector.py
# Purpose: Detect when price sweeps a key liquidity level
#          Only flags RELEVANT levels near current price
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from mt5_connection import connect, get_candles, disconnect
from liquidity_levels import scan_liquidity

# --- SETTINGS ---
SWEEP_LOOKBACK    = 3    # Recent candles to check for sweep
PROXIMITY_FACTOR  = 0.25 # Only watch levels within 25% of 5-day range

# --- GET 5 DAY RANGE ---
def get_5day_range(symbol):
    df = get_candles(symbol, mt5.TIMEFRAME_D1, 6)
    if df is None or len(df) < 5:
        return None
    last5 = df.iloc[-6:-1]
    return last5['high'].max() - last5['low'].min()

# --- CHECK IF LEVEL IS RELEVANT TO CURRENT PRICE ---
def is_relevant(level, current_price, side, proximity):
    if level is None:
        return False
    if side == "sell_side":
        # Level must be BELOW current price but within proximity
        # Price has not swept it yet — it's still ahead
        return (level < current_price) and (current_price - level <= proximity)
    if side == "buy_side":
        # Level must be ABOVE current price but within proximity
        # Price has not swept it yet — it's still ahead
        return (level > current_price) and (level - current_price <= proximity)
    return False

# --- CHECK IF A LEVEL WAS SWEPT BY RECENT CANDLE ---
def is_swept(candle_low, candle_high, level, direction):
    if direction == "sell_side":
        return candle_low < level
    if direction == "buy_side":
        return candle_high > level
    return False

# --- DETECT SWEEPS FOR A SYMBOL ---
def detect_sweeps(symbol):
    print(f"\n{'=' * 55}")
    print(f"  SWEEP DETECTOR — {symbol}")
    print(f"{'=' * 55}")

    levels = scan_liquidity(symbol)
    if levels is None:
        print("  No levels found.")
        return []

    current_price = levels["current"]
    five_day      = get_5day_range(symbol)

    if current_price is None or five_day is None:
        print("  Could not get current price or range.")
        return []

    proximity = five_day * PROXIMITY_FACTOR

    print(f"\n  Current Price : {round(current_price, 5)}")
    print(f"  Watch Zone    : ±{round(proximity, 5)} from current price")

    # --- BUILD SELL-SIDE LEVEL LIST (below current price) ---
    sell_side_candidates = {
        "PDL"          : levels["PDL"],
        "PWL"          : levels["PWL"],
        "Asia_L"       : levels["Asia_L"],
        "London_L"     : levels["London_L"],
        "NY_L"         : levels["NY_L"],
        "Prev_Asia_L"  : levels["Prev_Asia_L"],
        "Prev_London_L": levels["Prev_London_L"],
        "Prev_NY_L"    : levels["Prev_NY_L"],
    }
    for eql in levels["EQL"][:5]:
        sell_side_candidates[f"EQL_{round(eql,3)}"] = eql

    # --- BUILD BUY-SIDE LEVEL LIST (above current price) ---
    buy_side_candidates = {
        "PDH"          : levels["PDH"],
        "PWH"          : levels["PWH"],
        "Asia_H"       : levels["Asia_H"],
        "London_H"     : levels["London_H"],
        "NY_H"         : levels["NY_H"],
        "Prev_Asia_H"  : levels["Prev_Asia_H"],
        "Prev_London_H": levels["Prev_London_H"],
        "Prev_NY_H"    : levels["Prev_NY_H"],
    }
    for eqh in levels["EQH"][-5:]:
        buy_side_candidates[f"EQH_{round(eqh,3)}"] = eqh

    # --- GET RECENT CANDLES ---
    df = get_candles(symbol, mt5.TIMEFRAME_H1, SWEEP_LOOKBACK + 1)
    if df is None:
        return []

    recent      = df.iloc[-2]
    candle_high = recent['high']
    candle_low  = recent['low']
    candle_time = df.index[-2]

    print(f"\n  Last closed candle : {candle_time}")
    print(f"  High: {candle_high}  |  Low: {candle_low}")

    sweeps_found = []

    # --- CHECK SELL-SIDE ---
    print(f"\n  SELL-SIDE LEVELS IN WATCH ZONE (potential longs):")
    found_any_sell = False
    for name, level in sell_side_candidates.items():
        if is_relevant(level, current_price, "sell_side", proximity):
            found_any_sell = True
            swept = is_swept(candle_low, candle_high, level, "sell_side")
            status = "✅ SWEPT" if swept else "👁 WATCHING"
            print(f"    {status} — {name} at {level}")
            if swept:
                sweeps_found.append({
                    "symbol"    : symbol,
                    "type"      : "SELL_SIDE_SWEEP",
                    "level_name": name,
                    "level"     : level,
                    "candle_time": candle_time,
                    "direction" : "LONG"
                })
    if not found_any_sell:
        print(f"    No sell-side levels in watch zone")

    # --- CHECK BUY-SIDE ---
    print(f"\n  BUY-SIDE LEVELS IN WATCH ZONE (potential shorts):")
    found_any_buy = False
    for name, level in buy_side_candidates.items():
        if is_relevant(level, current_price, "buy_side", proximity):
            found_any_buy = True
            swept = is_swept(candle_low, candle_high, level, "buy_side")
            status = "✅ SWEPT" if swept else "👁 WATCHING"
            print(f"    {status} — {name} at {level}")
            if swept:
                sweeps_found.append({
                    "symbol"    : symbol,
                    "type"      : "BUY_SIDE_SWEEP",
                    "level_name": name,
                    "level"     : level,
                    "candle_time": candle_time,
                    "direction" : "SHORT"
                })
    if not found_any_buy:
        print(f"    No buy-side levels in watch zone")

    print(f"\n  ── Summary ──")
    if not sweeps_found:
        print(f"  No sweeps on last candle. Levels above are being watched.")
    else:
        print(f"  {len(sweeps_found)} sweep(s) detected — monitoring for MSS.")
        for s in sweeps_found:
            print(f"    → {s['direction']} setup — {s['level_name']} at {s['level']}")

    return sweeps_found

# --- RUN TEST ---
if __name__ == "__main__":
    if connect():
        detect_sweeps("XAUUSD.sim")
        detect_sweeps("EURUSD.sim")
        disconnect()