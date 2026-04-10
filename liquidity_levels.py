# ============================================================
# THE GHOST IN THE MACHINE
# File: liquidity_levels.py
# Purpose: Scan and identify all key liquidity levels
# ============================================================

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
from mt5_connection import connect, get_candles, disconnect

# --- SETTINGS ---
EQH_EQL_THRESHOLD_FOREX = 0.0010
EQH_EQL_THRESHOLD_GOLD  = 0.50
EQL_PROXIMITY_FACTOR    = 0.25  # 25% of 5-day range

# --- HELPERS ---
def is_gold(symbol):
    return "XAU" in symbol

def get_threshold(symbol):
    return EQH_EQL_THRESHOLD_GOLD if is_gold(symbol) else EQH_EQL_THRESHOLD_FOREX

def get_current_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    return (tick.bid + tick.ask) / 2 if tick else None

def get_5day_range(symbol):
    df = get_candles(symbol, mt5.TIMEFRAME_D1, 6)
    if df is None or len(df) < 5:
        return None
    last5 = df.iloc[-6:-1]
    range_val = last5['high'].max() - last5['low'].min()
    if "XAU" in symbol:
        return round(range_val, 2)
    return round(range_val * 10000, 1)
# --- PREVIOUS WEEK HIGH / LOW ---
def get_pwh_pwl(symbol):
    df = get_candles(symbol, mt5.TIMEFRAME_W1, 3)
    if df is None:
        return None, None
    last_week = df.iloc[-2]
    return last_week['high'], last_week['low']

# --- PREVIOUS DAY HIGH / LOW ---
def get_pdh_pdl(symbol):
    df = get_candles(symbol, mt5.TIMEFRAME_D1, 3)
    if df is None:
        return None, None
    yesterday = df.iloc[-2]
    return yesterday['high'], yesterday['low']

# --- SESSION HIGH / LOW FROM 1H DATA ---
def get_session_hl(symbol, session_name, lookback_days=2):
    df = get_candles(symbol, mt5.TIMEFRAME_H1, 24 * lookback_days)
    if df is None:
        return None, None

    # Session hours in UTC (OANDA uses UTC)
    sessions = {
        "asia"  : (0, 3),    # 8PM–11PM EST = 00:00–03:00 UTC
        "london": (7, 10),   # 2AM–5AM EST  = 07:00–10:00 UTC
        "ny"    : (12, 15),  # 7AM–10AM EST = 12:00–15:00 UTC
    }

    if session_name not in sessions:
        return None, None

    start_hour, end_hour = sessions[session_name]
    mask = (df.index.hour >= start_hour) & (df.index.hour < end_hour)
    session_df = df[mask]

    if session_df.empty:
        return None, None

    return session_df['high'].max(), session_df['low'].min()

# --- PREVIOUS SESSION HIGH / LOW (one day back) ---
def get_prev_session_hl(symbol, session_name):
    df = get_candles(symbol, mt5.TIMEFRAME_H1, 48)
    if df is None:
        return None, None

    sessions = {
        "asia"  : (0, 3),
        "london": (7, 10),
        "ny"    : (12, 15),
    }

    if session_name not in sessions:
        return None, None

    start_hour, end_hour = sessions[session_name]

    # Get all session candles then split into days
    mask = (df.index.hour >= start_hour) & (df.index.hour < end_hour)
    session_df = df[mask]

    if len(session_df) < 2:
        return None, None

    # Get unique dates and use second most recent
    dates = session_df.index.normalize().unique()
    if len(dates) < 2:
        return None, None

    prev_date = dates[-2]
    prev_session = session_df[session_df.index.normalize() == prev_date]

    if prev_session.empty:
        return None, None

    return prev_session['high'].max(), prev_session['low'].min()

# --- EQUAL HIGHS / EQUAL LOWS (proximity filtered) ---
def get_eqh_eql(symbol, lookback=50):
    df = get_candles(symbol, mt5.TIMEFRAME_H1, lookback)
    if df is None:
        return [], []

    threshold    = get_threshold(symbol)
    current_price = get_current_price(symbol)
    five_day_range = get_5day_range(symbol)

    if current_price is None or five_day_range is None:
        return [], []

    proximity_limit = five_day_range * EQL_PROXIMITY_FACTOR

    highs = df['high'].values
    lows  = df['low'].values
    eqh_levels = []
    eql_levels = []

    for i in range(len(highs)):
        for j in range(i + 1, len(highs)):
            if abs(highs[i] - highs[j]) <= threshold:
                level = round((highs[i] + highs[j]) / 2, 5)
                if level not in eqh_levels:
                    if abs(level - current_price) <= proximity_limit:
                        eqh_levels.append(level)

    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            if abs(lows[i] - lows[j]) <= threshold:
                level = round((lows[i] + lows[j]) / 2, 5)
                if level not in eql_levels:
                    if abs(level - current_price) <= proximity_limit:
                        eql_levels.append(level)

    return sorted(eqh_levels), sorted(eql_levels)

# --- FULL LIQUIDITY SCAN ---
def scan_liquidity(symbol):
    print(f"\n{'=' * 55}")
    print(f"  LIQUIDITY LEVELS — {symbol}")
    print(f"{'=' * 55}")

    # Collect all levels
    pwh, pwl         = get_pwh_pwl(symbol)
    pdh, pdl         = get_pdh_pdl(symbol)

    asia_h,   asia_l   = get_session_hl(symbol, "asia")
    lon_h,    lon_l    = get_session_hl(symbol, "london")
    ny_h,     ny_l     = get_session_hl(symbol, "ny")

    p_asia_h, p_asia_l = get_prev_session_hl(symbol, "asia")
    p_lon_h,  p_lon_l  = get_prev_session_hl(symbol, "london")
    p_ny_h,   p_ny_l   = get_prev_session_hl(symbol, "ny")

    eqh, eql         = get_eqh_eql(symbol)
    current          = get_current_price(symbol)
    five_day         = get_5day_range(symbol)

    print(f"\n  Current Price   : {current}")
    print(f"  5-Day Range     : {round(five_day, 2) if five_day else 'N/A'}")
    print(f"  EQL Proximity   : ±{round(five_day * EQL_PROXIMITY_FACTOR, 2) if five_day else 'N/A'}")

    print(f"\n  WEEKLY:")
    print(f"    PWH : {pwh}")
    print(f"    PWL : {pwl}")

    print(f"\n  DAILY:")
    print(f"    PDH : {pdh}")
    print(f"    PDL : {pdl}")

    print(f"\n  CURRENT SESSIONS (today):")
    print(f"    Asia   High : {asia_h}  |  Low : {asia_l}")
    print(f"    London High : {lon_h}  |  Low : {lon_l}")
    print(f"    NY     High : {ny_h}  |  Low : {ny_l}")

    print(f"\n  PREVIOUS SESSIONS (yesterday):")
    print(f"    Asia   High : {p_asia_h}  |  Low : {p_asia_l}")
    print(f"    London High : {p_lon_h}  |  Low : {p_lon_l}")
    print(f"    NY     High : {p_ny_h}  |  Low : {p_ny_l}")

    print(f"\n  EQUAL HIGHS (within proximity):")
    if eqh:
        for level in eqh[-5:]:
            print(f"    EQH : {level}")
    else:
        print(f"    None within proximity")

    print(f"\n  EQUAL LOWS (within proximity):")
    if eql:
        for level in eql[:5]:
            print(f"    EQL : {level}")
    else:
        print(f"    None within proximity")

    return {
        "symbol"  : symbol,
        "current" : current,
        "PWH": pwh, "PWL": pwl,
        "PDH": pdh, "PDL": pdl,
        "Asia_H"  : asia_h,   "Asia_L"  : asia_l,
        "London_H": lon_h,    "London_L": lon_l,
        "NY_H"    : ny_h,     "NY_L"    : ny_l,
        "Prev_Asia_H"  : p_asia_h, "Prev_Asia_L"  : p_asia_l,
        "Prev_London_H": p_lon_h,  "Prev_London_L": p_lon_l,
        "Prev_NY_H"    : p_ny_h,   "Prev_NY_L"    : p_ny_l,
        "EQH": eqh, "EQL": eql
    }

# --- RUN TEST ---
if __name__ == "__main__":
    if connect():
        scan_liquidity("XAUUSD.sim")
        scan_liquidity("EURUSD.sim")
        disconnect()