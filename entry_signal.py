# entry_signal.py
# Ghost In The Machine -- Entry Signal Engine
# Scans all pairs 24/5 -- Sunday 21:00 UTC to Friday 19:00 UTC
# Market hours gate handled by main.py

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

from datetime import datetime, timezone
from mt5_connection import connect, disconnect
from liquidity_levels import scan_liquidity
from sweep_detector import detect_sweeps
from mss_detector import detect_mss
from dealing_range import build_dealing_range
from zone_detector import detect_fvgs, detect_obs
from ltf_confirmation import confirm_ltf_entry
from config import ALL_SYMBOLS, HTF

# -----------------------------------------
# BIAS FROM DEALING RANGE
# -----------------------------------------
def get_bias(dealing_range):
    if not dealing_range:
        return None
    mid  = (dealing_range["range_high"] + dealing_range["range_low"]) / 2
    last = dealing_range.get("current_price", mid)
    return "BULLISH" if last < mid else "BEARISH"

# -----------------------------------------
# MAIN SIGNAL FUNCTION
# -----------------------------------------
def check_entry_signal(symbol):
    print(f"\n{'=' * 55}")
    print(f"  SCANNING {symbol}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'=' * 55}")

    # Step 1 -- Liquidity
    liquidity = scan_liquidity(symbol)
    if not liquidity:
        print(f"  No liquidity levels -- skipping")
        return None
    print(f"  Liquidity levels found")

    # Step 2 -- Sweeps
    sweeps = detect_sweeps(symbol)
    if not sweeps:
        print(f"  No sweep detected -- skipping")
        return None
    sweep = sweeps[-1]
    print(f"  Sweep DETECTED: {sweep.get('type')} at {sweep.get('level_name')} ({sweep.get('level')})")

    # Step 3 -- MSS
    sweep_dir = "sell_side" if sweep.get("type") == "SELL_SIDE_SWEEP" else "buy_side"
    mss = detect_mss(symbol, sweep_dir)
    if not mss or not mss.get("confirmed"):
        print(f"  No MSS confirmed -- skipping")
        return None
    print(f"  MSS CONFIRMED: {mss.get('direction')} at {mss.get('break_close')}")

    # Step 4 -- Dealing Range
    mss_direction = mss.get("direction", "BULLISH").upper()
    dr = build_dealing_range(symbol, mss_direction)
    if not dr:
        print(f"  No dealing range -- skipping")
        return None
    bias = get_bias(dr)
    if not bias:
        print(f"  Could not determine bias -- skipping")
        return None
    print(f"  Bias: {bias} | Range: {dr['range_low']} -- {dr['range_high']}")
    print(f"  Entry Zone: {dr['entry_zone_low']} -- {dr['entry_zone_high']}")

    # Step 5 -- Zones
    equilibrium = dr["fibs"]["50%"]
    fvgs  = detect_fvgs(symbol, bias)
    obs   = detect_obs(symbol, bias, equilibrium)
    zones = (fvgs or []) + (obs or [])
    if not zones:
        print(f"  No FVG or OB zones -- skipping")
        return None
    print(f"  Zones found: {len(zones)} ({len(fvgs)} FVG | {len(obs)} OB)")

    # Step 6 -- LTF Confirmation
    ltf = confirm_ltf_entry(symbol, direction=bias)
    if not ltf:
        print(f"  No LTF confirmation -- skipping")
        return None
    print(f"  LTF CONFIRMED: {ltf}")

    signal = {
        "symbol"    : symbol,
        "direction" : bias,
        "sweep"     : sweep,
        "mss"       : mss,
        "zones"     : zones,
        "ltf"       : ltf,
        "sl"        : dr.get("entry_zone_low") if bias == "BULLISH" else dr.get("entry_zone_high"),
        "tp"        : dr.get("range_high") if bias == "BULLISH" else dr.get("range_low"),
        "timestamp" : datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    print(f"\n  *** ENTRY SIGNAL CONFIRMED ***")
    print(f"  Symbol: {symbol} | Direction: {bias} | SL: {signal['sl']} | TP: {signal['tp']}")
    print(f"{'=' * 55}\n")
    return signal

# -----------------------------------------
# RUN ALL SYMBOLS
# -----------------------------------------
def scan_all():
    signals = []
    for symbol in ALL_SYMBOLS:
        result = check_entry_signal(symbol)
        if result:
            signals.append(result)
    return signals

if __name__ == "__main__":
    if connect():
        signals = scan_all()
        print(f"\n  {len(signals)} SIGNAL(S) READY FOR EXECUTION" if signals else "\n  No signals this scan -- bot is watching")
        disconnect()
