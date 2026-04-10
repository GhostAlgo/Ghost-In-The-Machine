# ============================================================
# THE GHOST IN THE MACHINE
# File: zone_detector.py
# Purpose: Detect FVGs and Order Blocks on 1H
#          Final condition before entry signal
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from mt5_connection import connect, get_candles, disconnect
from dealing_range import build_dealing_range

# --- SETTINGS ---
OB_DISTANCE_FOREX = 0.0030   # 30 pips
OB_DISTANCE_GOLD  = 0.90     # 90 points

def is_gold(symbol):
    return "XAU" in symbol

def get_ob_distance(symbol):
    return OB_DISTANCE_GOLD if is_gold(symbol) else OB_DISTANCE_FOREX

# --- DETECT FAIR VALUE GAPS (FVG) ---
def detect_fvgs(symbol, direction, lookback=20):
    df = get_candles(symbol, mt5.TIMEFRAME_H1, lookback)
    if df is None or len(df) < 3:
        return []

    fvgs = []
    for i in range(1, len(df) - 1):
        c1 = df.iloc[i - 1]  # Candle 1
        c2 = df.iloc[i]      # Candle 2 (impulse)
        c3 = df.iloc[i + 1]  # Candle 3

        if direction == "BULLISH":
            # Bullish FVG (SIBI): gap between c1 high and c3 low
            if c3['low'] > c1['high']:
                fvgs.append({
                    "type"     : "BULLISH_FVG",
                    "high"     : c3['low'],
                    "low"      : c1['high'],
                    "time"     : df.index[i],
                    "mitigated": False
                })

        elif direction == "BEARISH":
            # Bearish FVG (BISI): gap between c1 low and c3 high
            if c3['high'] < c1['low']:
                fvgs.append({
                    "type"     : "BEARISH_FVG",
                    "high"     : c1['low'],
                    "low"      : c3['high'],
                    "time"     : df.index[i],
                    "mitigated": False
                })

    # Check mitigation — has price returned to fill the FVG?
    current_candle = df.iloc[-1]
    for fvg in fvgs:
        if direction == "BULLISH":
            if current_candle['low'] <= fvg['low']:
                fvg['mitigated'] = True
        elif direction == "BEARISH":
            if current_candle['high'] >= fvg['high']:
                fvg['mitigated'] = True

    # Return only unmitigated FVGs
    return [f for f in fvgs if not f['mitigated']]

# --- DETECT ORDER BLOCKS (OB) ---
def detect_obs(symbol, direction, equilibrium, lookback=20):
    df = get_candles(symbol, mt5.TIMEFRAME_H1, lookback)
    if df is None or len(df) < 3:
        return []

    ob_distance = get_ob_distance(symbol)
    obs = []

    for i in range(len(df) - 2):
        c = df.iloc[i]
        next_c = df.iloc[i + 1]

        if direction == "BULLISH":
            # Last bearish candle before bullish impulse
            if c['close'] < c['open']:  # Bearish candle
                if next_c['close'] > next_c['open']:  # Followed by bullish
                    ob_mid = (c['high'] + c['low']) / 2
                    # Must be within distance of equilibrium
                    if abs(ob_mid - equilibrium) <= ob_distance * 3:
                        obs.append({
                            "type"          : "BULLISH_OB",
                            "high"          : c['high'],
                            "low"           : c['low'],
                            "mean_threshold": round((c['high'] + c['low']) / 2, 5),
                            "time"          : df.index[i]
                        })

        elif direction == "BEARISH":
            # Last bullish candle before bearish impulse
            if c['close'] > c['open']:  # Bullish candle
                if next_c['close'] < next_c['open']:  # Followed by bearish
                    ob_mid = (c['high'] + c['low']) / 2
                    if abs(ob_mid - equilibrium) <= ob_distance * 3:
                        obs.append({
                            "type"          : "BEARISH_OB",
                            "high"          : c['high'],
                            "low"           : c['low'],
                            "mean_threshold": round((c['high'] + c['low']) / 2, 5),
                            "time"          : df.index[i]
                        })

    return obs

# --- CHECK IF PRICE IS INSIDE A ZONE ---
def price_in_zone(price, zone_high, zone_low):
    return zone_low <= price <= zone_high

# --- FULL ZONE SCAN ---
def scan_zones(symbol, direction):
    print(f"\n{'=' * 55}")
    print(f"  ZONE DETECTOR — {symbol} — {direction}")
    print(f"{'=' * 55}")

    # Build dealing range first
    dr = build_dealing_range(symbol, direction)
    if dr is None:
        print("  Could not build dealing range.")
        return None

    current_price = dr['current_price']
    equilibrium   = dr['fibs']['50%']

    print(f"\n  Current Price : {current_price}")
    print(f"  Equilibrium   : {equilibrium}")
    print(f"  Entry Zone    : {dr['entry_zone_low']} – {dr['entry_zone_high']}")
    print(f"  In Zone       : {'✅ YES' if dr['in_entry_zone'] else '⏳ NO'}")

    if not dr['in_entry_zone']:
        print(f"\n  Price not in entry zone — skipping FVG/OB scan.")
        return None

    # Scan for FVGs
    print(f"\n  FAIR VALUE GAPS (1H — unmitigated):")
    fvgs = detect_fvgs(symbol, direction)
    fvgs_in_zone = []
    for fvg in fvgs:
        in_zone = price_in_zone(fvg['low'], dr['entry_zone_high'], dr['entry_zone_low']) or \
                  price_in_zone(fvg['high'], dr['entry_zone_high'], dr['entry_zone_low'])
        marker = "✅ IN ZONE" if in_zone else "— outside zone"
        print(f"    FVG {fvg['type']}: {fvg['low']} – {fvg['high']} | {fvg['time']} | {marker}")
        if in_zone:
            fvgs_in_zone.append(fvg)

    if not fvgs:
        print(f"    No unmitigated FVGs found.")

    # Scan for OBs
    print(f"\n  ORDER BLOCKS (1H — in zone):")
    obs = detect_obs(symbol, direction, equilibrium)
    obs_in_zone = []
    for ob in obs:
        in_zone = price_in_zone(ob['low'], dr['entry_zone_high'], dr['entry_zone_low']) or \
                  price_in_zone(ob['high'], dr['entry_zone_high'], dr['entry_zone_low'])
        marker = "✅ IN ZONE" if in_zone else "— outside zone"
        print(f"    OB {ob['type']}: {ob['low']} – {ob['high']} | Mean: {ob['mean_threshold']} | {marker}")
        if in_zone:
            obs_in_zone.append(ob)

    if not obs:
        print(f"    No order blocks found.")

    # --- ENTRY SIGNAL ASSESSMENT ---
    print(f"\n  ENTRY SIGNAL ASSESSMENT:")
    has_fvg = len(fvgs_in_zone) > 0
    has_ob  = len(obs_in_zone) > 0
    in_price_in_fvg = any(price_in_zone(current_price, f['high'], f['low']) for f in fvgs_in_zone)
    in_price_in_ob  = any(price_in_zone(current_price, o['high'], o['low']) for o in obs_in_zone)

    print(f"    FVG in zone      : {'✅' if has_fvg else '❌'}")
    print(f"    OB in zone       : {'✅' if has_ob else '❌'}")
    print(f"    Price in FVG     : {'✅' if in_price_in_fvg else '❌'}")
    print(f"    Price in OB      : {'✅' if in_price_in_ob else '❌'}")

    # Minimum: FVG or OB in zone + price in entry zone
    if (has_fvg or has_ob) and dr['in_entry_zone']:
        print(f"\n  🚨 ENTRY ZONE ACTIVE — Awaiting LTF confirmation")
    else:
        print(f"\n  ⏳ No valid entry zone yet.")

    return {
        "symbol"      : symbol,
        "direction"   : direction,
        "dealing_range": dr,
        "fvgs_in_zone": fvgs_in_zone,
        "obs_in_zone" : obs_in_zone,
        "entry_active": (has_fvg or has_ob) and dr['in_entry_zone']
    }

# --- RUN TEST ---
if __name__ == "__main__":
    if connect():
        for symbol, direction in [
            ("XAUUSD.sim", "BULLISH"),
            ("EURUSD.sim", "BULLISH"),
            ("GBPUSD.sim", "BULLISH"),
            ("AUDUSD.sim", "BULLISH"),
        ]:
            scan_zones(symbol, direction)
        disconnect()