from kiteconnect import KiteTicker
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("KITE_API_KEY")
access_token = os.getenv("KITE_ACCESS_TOKEN")

# Instrument tokens
INFY = 408065
RELIANCE = 738561
TCS = 2953217
HDFCBANK = 341249

tokens = [INFY, RELIANCE, TCS, HDFCBANK]

kws = KiteTicker(api_key, access_token)


def on_ticks(ws, ticks):
    for tick in ticks:
        instrument_token = tick["instrument_token"]
        last_price = tick["last_price"]

        print(f"Token: {instrument_token} | Live Price: {last_price}")


def on_connect(ws, response):
    print("WebSocket connected")
    ws.subscribe(tokens)
    ws.set_mode(ws.MODE_FULL, tokens)


def on_close(ws, code, reason):
    print("WebSocket closed:", code, reason)


kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close

print("Starting live stream...")
kws.connect()
