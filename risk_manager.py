# risk_manager.py
# Ghost In The Machine -- Risk Manager

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

import MetaTrader5 as mt5
from mt5_connection import connect, disconnect
from config import RISK_FOREX_PCT, RISK_GOLD_PCT, GOLD

def get_pip_value(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    if any(g in symbol for g in GOLD):
        pip_size = info.point
    elif "JPY" in symbol:
        pip_size = info.point * 100
    else:
        pip_size = info.point * 10
    return (info.trade_tick_value / info.trade_tick_size) * pip_size

def get_account_balance():
    account = mt5.account_info()
    if account is None:
        return None
    return account.balance

def calculate_lot_size(symbol, sl_pips):
    balance = get_account_balance()
    if balance is None:
        return None
    is_gold = any(g in symbol for g in GOLD)
    risk_pct = RISK_GOLD_PCT if is_gold else RISK_FOREX_PCT
    risk_amount = balance * risk_pct
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    pip_value = get_pip_value(symbol)
    if pip_value is None or pip_value == 0:
        return None
    lot_size = risk_amount / (sl_pips * pip_value)
    lot_size = max(info.volume_min, min(lot_size, info.volume_max))
    step = info.volume_step
    lot_size = round(round(lot_size / step) * step, 2)
    print(f"  [RISK] {symbol}")
    print(f"         Balance     : ${balance:,.2f}")
    print(f"         Risk PCT    : {risk_pct * 100}%")
    print(f"         Risk Amount : ${risk_amount:,.2f}")
    print(f"         SL Pips     : {sl_pips}")
    print(f"         Pip Value   : {pip_value:.4f}")
    print(f"         Lot Size    : {lot_size}")
    return lot_size

def get_sl_pips(symbol, entry_price, sl_price):
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    if any(g in symbol for g in GOLD):
        pip = info.point
    elif "JPY" in symbol:
        pip = info.point * 100
    else:
        pip = info.point * 10
    sl_pips = abs(entry_price - sl_price) / pip
    return round(sl_pips, 1)

if __name__ == "__main__":
    if connect():
        print("\n  GHOST IN THE MACHINE -- RISK MANAGER TEST")
        tests = [
            ("EURUSD.sim", 1.08500, 1.08200),
            ("XAUUSD.sim", 2980.00, 2970.00),
            ("GBPUSD.sim", 1.27000, 1.26600),
            ("AUDUSD.sim", 0.63000, 0.62700),
        ]
        for symbol, entry, sl in tests:
            sl_pips = get_sl_pips(symbol, entry, sl)
            if sl_pips:
                lot = calculate_lot_size(symbol, sl_pips)
                print(f"  --> Final lot size for {symbol}: {lot}\n")
       