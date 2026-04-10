# ============================================================
# THE GHOST IN THE MACHINE
# File: dealing_range.py
# Purpose: Build the dealing range after MSS confirmation
#          Calculate equilibrium, discount and premium zones
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from mt5_connection import connect, get_candles, disconnect
from liquidity_levels import scan_liquidity

# --- SETTINGS ---
FIBONACCI_LEVELS = {
    "0%"  : 0.00,
    "25%" : 0.25,
    "50%" : 0.50,  # Equilibrium
    "62%" : 0.618,
    "70%" : 0.70,
    "79%" : 0.79,
    "100%": 1.00
}

# --- BUILD DEALING RANGE ---
def build_dealing_range(symbol, direction, sweep_candle_time=None):
    """
    direction: 'BULLISH' = range low to high, entry in discount
               'BEARISH' = range high to low, entry in premium
    """
    df = get_candles(symbol, mt5.TIMEFRAME_H1, 50)
    if df is None:
        return None

    levels = scan_liquidity(symbol)
    if levels is None:
        return None

    current_price = levels["current"]

    if direction == "BULLISH":
        # Range Low  = most recent swing low (after sweep)
        # Range High = most recent swing high before retracement
        range_low  = df['low'].iloc[-20:].min()
        range_high = df['high'].iloc[-20:].max()

        # Use session levels to refine if available
        if levels["NY_L"] and levels["NY_L"] < current_price:
            range_low = min(range_low, levels["NY_L"])
        if levels["London_H"] and levels["London_H"] > range_low:
            range_high = min(range_high, levels["London_H"])

    elif direction == "BEARISH":
        # Range High = most recent swing high (after sweep)
        # Range Low  = most recent swing low before retracement
        range_high = df['high'].iloc[-20:].max()
        range_low  = df['low'].iloc[-20:].min()

        # Use session levels to refine if available
        if levels["NY_H"] and levels["NY_H"] > current_price:
            range_high = max(range_high, levels["NY_H"])
        if levels["London_L"] and levels["London_L"] < range_high:
            range_low = max(range_low, levels["London_L"])
    else:
        return None

    range_size = range_high - range_low
    if range_size <= 0:
        return None

    # --- CALCULATE FIBONACCI LEVELS ---
    fibs = {}
    for name, ratio in FIBONACCI_LEVELS.items():
        if direction == "BULLISH":
            # Retracement from high down to low
            fibs[name] = round(range_high - (range_size * ratio), 5)
        else:
            # Retracement from low up to high
            fibs[name] = round(range_low + (range_size * ratio), 5)

    # --- DEFINE ENTRY ZONE ---
    if direction == "BULLISH":
        entry_zone_high = fibs["50%"]   # Equilibrium
        entry_zone_low  = fibs["79%"]   # Deep discount
        in_entry_zone   = entry_zone_low <= current_price <= entry_zone_high
    else:
        entry_zone_low  = fibs["50%"]   # Equilibrium
        entry_zone_high = fibs["79%"]   # Deep premium
        in_entry_zone   = entry_zone_low <= current_price <= entry_zone_high

    return {
        "symbol"         : symbol,
        "direction"      : direction,
        "range_high"     : round(range_high, 5),
        "range_low"      : round(range_low, 5),
        "range_size"     : round(range_size, 5),
        "fibs"           : fibs,
        "entry_zone_high": entry_zone_high,
        "entry_zone_low" : entry_zone_low,
        "current_price"  : current_price,
        "in_entry_zone"  : in_entry_zone
    }

# --- PRINT DEALING RANGE ---
def print_dealing_range(dr):
    if dr is None:
        print("  Could not build dealing range.")
        return

    print(f"\n{'=' * 55}")
    print(f"  DEALING RANGE — {dr['symbol']} — {dr['direction']}")
    print(f"{'=' * 55}")
    print(f"\n  Range High : {dr['range_high']}")
    print(f"  Range Low  : {dr['range_low']}")
    print(f"  Range Size : {dr['range_size']}")

    print(f"\n  FIBONACCI LEVELS:")
    for name, level in dr['fibs'].items():
        marker = " ← Equilibrium" if name == "50%" else ""
        print(f"    {name:>5}  :  {level}{marker}")

    print(f"\n  ENTRY ZONE ({dr['direction']}):")
    print(f"    High : {dr['entry_zone_high']}  (50% — Equilibrium)")
    print(f"    Low  : {dr['entry_zone_low']}  (79% — Deep discount/premium)")

    status = "✅ IN ZONE" if dr['in_entry_zone'] else "⏳ NOT IN ZONE YET"
    print(f"\n  Current Price : {dr['current_price']}")
    print(f"  Zone Status   : {status}")

# --- RUN TEST ---
if __name__ == "__main__":
    if connect():
        for symbol, direction in [
            ("XAUUSD.sim", "BULLISH"),
            ("EURUSD.sim", "BULLISH"),
            ("GBPUSD.sim", "BULLISH"),
            ("AUDUSD.sim", "BULLISH"),
        ]:
            dr = build_dealing_range(symbol, direction)
            print_dealing_range(dr)
        disconnect()