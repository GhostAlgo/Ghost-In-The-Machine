# trade_executor.py
# Ghost In The Machine -- Trade Executor
# Takes a signal, calculates lot size, places trade on MT5 with SL and TP

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

import MetaTrader5 as mt5
from mt5_connection import connect, disconnect
from risk_manager import calculate_lot_size, get_sl_pips
from config import GOLD

# ─────────────────────────────────────────
# TP MULTIPLIER -- 2:1 REWARD TO RISK
# ─────────────────────────────────────────
TP_MULTIPLIER = 2.0

def get_current_price(symbol, direction):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"  [EXEC] Could not get tick for {symbol}")
        return None
    if direction == "bullish":
        return tick.ask
    else:
        return tick.bid

def calculate_sl_tp(symbol, direction, entry_price, zones):
    info = mt5.symbol_info(symbol)
    if info is None:
        return None, None

    is_gold = any(g in symbol for g in GOLD)
    pip = info.point if is_gold else info.point * 10

    # SL goes below the nearest zone low (bullish) or above zone high (bearish)
    if zones:
        zone = zones[0]
        if direction == "bullish":
            sl_price = zone.get("low", entry_price - pip * 20)
        else:
            sl_price = zone.get("high", entry_price + pip * 20)
    else:
        if direction == "bullish":
            sl_price = entry_price - pip * 20
        else:
            sl_price = entry_price + pip * 20

    sl_distance = abs(entry_price - sl_price)
    tp_distance = sl_distance * TP_MULTIPLIER

    if direction == "bullish":
        tp_price = entry_price + tp_distance
    else:
        tp_price = entry_price - tp_distance

    digits = info.digits
    sl_price = round(sl_price, digits)
    tp_price = round(tp_price, digits)

    return sl_price, tp_price

def place_trade(signal):
    symbol    = signal["symbol"]
    direction = signal["direction"]
    zones     = signal.get("zones", [])

    print(f"\n  [EXEC] Preparing trade for {symbol} -- {direction.upper()}")

    entry_price = get_current_price(symbol, direction)
    if entry_price is None:
        print(f"  [EXEC] Could not get entry price -- aborting")
        return None

    sl_price, tp_price = calculate_sl_tp(symbol, direction, entry_price, zones)
    if sl_price is None:
        print(f"  [EXEC] Could not calculate SL/TP -- aborting")
        return None

    sl_pips = get_sl_pips(symbol, entry_price, sl_price)
    if not sl_pips or sl_pips <= 0:
        print(f"  [EXEC] Invalid SL pips ({sl_pips}) -- aborting")
        return None

    lot_size = calculate_lot_size(symbol, sl_pips)
    if lot_size is None:
        print(f"  [EXEC] Could not calculate lot size -- aborting")
        return None

    order_type = mt5.ORDER_TYPE_BUY if direction == "bullish" else mt5.ORDER_TYPE_SELL

    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    symbol,
        "volume":    lot_size,
        "type":      order_type,
        "price":     entry_price,
        "sl":        sl_price,
        "tp":        tp_price,
        "deviation": 20,
        "magic":     20250101,
        "comment":   "GhostInTheMachine",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    print(f"  [EXEC] Symbol    : {symbol}")
    print(f"  [EXEC] Direction : {direction.upper()}")
    print(f"  [EXEC] Entry     : {entry_price}")
    print(f"  [EXEC] SL        : {sl_price}")
    print(f"  [EXEC] TP        : {tp_price}")
    print(f"  [EXEC] Lots      : {lot_size}")
    print(f"  [EXEC] SL Pips   : {sl_pips}")

    result = mt5.order_send(request)

    if result is None:
        print(f"  [EXEC] order_send returned None -- check MT5 connection")
        return None

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"\n  *** TRADE PLACED SUCCESSFULLY ***")
        print(f"  Order Ticket : {result.order}")
        print(f"  Volume       : {result.volume}")
        print(f"  Price        : {result.price}")
        return result
    else:
        print(f"\n  [EXEC] Trade FAILED -- retcode: {result.retcode}")
        print(f"  [EXEC] Comment: {result.comment}")
        return None

# ─────────────────────────────────────────
# TEST -- SIMULATED SIGNAL (NO REAL TRADE)
# ─────────────────────────────────────────
if __name__ == "__main__":
    if connect():
        print("\n  GHOST IN THE MACHINE -- TRADE EXECUTOR TEST")
        print("  (Dry run -- checking signal flow only)\n")

        test_signal = {
            "symbol":    "EURUSD.sim",
            "direction": "bullish",
            "zones": [
                {"low": 1.08100, "high": 1.08300}
            ],
            "timestamp": "2026-04-07 14:00:00 UTC"
        }

        entry = get_current_price(test_signal["symbol"], test_signal["direction"])
        sl, tp = calculate_sl_tp(
            test_signal["symbol"],
            test_signal["direction"],
            entry,
            test_signal["zones"]
        )
        sl_pips = get_sl_pips(test_signal["symbol"], entry, sl)
        lots = calculate_lot_size(test_signal["symbol"], sl_pips)

        print(f"  Symbol    : {test_signal['symbol']}")
        print(f"  Direction : {test_signal['direction'].upper()}")
        print(f"  Entry     : {entry}")
        print(f"  SL        : {sl}")
        print(f"  TP        : {tp}")
        print(f"  SL Pips   : {sl_pips}")
        print(f"  Lot Size  : {lots}")
        print(f"\n  Dry run complete -- trade_executor.py is ready")
        print(f"  To place real trades call place_trade(signal) from entry_signal.py")

        disconnect()