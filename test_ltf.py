import sys
sys.path.insert(0, r"C:\Users\Jay Stillo\Documents\GhostInTheMachine")

from mt5_connection import connect, disconnect
from ltf_confirmation import confirm_ltf_entry

if connect():
    print("MT5 connected")
    for symbol in ["EURUSD.sim", "XAUUSD.sim"]:
        result = confirm_ltf_entry(symbol, direction="bullish")
        print(f"{symbol} LTF confirmation -> {result}")
    disconnect()
    print("Disconnected")
else:
    print("MT5 connection failed")
