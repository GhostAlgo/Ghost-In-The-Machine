# main.py
# Ghost In The Machine -- Master Loop
# Scans every 5 minutes, fires signals, places trades, logs everything
# Market hours: Sunday 21:00 UTC -- Friday 19:00 UTC

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

import time
import logging
from datetime import datetime, timezone
from mt5_connection import connect, disconnect
from entry_signal import scan_all
from trade_executor import place_trade
from telegram_bot import notify_signal, notify_trade, notify_no_signal, notify_error
from logger import log_signal, log_trade, log_scan, print_stats

# ─────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────
import os
log_dir = r"C:\Users\Jay Stillo\Documents\GhostInTheMachine\logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, "ghost.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def log(msg):
    print(msg)
    logging.info(msg)

# ─────────────────────────────────────────
# MARKET HOURS GATE
# Sunday 21:00 UTC open -- Friday 19:00 UTC close
# ─────────────────────────────────────────
def is_market_open():
    now     = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour    = now.hour
    minute  = now.minute

    if weekday == 5:
        return False
    if weekday == 6:
        return hour >= 21
    if weekday == 4:
        return (hour < 19) or (hour == 19 and minute == 0)
    return True

def get_sleep_until_open():
    now     = datetime.now(timezone.utc)
    weekday = now.weekday()

    if weekday == 5:
        seconds_to_sunday_21 = (6 - now.weekday()) * 86400
        open_hour_seconds    = 21 * 3600
        current_seconds      = now.hour * 3600 + now.minute * 60 + now.second
        return seconds_to_sunday_21 - current_seconds + open_hour_seconds
    if weekday == 6 and now.hour < 21:
        return (21 - now.hour) * 3600 - now.minute * 60 - now.second
    return 0

# ─────────────────────────────────────────
# SCAN CYCLE
# ─────────────────────────────────────────
def run_scan():
    log("=" * 55)
    log(f"  GHOST IN THE MACHINE -- SCAN CYCLE")
    log(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    log("=" * 55)

    if not connect():
        msg = "MT5 connection failed -- skipping scan"
        log(f"  [ERROR] {msg}")
        notify_error(msg)
        return

    try:
        signals = scan_all()

        if signals:
            for signal in signals:
                log(f"  SIGNAL: {signal['symbol']} {signal['direction'].upper()}")

                log_signal(signal)
                log_scan(signal["symbol"], signal_fired=True)
                notify_signal(signal)

                result = place_trade(signal)
                if result:
                    log(f"  TRADE PLACED: Ticket {result.order}")
                    log_trade(signal, result)
                    notify_trade(
                        symbol    = signal["symbol"],
                        direction = signal["direction"],
                        entry     = result.price,
                        sl        = signal.get("sl", "N/A"),
                        tp        = signal.get("tp", "N/A"),
                        lots      = result.volume,
                        ticket    = result.order
                    )
                else:
                    log(f"  TRADE FAILED for {signal['symbol']}")
                    notify_error(f"Trade failed for {signal['symbol']}")
        else:
            log("  No signals this scan -- bot is watching")
            from config import ALL_SYMBOLS
            for symbol in ALL_SYMBOLS:
                log_scan(symbol, signal_fired=False, skip_reason="No signal this cycle")

    except Exception as e:
        msg = f"Scan error: {str(e)}"
        log(f"  [ERROR] {msg}")
        notify_error(msg)

    finally:
        disconnect()

# ─────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────
if __name__ == "__main__":
    log("\n  GHOST IN THE MACHINE -- ONLINE")
    log("  Market hours: Sunday 21:00 UTC -- Friday 19:00 UTC")
    log("  Scanning every 5 minutes during market hours")
    log("  Press Ctrl+C to stop\n")

    notify_signal({
        "symbol"   : "SYSTEM",
        "direction": "online",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    })

    while True:
        try:
            if is_market_open():
                run_scan()
                log(f"\n  Next scan in 5 minutes...\n")
                time.sleep(300)
            else:
                now = datetime.now(timezone.utc)
                if now.weekday() == 4 and now.hour >= 19:
                    log(f"  Market closed -- Friday close reached. Sleeping until Sunday 21:00 UTC.")
                elif now.weekday() == 5:
                    log(f"  Market closed -- Saturday. Sleeping until Sunday 21:00 UTC.")
                elif now.weekday() == 6 and now.hour < 21:
                    log(f"  Market closed -- Sunday, waiting for 21:00 UTC open.")
                else:
                    log(f"  Market closed -- sleeping.")

                wait = get_sleep_until_open()
                if wait > 0:
                    log(f"  Resuming in {round(wait / 3600, 1)} hours.\n")
                    time.sleep(min(wait, 3600))
                else:
                    time.sleep(60)

        except KeyboardInterrupt:
            log("\n  GHOST IN THE MACHINE -- OFFLINE")
            log("  Stopped by user")
            print_stats()
            break
        except Exception as e:
            log(f"  [CRITICAL ERROR] {str(e)}")
            notify_error(f"Critical error: {str(e)}")
            time.sleep(60)
