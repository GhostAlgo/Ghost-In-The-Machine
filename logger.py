# ============================================================
# THE GHOST IN THE MACHINE
# File: logger.py
# Purpose: Log all signals, trades, and scans to SQLite DB
# ============================================================

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

import sqlite3
import os
from datetime import datetime, timezone

# ─────────────────────────────────────────
# DB SETUP
# ─────────────────────────────────────────
DB_DIR  = r"C:\Users\Jay Stillo\Documents\GhostInTheMachine\logs"
DB_PATH = os.path.join(DB_DIR, "ghost.db")

def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    c    = conn.cursor()

    # Signals table -- every confirmed signal the bot generates
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            symbol      TEXT,
            direction   TEXT,
            sweep_type  TEXT,
            sweep_level TEXT,
            mss_level   TEXT,
            entry_zone_low  REAL,
            entry_zone_high REAL,
            sl          REAL,
            tp          REAL,
            zones_count INTEGER
        )
    """)

    # Trades table -- every trade the bot places
    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT,
            symbol      TEXT,
            direction   TEXT,
            entry_price REAL,
            sl          REAL,
            tp          REAL,
            lot_size    REAL,
            ticket      INTEGER,
            status      TEXT DEFAULT 'OPEN'
        )
    """)

    # Scans table -- every scan cycle, signal or not
    c.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT,
            symbol       TEXT,
            signal_fired INTEGER,  -- 1 = yes, 0 = no
            skip_reason  TEXT      -- why it was skipped if no signal
        )
    """)

    conn.commit()
    conn.close()
    print(f"  [LOGGER] DB ready at {DB_PATH}")

# ─────────────────────────────────────────
# LOG SIGNAL
# ─────────────────────────────────────────
def log_signal(signal):
    """Log a confirmed entry signal."""
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute("""
            INSERT INTO signals (
                timestamp, symbol, direction,
                sweep_type, sweep_level, mss_level,
                entry_zone_low, entry_zone_high,
                sl, tp, zones_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
            signal.get("symbol"),
            signal.get("direction"),
            signal.get("sweep", {}).get("type"),
            str(signal.get("sweep", {}).get("level")),
            str(signal.get("mss", {}).get("swing_level")),
            signal.get("sl"),
            signal.get("tp"),
            signal.get("sl"),
            signal.get("tp"),
            len(signal.get("zones", []))
        ))
        conn.commit()
        conn.close()
        print(f"  [LOGGER] Signal logged -- {signal.get('symbol')} {signal.get('direction')}")
    except Exception as e:
        print(f"  [LOGGER ERROR] Failed to log signal: {e}")

# ─────────────────────────────────────────
# LOG TRADE
# ─────────────────────────────────────────
def log_trade(signal, result):
    """Log a placed trade."""
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute("""
            INSERT INTO trades (
                timestamp, symbol, direction,
                entry_price, sl, tp,
                lot_size, ticket, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            signal.get("symbol"),
            signal.get("direction"),
            result.price,
            signal.get("sl"),
            signal.get("tp"),
            result.volume,
            result.order,
            "OPEN"
        ))
        conn.commit()
        conn.close()
        print(f"  [LOGGER] Trade logged -- Ticket {result.order} | {signal.get('symbol')} {signal.get('direction')}")
    except Exception as e:
        print(f"  [LOGGER ERROR] Failed to log trade: {e}")

# ─────────────────────────────────────────
# LOG SCAN
# ─────────────────────────────────────────
def log_scan(symbol, signal_fired, skip_reason=None):
    """Log every scan cycle whether a signal fired or not."""
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute("""
            INSERT INTO scans (timestamp, symbol, signal_fired, skip_reason)
            VALUES (?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            symbol,
            1 if signal_fired else 0,
            skip_reason
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"  [LOGGER ERROR] Failed to log scan: {e}")

# ─────────────────────────────────────────
# UPDATE TRADE STATUS
# ─────────────────────────────────────────
def update_trade_status(ticket, status):
    """Update a trade as WIN, LOSS, or BREAKEVEN when it closes."""
    try:
        conn = get_connection()
        c    = conn.cursor()
        c.execute("""
            UPDATE trades SET status = ? WHERE ticket = ?
        """, (status, ticket))
        conn.commit()
        conn.close()
        print(f"  [LOGGER] Trade {ticket} updated to {status}")
    except Exception as e:
        print(f"  [LOGGER ERROR] Failed to update trade: {e}")

# ─────────────────────────────────────────
# QUICK STATS PRINT
# ─────────────────────────────────────────
def print_stats():
    """Print a quick summary of all logged data."""
    try:
        conn = get_connection()
        c    = conn.cursor()

        c.execute("SELECT COUNT(*) FROM signals")
        total_signals = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM trades")
        total_trades = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM trades WHERE status = 'WIN'")
        wins = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM trades WHERE status = 'LOSS'")
        losses = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM scans")
        total_scans = c.fetchone()[0]

        conn.close()

        winrate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0

        print(f"\n{'=' * 55}")
        print(f"  GHOST IN THE MACHINE -- STATS")
        print(f"{'=' * 55}")
        print(f"  Total Scans   : {total_scans}")
        print(f"  Total Signals : {total_signals}")
        print(f"  Total Trades  : {total_trades}")
        print(f"  Wins          : {wins}")
        print(f"  Losses        : {losses}")
        print(f"  Win Rate      : {winrate}%")
        print(f"{'=' * 55}\n")

    except Exception as e:
        print(f"  [LOGGER ERROR] Failed to print stats: {e}")

# ─────────────────────────────────────────
# INIT ON IMPORT
# ─────────────────────────────────────────
init_db()

if __name__ == "__main__":
    print_stats()
