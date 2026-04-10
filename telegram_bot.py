# telegram_bot.py
# Ghost In The Machine -- Telegram Notifications

import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(message, retries=3):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    for attempt in range(retries):
        try:
            response = requests.post(url, data=payload, timeout=15)
            if response.status_code == 200:
                print(f"  [TELEGRAM] Message sent successfully")
                return True
            else:
                print(f"  [TELEGRAM] Failed -- status: {response.status_code}")
                return False
        except Exception as e:
            print(f"  [TELEGRAM] Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    print(f"  [TELEGRAM] All attempts failed -- continuing without notification")
    return False

def notify_signal(signal):
    symbol    = signal["symbol"]
    direction = signal["direction"].upper()
    timestamp = signal["timestamp"]
    if symbol == "SYSTEM":
        message = (
            f"<b>GHOST IN THE MACHINE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Bot is online and scanning\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        message = (
            f"<b>GHOST IN THE MACHINE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>SIGNAL DETECTED</b>\n"
            f"Symbol    : {symbol}\n"
            f"Direction : {direction}\n"
            f"Time      : {timestamp}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
    return send_message(message)

def notify_trade(symbol, direction, entry, sl, tp, lots, ticket):
    direction = direction.upper()
    message = (
        f"<b>GHOST IN THE MACHINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>TRADE PLACED</b>\n"
        f"Symbol    : {symbol}\n"
        f"Direction : {direction}\n"
        f"Entry     : {entry}\n"
        f"SL        : {sl}\n"
        f"TP        : {tp}\n"
        f"Lots      : {lots}\n"
        f"Ticket    : {ticket}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    return send_message(message)

def notify_no_signal():
    message = (
        f"<b>GHOST IN THE MACHINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Scan complete -- no signals this cycle\n"
        f"Bot is watching..."
    )
    return send_message(message)

def notify_error(error_msg):
    message = (
        f"<b>GHOST IN THE MACHINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>ERROR</b>\n"
        f"{error_msg}"
    )
    return send_message(message)

if __name__ == "__main__":
    print("\n  GHOST IN THE MACHINE -- TELEGRAM TEST")
    result = send_message(
        "<b>GHOST IN THE MACHINE</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Telegram reconnected successfully\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    if result:
        print("  SUCCESS")
    else:
        print("  FAILED")