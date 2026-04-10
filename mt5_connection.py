# ============================================================
# THE GHOST IN THE MACHINE
# File: mt5_connection.py
# Purpose: Connect to OANDA MT5 and pull price data
# ============================================================

import MetaTrader5 as mt5
import pandas as pd

# --- SYMBOLS ---
XAUUSD  = "XAUUSD.sim"
EURUSD  = "EURUSD.sim"
GBPUSD  = "GBPUSD.sim"
AUDUSD  = "AUDUSD.sim"
EURGBP  = "EURGBP.sim"
DXY     = None  # Not available on OANDA — loaded from TradingView CSV

ALL_SYMBOLS = [XAUUSD, EURUSD, GBPUSD, AUDUSD, EURGBP]

# --- CONNECT TO MT5 ---
def connect():
    if not mt5.initialize():
        print("MT5 connection FAILED:", mt5.last_error())
        return False
    info = mt5.account_info()
    if info is None:
        print("Account info FAILED:", mt5.last_error())
        return False
    # Enable all symbols
    for symbol in ALL_SYMBOLS:
        mt5.symbol_select(symbol, True)
    print("=" * 50)
    print("  GHOST IN THE MACHINE — CONNECTED")
    print("=" * 50)
    print(f"  Broker  : {info.server}")
    print(f"  Balance : ${info.balance:,.2f}")
    print(f"  Equity  : ${info.equity:,.2f}")
    print("=" * 50)
    return True

# --- PULL CANDLE DATA ---
def get_candles(symbol, timeframe, count):
    bars = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if bars is None or len(bars) == 0:
        print(f"Failed to get data for {symbol} — error: {mt5.last_error()}")
        return None
    df = pd.DataFrame(bars)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df[['open', 'high', 'low', 'close', 'tick_volume']]

# --- DISCONNECT ---
def disconnect():
    mt5.shutdown()
    print("\nDisconnected from MT5.")

# --- RUN TEST ---
if __name__ == "__main__":
    if connect():
        print("\nTesting all symbols...\n")
        for symbol in ALL_SYMBOLS:
            df = get_candles(symbol, mt5.TIMEFRAME_H1, 3)
            if df is not None:
                last = df.iloc[-1]
                print(f"  {symbol:<15} | Close: {last['close']:.5f} ✅")
            else:
                print(f"  {symbol:<15} | ❌ No data")
        print("\nXAUUSD — Last 10 x 1H Candles:")
        df = get_candles(XAUUSD, mt5.TIMEFRAME_H1, 10)
        if df is not None:
            print(df.to_string())
        disconnect()