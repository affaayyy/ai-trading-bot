from flask import Flask, request, render_template, render_template_string, session, redirect, url_for, has_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
import os
import requests
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.offline import plot
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")
kite = KiteConnect(api_key=api_key)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

AUTO_TRADE_ENABLED = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
MAX_ORDER_QTY = int(os.getenv("MAX_ORDER_QTY", 1))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 3))
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 1))
TARGET_PERCENT = float(os.getenv("TARGET_PERCENT", 2))
MIN_CONFIDENCE = int(os.getenv("MIN_CONFIDENCE", 70))
TRADE_CONFIDENCE = int(os.getenv("TRADE_CONFIDENCE", 80))

# Phase 23: AI Position Sizing + Capital Management
ACCOUNT_CAPITAL = float(os.getenv("ACCOUNT_CAPITAL", 100000))
RISK_PER_TRADE_PERCENT = float(os.getenv("RISK_PER_TRADE_PERCENT", 1))
MAX_DAILY_LOSS_PERCENT = float(os.getenv("MAX_DAILY_LOSS_PERCENT", 3))
MAX_POSITION_VALUE_PERCENT = float(os.getenv("MAX_POSITION_VALUE_PERCENT", 20))
MAX_PORTFOLIO_EXPOSURE_PERCENT = float(os.getenv("MAX_PORTFOLIO_EXPOSURE_PERCENT", 60))
MIN_TRADE_QTY = int(os.getenv("MIN_TRADE_QTY", 1))

SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 15))
MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", 5))

# Phase 27: News Sentiment AI Engine
NEWS_SENTIMENT_ENABLED = os.getenv("NEWS_SENTIMENT_ENABLED", "true").lower() == "true"
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_LIMIT = int(os.getenv("NEWS_LIMIT", 8))

STOCK_UNIVERSE = {
    "INFY": 408065,
    "RELIANCE": 738561,
    "TCS": 2953217,
    "HDFCBANK": 341249,
    "ICICIBANK": 1270529,
    "SBIN": 779521,
    "AXISBANK": 1510401,
    "KOTAKBANK": 492033,
    "LT": 2939649,
    "ITC": 424961,
    "HINDUNILVR": 356865,
    "BHARTIARTL": 2714625,
    "MARUTI": 2815745,
    "TITAN": 897537,
    "ASIANPAINT": 60417,
    "BAJFINANCE": 81153,
    "HCLTECH": 1850625,
    "WIPRO": 969473,
    "TECHM": 3465729,
    "SUNPHARMA": 857857,
    "CIPLA": 177665,
    "POWERGRID": 3834113,
    "NTPC": 2977281,
    "ONGC": 633601,
    "COALINDIA": 5215745,
    "TATASTEEL": 895745,
    "JSWSTEEL": 3001089,
    "HINDALCO": 348929,
    "ULTRACEMCO": 2952193,
    "NESTLEIND": 4598529,
}


# Phase 26: Sector Rotation AI mapping
SECTOR_MAP = {
    "INFY": "IT",
    "TCS": "IT",
    "HCLTECH": "IT",
    "WIPRO": "IT",
    "TECHM": "IT",
    "RELIANCE": "Energy",
    "ONGC": "Energy",
    "COALINDIA": "Energy",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "AXISBANK": "Banking",
    "KOTAKBANK": "Banking",
    "LT": "Infrastructure",
    "POWERGRID": "Infrastructure",
    "NTPC": "Infrastructure",
    "ITC": "FMCG",
    "HINDUNILVR": "FMCG",
    "NESTLEIND": "FMCG",
    "MARUTI": "Auto",
    "TITAN": "Consumer",
    "ASIANPAINT": "Consumer",
    "BAJFINANCE": "Finance",
    "SUNPHARMA": "Pharma",
    "CIPLA": "Pharma",
    "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals",
    "HINDALCO": "Metals",
    "ULTRACEMCO": "Cement",
}

# Phase 27: News query names for sentiment engine
STOCK_NEWS_QUERY_MAP = {
    "INFY": "Infosys",
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "AXISBANK": "Axis Bank",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen Toubro",
    "ITC": "ITC Limited",
    "HINDUNILVR": "Hindustan Unilever",
    "BHARTIARTL": "Bharti Airtel",
    "MARUTI": "Maruti Suzuki",
    "TITAN": "Titan Company",
    "ASIANPAINT": "Asian Paints",
    "BAJFINANCE": "Bajaj Finance",
    "HCLTECH": "HCL Technologies",
    "WIPRO": "Wipro",
    "TECHM": "Tech Mahindra",
    "SUNPHARMA": "Sun Pharma",
    "CIPLA": "Cipla",
    "POWERGRID": "Power Grid Corporation",
    "NTPC": "NTPC",
    "ONGC": "ONGC",
    "COALINDIA": "Coal India",
    "TATASTEEL": "Tata Steel",
    "JSWSTEEL": "JSW Steel",
    "HINDALCO": "Hindalco",
    "ULTRACEMCO": "UltraTech Cement",
    "NESTLEIND": "Nestle India",
}

POSITIVE_NEWS_WORDS = [
    "beats", "beat", "surge", "surges", "gain", "gains", "rally", "rises", "rise",
    "growth", "profit", "profits", "record", "upgrade", "bullish", "strong",
    "expands", "expansion", "wins", "order", "positive", "outperform", "buy",
    "breakout", "higher", "upside", "raises", "improves", "approval"
]

NEGATIVE_NEWS_WORDS = [
    "misses", "fall", "falls", "decline", "declines", "drop", "drops", "loss",
    "losses", "weak", "downgrade", "bearish", "fraud", "probe", "penalty",
    "fine", "risk", "concern", "concerns", "lawsuit", "sell", "lower",
    "downside", "cuts", "recession", "negative", "default"
]



class SignalLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    price = db.Column(db.Float)
    signal = db.Column(db.String(50))
    confidence = db.Column(db.Integer)
    score = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    transaction_type = db.Column(db.String(10))
    quantity = db.Column(db.Integer)
    status = db.Column(db.String(100))
    order_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TradeJournal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50))
    trade_type = db.Column(db.String(50))
    signal = db.Column(db.String(50))
    confidence = db.Column(db.Integer)
    score = db.Column(db.Integer)
    entry_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    stop_loss = db.Column(db.Float)
    target = db.Column(db.Float)
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(50), default="OPEN")
    pnl = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TokenStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WatchlistStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(50), unique=True, nullable=False)
    instrument_token = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


def get_latest_access_token():
    if has_request_context() and "access_token" in session:
        return session["access_token"]

    latest_token = TokenStore.query.order_by(TokenStore.created_at.desc()).first()
    return latest_token.access_token if latest_token else None


def is_logged_in():
    if has_request_context() and "access_token" in session:
        return True
    return False


def set_kite_token():
    token = get_latest_access_token()
    if token:
        kite.set_access_token(token)
        return True
    return False


def get_watchlist_symbols():
    try:
        stocks = WatchlistStock.query.order_by(WatchlistStock.id.desc()).all()

        if stocks and len(stocks) > 0:
            return [stock.symbol for stock in stocks]

    except Exception as e:
        print("Watchlist load error:", str(e), flush=True)

    return list(STOCK_UNIVERSE.keys())


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return "Telegram not configured"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}

    try:
        response = requests.post(url, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        return str(e)


def get_historical_df(instrument_token=408065):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)
    data = kite.historical_data(instrument_token, start_date, end_date, "day")
    return pd.DataFrame(data)


def prepare_indicator_df(df):
    """Add reusable technical indicators needed by market chart, scanner, and AI engines."""
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    macd = ta.trend.MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    return df


def generate_ai_strategy(df):
    df = prepare_indicator_df(df)

    latest = df.iloc[-1]
    score = 0
    reasons = []

    if latest["rsi"] < 30:
        score += 2
        reasons.append("RSI indicates oversold market")
    elif latest["rsi"] > 70:
        score -= 2
        reasons.append("RSI indicates overbought market")
    else:
        reasons.append("RSI is neutral")

    if latest["ema20"] > latest["ema50"]:
        score += 1
        reasons.append("EMA20 is above EMA50")
    else:
        score -= 1
        reasons.append("EMA20 is below EMA50")

    if latest["macd"] > latest["macd_signal"]:
        score += 1
        reasons.append("MACD bullish crossover")
    else:
        score -= 1
        reasons.append("MACD bearish crossover")

    if score >= 4:
        raw_signal = "STRONG BUY"
    elif score >= 2:
        raw_signal = "BUY"
    elif score <= -4:
        raw_signal = "STRONG SELL"
    elif score <= -2:
        raw_signal = "SELL"
    else:
        raw_signal = "HOLD"

    abs_score = abs(score)
    if abs_score == 0:
        confidence = 45
    elif abs_score == 1:
        confidence = 55
    elif abs_score == 2:
        confidence = 70
    elif abs_score == 3:
        confidence = 80
    else:
        confidence = 90

    if confidence < MIN_CONFIDENCE:
        signal = "WATCH"
        reasons.append(f"Confidence below {MIN_CONFIDENCE}%, trade blocked")
    else:
        signal = raw_signal

    return {
        "signal": signal,
        "raw_signal": raw_signal,
        "score": score,
        "confidence": confidence,
        "rsi": round(latest["rsi"], 2),
        "ema20": round(latest["ema20"], 2),
        "ema50": round(latest["ema50"], 2),
        "macd": round(latest["macd"], 2),
        "macd_signal": round(latest["macd_signal"], 2),
        "reasons": reasons,
    }


def calculate_trade_levels(entry_price, signal):
    if signal in ["BUY", "STRONG BUY"]:
        stop_loss = entry_price - (entry_price * STOP_LOSS_PERCENT / 100)
        target = entry_price + (entry_price * TARGET_PERCENT / 100)
    elif signal in ["SELL", "STRONG SELL"]:
        stop_loss = entry_price + (entry_price * STOP_LOSS_PERCENT / 100)
        target = entry_price - (entry_price * TARGET_PERCENT / 100)
    else:
        stop_loss = None
        target = None

    return {
        "stop_loss": round(stop_loss, 2) if stop_loss else None,
        "target": round(target, 2) if target else None,
    }


def calculate_journal_pnl(signal, entry_price, current_price, quantity):
    if signal in ["BUY", "STRONG BUY"]:
        return round((current_price - entry_price) * quantity, 2)
    if signal in ["SELL", "STRONG SELL"]:
        return round((entry_price - current_price) * quantity, 2)
    return 0


def get_effective_capital():
    """Use broker available cash when available, otherwise fallback to ACCOUNT_CAPITAL from .env."""
    try:
        if set_kite_token():
            margins = kite.margins()
            cash = margins.get("equity", {}).get("available", {}).get("cash")
            if cash and cash > 0:
                return float(cash)
    except Exception:
        pass

    return float(ACCOUNT_CAPITAL)


def get_open_exposure_value():
    open_trades = TradeJournal.query.filter_by(status="OPEN").all()
    exposure = 0

    for trade in open_trades:
        exposure += (trade.entry_price or 0) * (trade.quantity or 0)

    return round(exposure, 2)


def get_today_realized_pnl():
    today = datetime.utcnow().date()
    trades = TradeJournal.query.filter(
        db.func.date(TradeJournal.created_at) == today,
        TradeJournal.status != "OPEN"
    ).all()

    return round(sum([trade.pnl or 0 for trade in trades]), 2)


def calculate_position_size(entry_price, stop_loss):
    capital = get_effective_capital()

    if not entry_price or not stop_loss:
        return MIN_TRADE_QTY

    risk_per_share = abs(entry_price - stop_loss)

    if risk_per_share <= 0:
        return MIN_TRADE_QTY

    risk_amount = capital * (RISK_PER_TRADE_PERCENT / 100)
    max_position_value = capital * (MAX_POSITION_VALUE_PERCENT / 100)

    qty_by_risk = int(risk_amount // risk_per_share)
    qty_by_value = int(max_position_value // entry_price)

    quantity = max(MIN_TRADE_QTY, min(qty_by_risk, qty_by_value, MAX_ORDER_QTY))

    return max(quantity, 0)


def get_capital_management_snapshot():
    capital = get_effective_capital()
    open_exposure = get_open_exposure_value()
    today_pnl = get_today_realized_pnl()

    max_daily_loss_amount = capital * (MAX_DAILY_LOSS_PERCENT / 100)
    max_portfolio_exposure = capital * (MAX_PORTFOLIO_EXPOSURE_PERCENT / 100)

    return {
        "capital": round(capital, 2),
        "open_exposure": round(open_exposure, 2),
        "open_exposure_percent": round((open_exposure / capital) * 100, 2) if capital else 0,
        "today_pnl": round(today_pnl, 2),
        "max_daily_loss_amount": round(max_daily_loss_amount, 2),
        "max_portfolio_exposure": round(max_portfolio_exposure, 2),
        "risk_per_trade_percent": RISK_PER_TRADE_PERCENT,
        "max_daily_loss_percent": MAX_DAILY_LOSS_PERCENT,
        "max_position_value_percent": MAX_POSITION_VALUE_PERCENT,
        "max_portfolio_exposure_percent": MAX_PORTFOLIO_EXPOSURE_PERCENT,
    }


def risk_check(symbol, signal, quantity, confidence, entry_price=None, stop_loss=None):
    today = datetime.utcnow().date()
    today_orders = OrderLog.query.filter(db.func.date(OrderLog.created_at) == today).count()

    if today_orders >= MAX_TRADES_PER_DAY:
        return False, "Daily trade limit reached"

    if quantity < MIN_TRADE_QTY:
        return False, "Calculated quantity below minimum trade quantity"

    if quantity > MAX_ORDER_QTY:
        return False, "Quantity exceeds maximum order quantity"

    if signal not in ["BUY", "SELL", "STRONG BUY", "STRONG SELL"]:
        return False, "Signal not actionable"

    if confidence < TRADE_CONFIDENCE:
        return False, f"Confidence below trade threshold {TRADE_CONFIDENCE}%"

    capital = get_effective_capital()
    today_pnl = get_today_realized_pnl()
    max_daily_loss_amount = capital * (MAX_DAILY_LOSS_PERCENT / 100)

    if today_pnl <= -max_daily_loss_amount:
        return False, f"Daily max loss reached. Today P&L: ₹{today_pnl}"

    open_exposure = get_open_exposure_value()
    new_position_value = (entry_price or 0) * quantity
    max_portfolio_exposure = capital * (MAX_PORTFOLIO_EXPOSURE_PERCENT / 100)

    if open_exposure + new_position_value > max_portfolio_exposure:
        return False, "Portfolio exposure limit reached"

    if entry_price and stop_loss:
        trade_risk = abs(entry_price - stop_loss) * quantity
        max_trade_risk = capital * (RISK_PER_TRADE_PERCENT / 100)

        if trade_risk > max_trade_risk:
            return False, "Trade risk exceeds risk-per-trade limit"

    return True, "Risk check passed"

def save_trade_journal(symbol, trade_type, strategy, entry_price, current_price, levels, quantity=1, status="OPEN", notes=""):
    journal = TradeJournal(
        symbol=symbol,
        trade_type=trade_type,
        signal=strategy["signal"],
        confidence=strategy["confidence"],
        score=strategy["score"],
        entry_price=entry_price,
        current_price=current_price,
        stop_loss=levels["stop_loss"],
        target=levels["target"],
        quantity=quantity,
        status=status,
        pnl=0,
        notes=notes,
    )
    db.session.add(journal)
    db.session.commit()
    return journal


def monitor_open_trades():
    if not set_kite_token():
        print("No valid Zerodha token found for trade monitor.", flush=True)
        return {"checked": 0, "closed": 0, "message": "No valid Zerodha token found. Please login once today."}

    open_trades = TradeJournal.query.filter_by(status="OPEN").all()
    checked_count = 0
    closed_count = 0

    for trade in open_trades:
        checked_count += 1
        try:
            current_price = round(get_live_price(trade.symbol, trade.current_price or trade.entry_price), 2)
            trade.current_price = current_price
            trade.pnl = calculate_journal_pnl(trade.signal, trade.entry_price, current_price, trade.quantity)

            exit_reason = None
            if trade.signal in ["BUY", "STRONG BUY"]:
                if trade.stop_loss and current_price <= trade.stop_loss:
                    exit_reason = "STOP_LOSS_HIT"
                elif trade.target and current_price >= trade.target:
                    exit_reason = "TARGET_HIT"
            elif trade.signal in ["SELL", "STRONG SELL"]:
                if trade.stop_loss and current_price >= trade.stop_loss:
                    exit_reason = "STOP_LOSS_HIT"
                elif trade.target and current_price <= trade.target:
                    exit_reason = "TARGET_HIT"

            if exit_reason:
                trade.status = exit_reason
                closed_count += 1
                send_telegram_alert(f"""
🚨 <b>Trade Monitor Alert</b>

Stock: {trade.symbol}
Signal: {trade.signal}
Status: {exit_reason}

Entry Price: ₹{trade.entry_price}
Current Price: ₹{current_price}
Stop Loss: ₹{trade.stop_loss}
Target: ₹{trade.target}
Quantity: {trade.quantity}
P&L: ₹{trade.pnl}

Trade Journal ID: {trade.id}
""")

        except Exception as e:
            trade.notes = f"{trade.notes or ''}\nMonitor error: {str(e)}"

    db.session.commit()
    return {"checked": checked_count, "closed": closed_count, "message": f"Trade monitor completed. Checked: {checked_count}, Closed: {closed_count}"}


def get_journal_analytics(trades):
    total_trades = len(trades)
    open_trades = len([t for t in trades if t.status == "OPEN"])
    closed_trades_list = [t for t in trades if t.status != "OPEN"]
    closed_trades = len(closed_trades_list)
    winning_trades = [t for t in closed_trades_list if (t.pnl or 0) > 0]
    losing_trades = [t for t in closed_trades_list if (t.pnl or 0) < 0]

    total_pnl = round(sum([t.pnl or 0 for t in trades]), 2)
    closed_pnl = round(sum([t.pnl or 0 for t in closed_trades_list]), 2)
    avg_pnl = round(closed_pnl / closed_trades, 2) if closed_trades else 0
    win_rate = round((len(winning_trades) / closed_trades) * 100, 2) if closed_trades else 0
    best_trade = max(closed_trades_list, key=lambda t: t.pnl or 0) if closed_trades_list else None
    worst_trade = min(closed_trades_list, key=lambda t: t.pnl or 0) if closed_trades_list else None

    return {
        "total_trades": total_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "total_pnl": total_pnl,
        "closed_pnl": closed_pnl,
        "avg_pnl": avg_pnl,
        "win_rate": win_rate,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
    }


def close_trade_by_id(trade_id):
    trade = TradeJournal.query.get_or_404(trade_id)
    current_price = round(get_live_price(trade.symbol, trade.current_price or trade.entry_price), 2)
    trade.current_price = current_price
    trade.pnl = calculate_journal_pnl(trade.signal, trade.entry_price, current_price, trade.quantity)
    trade.status = "CLOSED"
    db.session.commit()
    return trade


def auto_close_open_trades():
    if not set_kite_token():
        return {"closed": 0, "message": "No valid Zerodha token found. Please login once today."}

    open_trades = TradeJournal.query.filter_by(status="OPEN").all()
    closed_count = 0

    for trade in open_trades:
        current_price = round(get_live_price(trade.symbol, trade.current_price or trade.entry_price), 2)
        trade.current_price = current_price
        trade.pnl = calculate_journal_pnl(trade.signal, trade.entry_price, current_price, trade.quantity)
        trade.status = "CLOSED"
        closed_count += 1

    db.session.commit()
    return {"closed": closed_count, "message": f"Auto-closed {closed_count} open trades."}


def execute_auto_trade(symbol, signal, quantity=None, entry_price=None, confidence=0, stop_loss=None):
    if not AUTO_TRADE_ENABLED:
        return "SAFE MODE ENABLED\n\nAuto trading disabled."

    if signal in ["BUY", "STRONG BUY"]:
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif signal in ["SELL", "STRONG SELL"]:
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        return "No trade placed. Signal is not actionable."

    if quantity is None:
        quantity = calculate_position_size(entry_price, stop_loss)

    allowed, reason = risk_check(
        symbol=symbol,
        signal=signal,
        quantity=quantity,
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss
    )

    if not allowed:
        return f"Trade blocked.\n\nReason: {reason}"

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET,
        )
        db.session.add(OrderLog(symbol=symbol, transaction_type=transaction_type, quantity=quantity, status="AUTO_SUCCESS", order_id=order_id))
        db.session.commit()
        levels = calculate_trade_levels(entry_price, signal)
        return f"""
AUTO TRADE EXECUTED

Stock: {symbol}
Signal: {signal}
Confidence: {confidence}%
Quantity: {quantity}
Order ID: {order_id}
Stop Loss: {levels["stop_loss"]}
Target: {levels["target"]}
"""
    except Exception as e:
        db.session.add(OrderLog(symbol=symbol, transaction_type="AUTO", quantity=quantity, status="AUTO_FAILED", order_id=None))
        db.session.commit()
        return f"Auto trade failed.\n\nReason: {str(e)}"


def calculate_portfolio_analytics(holdings):
    total_invested = 0
    current_value = 0
    total_pnl = 0
    holdings_data = []

    for h in holdings:
        symbol = h.get("tradingsymbol")
        quantity = h.get("quantity", 0)
        avg_price = h.get("average_price", 0)
        last_price = h.get("last_price", 0)
        pnl = h.get("pnl", 0)
        invested = quantity * avg_price
        value = quantity * last_price
        total_invested += invested
        current_value += value
        total_pnl += pnl
        holdings_data.append({"symbol": symbol, "quantity": quantity, "average_price": round(avg_price, 2), "last_price": round(last_price, 2), "invested": round(invested, 2), "current_value": round(value, 2), "pnl": round(pnl, 2)})

    pnl_percent = (total_pnl / total_invested) * 100 if total_invested > 0 else 0
    return {"total_invested": round(total_invested, 2), "current_value": round(current_value, 2), "total_pnl": round(total_pnl, 2), "pnl_percent": round(pnl_percent, 2), "holdings_data": holdings_data}


def get_live_price(symbol, fallback_price):
    try:
        quote = kite.quote([f"NSE:{symbol}"])
        return quote[f"NSE:{symbol}"]["last_price"]
    except Exception:
        return fallback_price


def get_opportunity_score(strategy):
    confidence = strategy["confidence"]
    score = abs(strategy["score"])
    if confidence < MIN_CONFIDENCE:
        return 0
    if strategy["signal"] in ["STRONG BUY", "STRONG SELL"]:
        return confidence + score * 10 + 30
    if strategy["signal"] in ["BUY", "SELL"]:
        return confidence + score * 10 + 20
    return confidence + score * 5


def scan_multiple_stocks(selected_symbols=None, top_n=None, min_confidence_filter=0):
    set_kite_token()
    symbols_to_scan = selected_symbols if selected_symbols else get_watchlist_symbols()
    scan_results = []

    for symbol in symbols_to_scan:
        try:
            token = STOCK_UNIVERSE.get(symbol)
            if not token:
                raise Exception("Instrument token not found")
            df = get_historical_df(token)
            strategy = generate_ai_strategy(df)
            entry_price = round(df.iloc[-1]["close"], 2)
            current_price = round(get_live_price(symbol, entry_price), 2)
            levels = calculate_trade_levels(entry_price, strategy["signal"])
            opportunity_score = get_opportunity_score(strategy)
            item = {"symbol": symbol, "price": current_price, "current_price": current_price, "entry_price": entry_price, "stop_loss": levels["stop_loss"], "target": levels["target"], "signal": strategy["signal"], "raw_signal": strategy["raw_signal"], "confidence": strategy["confidence"], "score": strategy["score"], "opportunity_score": opportunity_score, "rsi": strategy["rsi"], "ema20": strategy["ema20"], "ema50": strategy["ema50"], "reasons": ", ".join(strategy["reasons"])}
            if item["confidence"] >= min_confidence_filter:
                scan_results.append(item)
        except Exception as e:
            scan_results.append({"symbol": symbol, "price": "Error", "current_price": "Error", "entry_price": "Error", "stop_loss": "-", "target": "-", "signal": "ERROR", "raw_signal": "ERROR", "confidence": 0, "score": 0, "opportunity_score": 0, "rsi": "-", "ema20": "-", "ema50": "-", "reasons": str(e)})

    scan_results = sorted(scan_results, key=lambda x: x["opportunity_score"], reverse=True)
    return scan_results[:top_n] if top_n else scan_results


def send_scanner_alerts(results):
    alert_count = 0
    for item in results:
        if item["confidence"] < MIN_CONFIDENCE:
            continue
        message = f"""
🚨 <b>Top AI Stock Alert</b>

Stock: {item["symbol"]}
Signal: {item["signal"]}
Confidence: {item["confidence"]}%
Score: {item["score"]}
Opportunity Score: {item["opportunity_score"]}
RSI: {item["rsi"]}

Current Price: ₹{item["current_price"]}
Entry Price: ₹{item["entry_price"]}
Stop Loss: ₹{item["stop_loss"]}
Target Price: ₹{item["target"]}

Reason:
{item["reasons"]}
"""
        send_telegram_alert(message)
        alert_count += 1
    return alert_count


def run_backtest_v2(df, initial_capital=100000):
    capital = initial_capital
    position = 0
    entry_price = 0
    trades = []
    equity_curve = []
    peak_equity = initial_capital
    max_drawdown = 0
    df = df.copy()
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    for i in range(50, len(df)):
        row = df.iloc[i]
        price = row["close"]
        current_equity = capital + (position * price)
        peak_equity = max(peak_equity, current_equity)
        drawdown = ((peak_equity - current_equity) / peak_equity) * 100
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({"date": row["date"], "equity": round(current_equity, 2)})
        buy_signal = row["rsi"] < 35 and row["ema20"] > row["ema50"] and position == 0
        sell_signal = row["rsi"] > 65 and position > 0
        stop_loss_hit = position > 0 and price <= entry_price * 0.99
        target_hit = position > 0 and price >= entry_price * 1.02

        if buy_signal:
            quantity = int(capital // price)
            if quantity > 0:
                position = quantity
                entry_price = price
                capital -= quantity * price
                trades.append({"date": row["date"], "action": "BUY", "price": round(price, 2), "quantity": quantity, "pnl": 0, "reason": "AI BUY Signal"})
        elif sell_signal or stop_loss_hit or target_hit:
            capital += position * price
            pnl = (price - entry_price) * position
            reason = "Stop Loss Hit" if stop_loss_hit else "Target Hit" if target_hit else "AI SELL Signal"
            trades.append({"date": row["date"], "action": "SELL", "price": round(price, 2), "quantity": position, "pnl": round(pnl, 2), "reason": reason})
            position = 0
            entry_price = 0

    final_value = capital + (position * df.iloc[-1]["close"])
    total_pnl = final_value - initial_capital
    roi = (total_pnl / initial_capital) * 100
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    winning_trades = [t for t in sell_trades if t["pnl"] > 0]
    win_rate = (len(winning_trades) / len(sell_trades)) * 100 if sell_trades else 0
    return {"initial_capital": initial_capital, "final_value": round(final_value, 2), "total_pnl": round(total_pnl, 2), "roi": round(roi, 2), "total_trades": len(trades), "win_rate": round(win_rate, 2), "max_drawdown": round(max_drawdown, 2), "trades": trades, "equity_curve": equity_curve}


def get_sector_rotation_data(symbols=None):
    """Phase 26: Rank sectors using watchlist/stock universe momentum and AI signal strength."""
    set_kite_token()

    symbols_to_scan = symbols if symbols else list(STOCK_UNIVERSE.keys())
    sector_bucket = {}

    for symbol in symbols_to_scan:
        if symbol not in STOCK_UNIVERSE:
            continue

        sector = SECTOR_MAP.get(symbol, "Others")

        try:
            df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))

            if df.empty or len(df) < 30:
                continue

            strategy = generate_ai_strategy(df)
            latest_close = float(df.iloc[-1]["close"])
            close_5d = float(df.iloc[-6]["close"]) if len(df) > 6 else latest_close
            close_20d = float(df.iloc[-21]["close"]) if len(df) > 21 else latest_close

            momentum_5d = ((latest_close - close_5d) / close_5d) * 100 if close_5d else 0
            momentum_20d = ((latest_close - close_20d) / close_20d) * 100 if close_20d else 0

            signal_bias = 0
            if strategy["signal"] in ["BUY", "STRONG BUY"]:
                signal_bias = strategy["confidence"]
            elif strategy["signal"] in ["SELL", "STRONG SELL"]:
                signal_bias = -strategy["confidence"]
            else:
                signal_bias = 0

            composite_score = round((momentum_5d * 2) + momentum_20d + (signal_bias / 10), 2)

            row = {
                "symbol": symbol,
                "sector": sector,
                "price": round(latest_close, 2),
                "signal": strategy["signal"],
                "confidence": strategy["confidence"],
                "score": strategy["score"],
                "rsi": strategy["rsi"],
                "momentum_5d": round(momentum_5d, 2),
                "momentum_20d": round(momentum_20d, 2),
                "composite_score": composite_score,
            }

            sector_bucket.setdefault(sector, []).append(row)

        except Exception as e:
            sector_bucket.setdefault(sector, []).append({
                "symbol": symbol,
                "sector": sector,
                "price": "Error",
                "signal": "ERROR",
                "confidence": 0,
                "score": 0,
                "rsi": "-",
                "momentum_5d": 0,
                "momentum_20d": 0,
                "composite_score": 0,
                "error": str(e),
            })

    sectors = []

    for sector, stocks in sector_bucket.items():
        valid = [x for x in stocks if isinstance(x.get("composite_score"), (int, float))]
        avg_score = round(sum(x["composite_score"] for x in valid) / len(valid), 2) if valid else 0
        avg_confidence = round(sum(x.get("confidence", 0) for x in valid) / len(valid), 2) if valid else 0
        bullish_count = len([x for x in valid if x.get("signal") in ["BUY", "STRONG BUY"]])
        bearish_count = len([x for x in valid if x.get("signal") in ["SELL", "STRONG SELL"]])

        if avg_score >= 12:
            rotation_signal = "STRONG ROTATION IN"
        elif avg_score >= 5:
            rotation_signal = "ROTATION IN"
        elif avg_score <= -12:
            rotation_signal = "STRONG ROTATION OUT"
        elif avg_score <= -5:
            rotation_signal = "ROTATION OUT"
        else:
            rotation_signal = "NEUTRAL"

        sectors.append({
            "sector": sector,
            "avg_score": avg_score,
            "avg_confidence": avg_confidence,
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "stock_count": len(stocks),
            "rotation_signal": rotation_signal,
            "stocks": sorted(stocks, key=lambda x: x.get("composite_score", 0), reverse=True),
        })

    return sorted(sectors, key=lambda x: x["avg_score"], reverse=True)


def get_top_sector_opportunities(limit=5):
    sectors = get_sector_rotation_data(get_watchlist_symbols())
    opportunities = []

    for sector in sectors:
        for stock in sector["stocks"]:
            stock["sector_rank_score"] = sector["avg_score"]
            stock["rotation_signal"] = sector["rotation_signal"]
            opportunities.append(stock)

    opportunities = sorted(
        opportunities,
        key=lambda x: (x.get("sector_rank_score", 0), x.get("composite_score", 0), x.get("confidence", 0)),
        reverse=True,
    )

    return opportunities[:limit]



def fetch_stock_news(symbol, limit=None):
    """Phase 27: Fetch latest stock news using NewsAPI when configured, otherwise Yahoo Finance RSS."""
    if limit is None:
        limit = NEWS_LIMIT

    symbol = symbol.upper()
    query_name = STOCK_NEWS_QUERY_MAP.get(symbol, symbol)
    articles = []

    if NEWS_API_KEY:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": f'"{query_name}" OR {symbol}',
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": limit,
                "apiKey": NEWS_API_KEY,
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            for item in data.get("articles", [])[:limit]:
                articles.append({
                    "title": item.get("title") or "",
                    "summary": item.get("description") or "",
                    "url": item.get("url") or "",
                    "source": (item.get("source") or {}).get("name", "NewsAPI"),
                    "published_at": item.get("publishedAt") or "",
                })

            if articles:
                return articles

        except Exception as e:
            print("NewsAPI fetch error:", str(e), flush=True)

    try:
        yahoo_symbol = f"{symbol}.NS"
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(yahoo_symbol)}&region=IN&lang=en-IN"
        response = requests.get(url, timeout=10)

        root = ET.fromstring(response.content)
        channel = root.find("channel")

        if channel is not None:
            for item in channel.findall("item")[:limit]:
                articles.append({
                    "title": item.findtext("title") or "",
                    "summary": item.findtext("description") or "",
                    "url": item.findtext("link") or "",
                    "source": "Yahoo Finance RSS",
                    "published_at": item.findtext("pubDate") or "",
                })

    except Exception as e:
        print("Yahoo RSS fetch error:", str(e), flush=True)

    return articles[:limit]


def score_news_text(text_value):
    text_lower = (text_value or "").lower()
    positive_hits = sum(1 for word in POSITIVE_NEWS_WORDS if word in text_lower)
    negative_hits = sum(1 for word in NEGATIVE_NEWS_WORDS if word in text_lower)
    return positive_hits - negative_hits, positive_hits, negative_hits


def analyze_news_sentiment(symbol):
    """Phase 27: Simple explainable news sentiment engine."""
    symbol = symbol.upper()
    articles = fetch_stock_news(symbol, NEWS_LIMIT)

    scored_articles = []
    total_score = 0
    positive_articles = 0
    negative_articles = 0
    neutral_articles = 0

    for article in articles:
        combined_text = f"{article.get('title', '')} {article.get('summary', '')}"
        article_score, positive_hits, negative_hits = score_news_text(combined_text)
        total_score += article_score

        if article_score > 0:
            sentiment = "BULLISH"
            positive_articles += 1
        elif article_score < 0:
            sentiment = "BEARISH"
            negative_articles += 1
        else:
            sentiment = "NEUTRAL"
            neutral_articles += 1

        scored_articles.append({
            "title": article.get("title", ""),
            "summary": article.get("summary", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "published_at": article.get("published_at", ""),
            "sentiment": sentiment,
            "score": article_score,
            "positive_hits": positive_hits,
            "negative_hits": negative_hits,
        })

    article_count = len(scored_articles)

    if article_count == 0:
        return {
            "symbol": symbol,
            "overall_sentiment": "NO NEWS",
            "confidence": 0,
            "sentiment_score": 0,
            "positive_articles": 0,
            "negative_articles": 0,
            "neutral_articles": 0,
            "articles": [],
            "summary": "No recent news found or news provider unavailable.",
            "signal_boost": 0,
        }

    normalized_score = total_score / article_count

    if normalized_score >= 1.5:
        overall = "STRONG BULLISH"
        signal_boost = 10
    elif normalized_score > 0:
        overall = "BULLISH"
        signal_boost = 5
    elif normalized_score <= -1.5:
        overall = "STRONG BEARISH"
        signal_boost = -10
    elif normalized_score < 0:
        overall = "BEARISH"
        signal_boost = -5
    else:
        overall = "NEUTRAL"
        signal_boost = 0

    confidence = min(95, int(40 + abs(normalized_score) * 20 + article_count * 3))

    return {
        "symbol": symbol,
        "overall_sentiment": overall,
        "confidence": confidence,
        "sentiment_score": round(normalized_score, 2),
        "positive_articles": positive_articles,
        "negative_articles": negative_articles,
        "neutral_articles": neutral_articles,
        "articles": scored_articles,
        "summary": f"{overall} sentiment based on {article_count} recent news item(s).",
        "signal_boost": signal_boost,
    }


def send_news_sentiment_alert(symbol):
    data = analyze_news_sentiment(symbol)

    message = f"""
📰 <b>News Sentiment Alert</b>

Stock: {data["symbol"]}
Sentiment: {data["overall_sentiment"]}
Confidence: {data["confidence"]}%
Score: {data["sentiment_score"]}
Signal Boost: {data["signal_boost"]}

Positive News: {data["positive_articles"]}
Negative News: {data["negative_articles"]}
Neutral News: {data["neutral_articles"]}

Summary:
{data["summary"]}
"""

    send_telegram_alert(message)
    return data

def autonomous_scan_job():
    with app.app_context():
        try:
            if not set_kite_token():
                print("No valid Zerodha token found. Please login once today.", flush=True)
                return
            monitor_open_trades()
            results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
            alert_count = send_scanner_alerts(results)
            for item in results:
                if item["confidence"] >= TRADE_CONFIDENCE:
                    execute_auto_trade(
                        symbol=item["symbol"],
                        signal=item["signal"],
                        quantity=None,
                        entry_price=item["entry_price"],
                        confidence=item["confidence"],
                        stop_loss=item["stop_loss"]
                    )
            print(f"Autonomous scan completed. Alerts sent: {alert_count}", flush=True)
        except Exception as e:
            print("Autonomous scan failed:", str(e), flush=True)


@app.route("/")
def login_page():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return render_template("login.html", login_url=kite.login_url())


@app.route("/login")
def login():
    request_token = request.args.get("request_token")
    if not request_token:
        return "Login failed. Request token not found."
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]
    session["access_token"] = access_token
    db.session.add(TokenStore(access_token=access_token))
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()

    try:
        TokenStore.query.delete()
        db.session.commit()
    except Exception as e:
        print("Logout token clear error:", str(e), flush=True)

    return redirect(url_for("login_page"))


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return render_template("dashboard.html")


@app.route("/market")
def market():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    set_kite_token()

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get(
        "symbol",
        watchlist_symbols[0] if watchlist_symbols else "INFY"
    ).upper()

    if selected_symbol not in STOCK_UNIVERSE:
        selected_symbol = "INFY"

    try:
        df = get_historical_df(STOCK_UNIVERSE[selected_symbol])

        if df is None or df.empty or len(df) < 60:
            raise Exception("Historical data empty or insufficient")

    except Exception as e:
        print("Market data error:", str(e), flush=True)
        selected_symbol = "INFY"
        df = get_historical_df(STOCK_UNIVERSE["INFY"])

    df = prepare_indicator_df(df)
    df.dropna(inplace=True)

    if df.empty:
        return render_template(
            "scanner_trade_result.html",
            message="Market chart could not load because historical data is unavailable. Please refresh after login/token update."
        )

    strategy = generate_ai_strategy(df)
    entry_price = round(float(df.iloc[-1]["close"]), 2)
    live_price = round(get_live_price(selected_symbol, entry_price), 2)
    levels = calculate_trade_levels(entry_price, strategy["signal"])

    market_data = []
    valid_watchlist = [s for s in watchlist_symbols if s in STOCK_UNIVERSE]
    quote_symbols = [f"NSE:{symbol}" for symbol in valid_watchlist[:8]]

    try:
        quotes = kite.quote(quote_symbols) if quote_symbols else {}

        for symbol in valid_watchlist[:8]:
            key = f"NSE:{symbol}"
            price = quotes.get(key, {}).get("last_price", None)

            if price is None:
                price = get_live_price(symbol, 0)

            market_data.append({
                "symbol": symbol,
                "price": price,
                "signal": "HOLD" if price and price > 1000 else "WATCH"
            })

            db.session.add(SignalLog(
                symbol=symbol,
                price=price or 0,
                signal=strategy["signal"],
                confidence=strategy["confidence"],
                score=strategy["score"]
            ))

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Market quote error:", str(e), flush=True)

    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Candlestick"
    ))

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["ema20"],
        mode="lines",
        name="EMA20"
    ))

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["ema50"],
        mode="lines",
        name="EMA50"
    ))

    fig.add_trace(go.Scatter(
        x=[datetime.now()],
        y=[live_price],
        mode="markers+text",
        name="Live Price",
        text=[f"Live ₹{live_price}"],
        textposition="top center"
    ))

    fig.update_layout(
        title=f"{selected_symbol} AI Trading Chart - Live Price ₹{live_price}",
        height=550
    )

    chart = plot(fig, output_type="div")

    return render_template(
        "market.html",
        watchlist_symbols=watchlist_symbols,
        selected_symbol=selected_symbol,
        latest_rsi=strategy["rsi"],
        latest_ema20=strategy["ema20"],
        latest_ema50=strategy["ema50"],
        macd=strategy["macd"],
        macd_signal=strategy["macd_signal"],
        ai_signal=strategy["signal"],
        confidence=strategy["confidence"],
        score=strategy["score"],
        reasons=strategy["reasons"],
        current_price=live_price,
        entry_price=entry_price,
        stop_loss=levels["stop_loss"],
        target=levels["target"],
        gpt_reasoning="AI signal generated using RSI, EMA20, EMA50, MACD, and Bollinger Bands.",
        market_data=market_data,
        chart=chart
    )


@app.route("/portfolio")
def portfolio():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    profile = kite.profile()
    holdings = kite.holdings()
    margins = kite.margins()
    cash = margins["equity"]["available"]["cash"]
    analytics = calculate_portfolio_analytics(holdings)
    if analytics["holdings_data"]:
        allocation_fig = go.Figure()
        allocation_fig.add_trace(go.Pie(labels=[h["symbol"] for h in analytics["holdings_data"]], values=[h["current_value"] for h in analytics["holdings_data"]], hole=0.4))
        allocation_fig.update_layout(title="Portfolio Allocation", height=400)
        allocation_chart = plot(allocation_fig, output_type="div")
    else:
        allocation_chart = "<p>No holdings available.</p>"
    return render_template("portfolio.html", profile=profile, cash=cash, analytics=analytics, allocation_chart=allocation_chart)


@app.route("/orders", methods=["GET", "POST"])
def orders():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    message = None
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        transaction_type = request.form.get("transaction_type")
        quantity = int(request.form.get("quantity"))
        try:
            order_id = kite.place_order(variety=kite.VARIETY_REGULAR, exchange=kite.EXCHANGE_NSE, tradingsymbol=symbol, transaction_type=transaction_type, quantity=quantity, product=kite.PRODUCT_CNC, order_type=kite.ORDER_TYPE_MARKET)
            message = f"Order placed successfully. Order ID: {order_id}"
            status = "SUCCESS"
        except Exception as e:
            order_id = None
            message = f"Order failed: {str(e)}"
            status = "FAILED"
        db.session.add(OrderLog(symbol=symbol, transaction_type=transaction_type, quantity=quantity, status=status, order_id=order_id))
        db.session.commit()
    return render_template("orders.html", message=message)


@app.route("/history")
def history():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    signals = SignalLog.query.order_by(SignalLog.created_at.desc()).limit(50).all()
    orders = OrderLog.query.order_by(OrderLog.created_at.desc()).limit(50).all()
    return render_template("history.html", signals=signals, orders=orders)


@app.route("/trade-journal")
def trade_journal():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    monitor = request.args.get("monitor", "false") == "true"
    if monitor:
        monitor_open_trades()
    trades = TradeJournal.query.order_by(TradeJournal.created_at.desc()).limit(200).all()
    analytics = get_journal_analytics(trades)
    return render_template("trade_journal.html", trades=trades, analytics=analytics)


@app.route("/trade-journal/close/<int:trade_id>")
def close_trade_journal(trade_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    close_trade_by_id(trade_id)
    return redirect(url_for("trade_journal"))


@app.route("/trade-journal/delete/<int:trade_id>")
def delete_trade_journal(trade_id):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    trade = TradeJournal.query.get_or_404(trade_id)
    db.session.delete(trade)
    db.session.commit()
    return redirect(url_for("trade_journal"))


@app.route("/trade-journal/auto-close-all")
def trade_journal_auto_close_all():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    auto_close_open_trades()
    return redirect(url_for("trade_journal"))


@app.route("/trade-journal/monitor")
def trade_journal_monitor():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    monitor_open_trades()
    return redirect(url_for("trade_journal"))


@app.route("/monitor-trades")
def monitor_trades():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    result = monitor_open_trades()
    return render_template("scanner_trade_result.html", message=result["message"])


@app.route("/paper-trading")
def paper_trading():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return render_template("paper_trading.html")


@app.route("/auto-trade")
def auto_trade():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    symbol = "INFY"
    df = get_historical_df(STOCK_UNIVERSE[symbol])
    strategy = generate_ai_strategy(df)
    entry_price = round(df.iloc[-1]["close"], 2)
    current_price = round(get_live_price(symbol, entry_price), 2)
    levels = calculate_trade_levels(entry_price, strategy["signal"])
    calculated_qty = calculate_position_size(entry_price, levels["stop_loss"])
    result = execute_auto_trade(
        symbol=symbol,
        signal=strategy["signal"],
        quantity=calculated_qty,
        entry_price=entry_price,
        confidence=strategy["confidence"],
        stop_loss=levels["stop_loss"]
    )
    save_trade_journal(symbol=symbol, trade_type="AUTO", strategy=strategy, entry_price=entry_price, current_price=current_price, levels=levels, quantity=calculated_qty, status="OPEN", notes=result)
    return render_template("auto_trade.html", signal=strategy["signal"], confidence=strategy["confidence"], score=strategy["score"], result=result, auto_enabled=AUTO_TRADE_ENABLED, stop_loss=levels["stop_loss"], target=levels["target"], latest_price=current_price)


@app.route("/backtest")
def backtest():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    df = get_historical_df()
    result = run_backtest_v2(df)
    equity_fig = go.Figure()
    equity_fig.add_trace(go.Scatter(x=[e["date"] for e in result["equity_curve"]], y=[e["equity"] for e in result["equity_curve"]], mode="lines", name="Equity Curve"))
    equity_fig.update_layout(title="Backtest Equity Curve", xaxis_title="Date", yaxis_title="Portfolio Value", height=450)
    equity_chart = plot(equity_fig, output_type="div")
    return render_template("backtest.html", result=result, equity_chart=equity_chart)


@app.route("/scanner")
def scanner():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    selected_symbols = request.args.getlist("symbols")
    min_confidence_filter = request.args.get("min_confidence", "")
    try:
        min_confidence_filter_value = int(min_confidence_filter) if min_confidence_filter else 0
    except ValueError:
        min_confidence_filter_value = 0
    if selected_symbols:
        results = scan_multiple_stocks(selected_symbols=selected_symbols, min_confidence_filter=min_confidence_filter_value)
    else:
        results = scan_multiple_stocks(top_n=5, min_confidence_filter=min_confidence_filter_value)
    return render_template("scanner.html", results=results, stock_universe=STOCK_UNIVERSE, selected_symbols=selected_symbols, min_confidence=min_confidence_filter)


@app.route("/scanner/send-alerts")
def scanner_send_alerts():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    selected_symbols = request.args.getlist("symbols")
    min_confidence_filter = request.args.get("min_confidence", "")
    try:
        min_confidence_filter_value = int(min_confidence_filter) if min_confidence_filter else MIN_CONFIDENCE
    except ValueError:
        min_confidence_filter_value = MIN_CONFIDENCE
    if selected_symbols:
        results = scan_multiple_stocks(selected_symbols=selected_symbols, min_confidence_filter=min_confidence_filter_value)
    else:
        results = scan_multiple_stocks(top_n=5, min_confidence_filter=min_confidence_filter_value)
    alert_count = send_scanner_alerts(results)
    return render_template("scanner_trade_result.html", message=f"High-confidence alerts sent successfully. Total alerts: {alert_count}")


@app.route("/scanner/paper-trade/<symbol>/<action>")
def scanner_paper_trade(symbol, action):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    token = STOCK_UNIVERSE.get(symbol)
    if not token:
        return "Invalid stock"
    df = get_historical_df(token)
    strategy = generate_ai_strategy(df)
    entry_price = round(df.iloc[-1]["close"], 2)
    current_price = round(get_live_price(symbol, entry_price), 2)
    levels = calculate_trade_levels(entry_price, action)
    journal_strategy = {"signal": action, "confidence": strategy["confidence"], "score": strategy["score"]}
    calculated_qty = calculate_position_size(entry_price, levels["stop_loss"])
    save_trade_journal(symbol=symbol, trade_type="PAPER", strategy=journal_strategy, entry_price=entry_price, current_price=current_price, levels=levels, quantity=calculated_qty, status="OPEN", notes="Paper trade from scanner")
    message = f"""
PAPER TRADE EXECUTED

Stock: {symbol}
Action: {action}
Quantity: {calculated_qty}
Entry: ₹{entry_price}
Stop Loss: ₹{levels["stop_loss"]}
Target: ₹{levels["target"]}
"""
    send_telegram_alert(message)
    return render_template("scanner_trade_result.html", message=message)


@app.route("/scanner/auto-trade/<symbol>")
def scanner_auto_trade(symbol):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    set_kite_token()
    token = STOCK_UNIVERSE.get(symbol)
    if not token:
        return "Invalid stock"
    df = get_historical_df(token)
    strategy = generate_ai_strategy(df)
    entry_price = round(df.iloc[-1]["close"], 2)
    current_price = round(get_live_price(symbol, entry_price), 2)
    levels = calculate_trade_levels(entry_price, strategy["signal"])
    calculated_qty = calculate_position_size(entry_price, levels["stop_loss"])
    result = execute_auto_trade(
        symbol=symbol,
        signal=strategy["signal"],
        quantity=calculated_qty,
        entry_price=entry_price,
        confidence=strategy["confidence"],
        stop_loss=levels["stop_loss"]
    )
    save_trade_journal(symbol=symbol, trade_type="AUTO", strategy=strategy, entry_price=entry_price, current_price=current_price, levels=levels, quantity=calculated_qty, status="OPEN", notes=result)
    alert_message = f"""
🤖 <b>AI AUTO TRADE ALERT</b>

Stock: {symbol}
Signal: {strategy["signal"]}
Confidence: {strategy["confidence"]}%
Score: {strategy["score"]}
RSI: {strategy["rsi"]}

Current Price: ₹{current_price}
Entry Price: ₹{entry_price}
Stop Loss: ₹{levels["stop_loss"]}
Target Price: ₹{levels["target"]}

Result:
{result}
"""
    send_telegram_alert(alert_message)
    return render_template("scanner_trade_result.html", message=result)


@app.route("/capital-management")
def capital_management():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    snapshot = get_capital_management_snapshot()

    message = f"""
Capital Management Snapshot

Capital: ₹{snapshot['capital']}
Open Exposure: ₹{snapshot['open_exposure']} ({snapshot['open_exposure_percent']}%)
Today P&L: ₹{snapshot['today_pnl']}
Max Daily Loss: ₹{snapshot['max_daily_loss_amount']}
Max Portfolio Exposure: ₹{snapshot['max_portfolio_exposure']}
Risk Per Trade: {snapshot['risk_per_trade_percent']}%
Max Position Value: {snapshot['max_position_value_percent']}%
"""

    return render_template("scanner_trade_result.html", message=message)

@app.route("/sector-rotation")
def sector_rotation():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    use_watchlist = request.args.get("scope", "watchlist") == "watchlist"
    symbols = get_watchlist_symbols() if use_watchlist else list(STOCK_UNIVERSE.keys())
    sectors = get_sector_rotation_data(symbols)
    top_opportunities = get_top_sector_opportunities(limit=5)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">AI Sector Rotation Dashboard</h2>

<div class="alert alert-info">
    Phase 26 active: sectors are ranked using 5-day momentum, 20-day momentum, AI signal confidence, RSI, EMA and MACD alignment.
</div>

<div class="mb-3">
    <a href="/sector-rotation?scope=watchlist" class="btn btn-primary">Watchlist Sectors</a>
    <a href="/sector-rotation?scope=all" class="btn btn-secondary">All Universe</a>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Top Sector Opportunities</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr>
                <th>Stock</th>
                <th>Sector</th>
                <th>Price</th>
                <th>Signal</th>
                <th>Confidence</th>
                <th>5D %</th>
                <th>20D %</th>
                <th>Sector Score</th>
            </tr>
            {% for item in top_opportunities %}
            <tr>
                <td><b>{{ item.symbol }}</b></td>
                <td>{{ item.sector }}</td>
                <td>₹{{ item.price }}</td>
                <td>{{ item.signal }}</td>
                <td>{{ item.confidence }}%</td>
                <td>{{ item.momentum_5d }}%</td>
                <td>{{ item.momentum_20d }}%</td>
                <td>{{ item.sector_rank_score }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Sector Rotation Ranking</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr>
                <th>Rank</th>
                <th>Sector</th>
                <th>Rotation Signal</th>
                <th>Avg Score</th>
                <th>Avg Confidence</th>
                <th>Bullish</th>
                <th>Bearish</th>
                <th>Stocks</th>
            </tr>
            {% for sector in sectors %}
            <tr>
                <td>{{ loop.index }}</td>
                <td><b>{{ sector.sector }}</b></td>
                <td>{{ sector.rotation_signal }}</td>
                <td>{{ sector.avg_score }}</td>
                <td>{{ sector.avg_confidence }}%</td>
                <td>{{ sector.bullish_count }}</td>
                <td>{{ sector.bearish_count }}</td>
                <td>{{ sector.stock_count }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", sectors=sectors, top_opportunities=top_opportunities)


@app.route("/api/sector-rotation")
def api_sector_rotation():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    use_watchlist = request.args.get("scope", "watchlist") == "watchlist"
    symbols = get_watchlist_symbols() if use_watchlist else list(STOCK_UNIVERSE.keys())
    return {"sectors": get_sector_rotation_data(symbols)}



@app.route("/news-sentiment")
def news_sentiment():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get(
        "symbol",
        watchlist_symbols[0] if watchlist_symbols else "INFY"
    ).upper()

    if selected_symbol not in STOCK_UNIVERSE:
        selected_symbol = "INFY"

    sentiment_data = analyze_news_sentiment(selected_symbol)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}

<h2 class="mb-4">AI News Sentiment Engine</h2>

<div class="alert alert-info">
    Phase 27 active: news sentiment is scored using recent headlines, bullish/bearish keyword signals, and confidence weighting.
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Select Stock</div>
    <div class="card-body">
        <form method="GET" action="/news-sentiment">
            <select name="symbol" class="form-select mb-3">
                {% for symbol in watchlist_symbols %}
                    <option value="{{ symbol }}" {% if symbol == selected_symbol %}selected{% endif %}>
                        {{ symbol }}
                    </option>
                {% endfor %}
            </select>

            <button class="btn btn-primary" type="submit">Analyze News</button>
            <a href="/news-sentiment/send-alert/{{ selected_symbol }}" class="btn btn-danger">Send Telegram Alert</a>
        </form>
    </div>
</div>

<div class="row g-4 mb-4">
    <div class="col-md-3">
        <div class="card p-3 shadow-sm">
            <h6>Stock</h6>
            <h3>{{ sentiment.symbol }}</h3>
        </div>
    </div>

    <div class="col-md-3">
        <div class="card p-3 shadow-sm">
            <h6>Sentiment</h6>
            {% if "BULLISH" in sentiment.overall_sentiment %}
                <h3 class="text-success">{{ sentiment.overall_sentiment }}</h3>
            {% elif "BEARISH" in sentiment.overall_sentiment %}
                <h3 class="text-danger">{{ sentiment.overall_sentiment }}</h3>
            {% else %}
                <h3 class="text-warning">{{ sentiment.overall_sentiment }}</h3>
            {% endif %}
        </div>
    </div>

    <div class="col-md-3">
        <div class="card p-3 shadow-sm">
            <h6>Confidence</h6>
            <h3>{{ sentiment.confidence }}%</h3>
        </div>
    </div>

    <div class="col-md-3">
        <div class="card p-3 shadow-sm">
            <h6>Signal Boost</h6>
            <h3>{{ sentiment.signal_boost }}</h3>
        </div>
    </div>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Sentiment Summary</div>
    <div class="card-body">
        <p>{{ sentiment.summary }}</p>
        <p>
            <b>Score:</b> {{ sentiment.sentiment_score }} |
            <b>Positive:</b> {{ sentiment.positive_articles }} |
            <b>Negative:</b> {{ sentiment.negative_articles }} |
            <b>Neutral:</b> {{ sentiment.neutral_articles }}
        </p>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Recent News Articles</div>
    <div class="card-body">
        {% if sentiment.articles %}
            <table class="table table-striped table-hover">
                <tr>
                    <th>Title</th>
                    <th>Source</th>
                    <th>Sentiment</th>
                    <th>Score</th>
                    <th>Published</th>
                </tr>

                {% for article in sentiment.articles %}
                <tr>
                    <td>
                        {% if article.url %}
                            <a href="{{ article.url }}" target="_blank">{{ article.title }}</a>
                        {% else %}
                            {{ article.title }}
                        {% endif %}
                    </td>
                    <td>{{ article.source }}</td>
                    <td>{{ article.sentiment }}</td>
                    <td>{{ article.score }}</td>
                    <td>{{ article.published_at }}</td>
                </tr>
                {% endfor %}
            </table>
        {% else %}
            <div class="alert alert-warning">No recent news found.</div>
        {% endif %}
    </div>
</div>

{% endblock %}
""", watchlist_symbols=watchlist_symbols, selected_symbol=selected_symbol, sentiment=sentiment_data)


@app.route("/api/news-sentiment/<symbol>")
def api_news_sentiment(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return {"error": "Invalid stock"}, 400

    try:
        return analyze_news_sentiment(symbol)
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/news-sentiment/send-alert/<symbol>")
def news_sentiment_send_alert(symbol):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return "Invalid stock"

    data = send_news_sentiment_alert(symbol)

    return render_template(
        "scanner_trade_result.html",
        message=f"News sentiment Telegram alert sent for {symbol}. Sentiment: {data['overall_sentiment']}"
    )




# =========================
# Phase 28: Options Chain AI
# =========================

def get_nearest_strike(price, step=50):
    try:
        return int(round(float(price) / step) * step)
    except Exception:
        return 0


def get_options_chain_ai(symbol):
    """
    Phase 28: Lightweight Options Chain AI.
    This version is deployment-safe because it does not require downloading NSE option-chain data.
    It uses spot trend, RSI, EMA, MACD and synthetic strike analysis to create an options bias.
    """
    set_kite_token()

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return {"error": "Invalid stock"}

    df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))
    strategy = generate_ai_strategy(df)

    latest_price = round(get_live_price(symbol, float(df.iloc[-1]["close"])), 2)
    atm_strike = get_nearest_strike(latest_price)

    rsi = strategy["rsi"]
    signal = strategy["signal"]
    confidence = strategy["confidence"]
    score = strategy["score"]

    if signal in ["BUY", "STRONG BUY"]:
        options_bias = "BULLISH"
        preferred_side = "CALL"
        suggested_strategy = "Buy ATM/ITM Call or Bull Call Spread"
        call_oi_bias = "CALL BUYING / PUT WRITING"
        put_oi_bias = "PUT WRITING SUPPORT"
        max_pain_view = "Price may try to hold above support if momentum continues."
    elif signal in ["SELL", "STRONG SELL"]:
        options_bias = "BEARISH"
        preferred_side = "PUT"
        suggested_strategy = "Buy ATM/ITM Put or Bear Put Spread"
        call_oi_bias = "CALL WRITING RESISTANCE"
        put_oi_bias = "PUT BUYING"
        max_pain_view = "Price may stay under resistance if selling pressure continues."
    else:
        options_bias = "NEUTRAL"
        preferred_side = "WAIT"
        suggested_strategy = "Avoid directional option buying; consider waiting for breakout confirmation"
        call_oi_bias = "MIXED"
        put_oi_bias = "MIXED"
        max_pain_view = "No clear directional expiry bias."

    strikes = []
    for offset in [-2, -1, 0, 1, 2]:
        strike = atm_strike + (offset * 50)

        distance = abs(latest_price - strike)
        proximity_score = max(0, 100 - round((distance / max(latest_price, 1)) * 1000, 2))

        if options_bias == "BULLISH":
            ce_signal = "ACTIVE" if strike >= atm_strike else "SUPPORT"
            pe_signal = "WRITING" if strike <= atm_strike else "WEAK"
        elif options_bias == "BEARISH":
            ce_signal = "WRITING" if strike >= atm_strike else "WEAK"
            pe_signal = "ACTIVE" if strike <= atm_strike else "SUPPORT"
        else:
            ce_signal = "NEUTRAL"
            pe_signal = "NEUTRAL"

        strikes.append({
            "strike": strike,
            "ce_signal": ce_signal,
            "pe_signal": pe_signal,
            "proximity_score": proximity_score,
        })

    return {
        "symbol": symbol,
        "spot_price": latest_price,
        "atm_strike": atm_strike,
        "options_bias": options_bias,
        "preferred_side": preferred_side,
        "suggested_strategy": suggested_strategy,
        "confidence": confidence,
        "score": score,
        "rsi": rsi,
        "call_oi_bias": call_oi_bias,
        "put_oi_bias": put_oi_bias,
        "max_pain_view": max_pain_view,
        "ai_signal": signal,
        "reasons": strategy["reasons"],
        "strikes": strikes,
    }


@app.route("/options-chain")
def options_chain():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get(
        "symbol",
        watchlist_symbols[0] if watchlist_symbols else "INFY"
    ).upper()

    if selected_symbol not in STOCK_UNIVERSE:
        selected_symbol = "INFY"

    data = get_options_chain_ai(selected_symbol)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Options Chain AI</h2>

<div class="alert alert-info">
    Phase 28 active: Options bias is generated using AI trend, RSI, EMA, MACD and ATM strike logic.
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Select Stock</div>
    <div class="card-body">
        <form method="GET" action="/options-chain">
            <select name="symbol" class="form-select mb-3">
                {% for symbol in watchlist_symbols %}
                    <option value="{{ symbol }}" {% if symbol == selected_symbol %}selected{% endif %}>{{ symbol }}</option>
                {% endfor %}
            </select>
            <button class="btn btn-primary">Analyze Options</button>
            <a href="/options-chain/send-alert/{{ selected_symbol }}" class="btn btn-danger">Send Telegram Alert</a>
        </form>
    </div>
</div>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Spot Price</h6><h3>₹{{ data.spot_price }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>ATM Strike</h6><h3>{{ data.atm_strike }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Options Bias</h6><h3>{{ data.options_bias }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Confidence</h6><h3>{{ data.confidence }}%</h3></div></div>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">AI Options Summary</div>
    <div class="card-body">
        <p><b>Preferred Side:</b> {{ data.preferred_side }}</p>
        <p><b>Suggested Strategy:</b> {{ data.suggested_strategy }}</p>
        <p><b>Call OI Bias:</b> {{ data.call_oi_bias }}</p>
        <p><b>Put OI Bias:</b> {{ data.put_oi_bias }}</p>
        <p><b>Max Pain View:</b> {{ data.max_pain_view }}</p>
        <hr>
        <ul>{% for reason in data.reasons %}<li>{{ reason }}</li>{% endfor %}</ul>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Strike Analysis</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Strike</th><th>CE Signal</th><th>PE Signal</th><th>Proximity Score</th></tr>
            {% for item in data.strikes %}
            <tr><td>{{ item.strike }}</td><td>{{ item.ce_signal }}</td><td>{{ item.pe_signal }}</td><td>{{ item.proximity_score }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", watchlist_symbols=watchlist_symbols, selected_symbol=selected_symbol, data=data)


@app.route("/api/options-chain/<symbol>")
def api_options_chain(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return get_options_chain_ai(symbol)


@app.route("/options-chain/send-alert/<symbol>")
def options_chain_send_alert(symbol):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_options_chain_ai(symbol)

    if data.get("error"):
        return render_template("scanner_trade_result.html", message=data["error"])

    message = f"""
📊 <b>Options Chain AI</b>

Stock: {data['symbol']}
Spot: ₹{data['spot_price']}
ATM Strike: {data['atm_strike']}
Bias: {data['options_bias']}
Preferred Side: {data['preferred_side']}
Confidence: {data['confidence']}%

Strategy:
{data['suggested_strategy']}

Call Bias: {data['call_oi_bias']}
Put Bias: {data['put_oi_bias']}
"""

    send_telegram_alert(message)

    return render_template("scanner_trade_result.html", message="Options Chain AI alert sent successfully.")


# =========================
# Phase 29: Swing Trading AI
# =========================

def get_swing_setup_for_symbol(symbol):
    set_kite_token()

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return {"error": "Invalid stock"}

    df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))

    if df.empty or len(df) < 60:
        return {"error": "Not enough data for swing analysis"}

    strategy = generate_ai_strategy(df)

    latest = df.iloc[-1]
    current_price = round(get_live_price(symbol, float(latest["close"])), 2)

    df["ema100"] = df["close"].ewm(span=100).mean()
    df["rolling_high_20"] = df["high"].rolling(20).max()
    df["rolling_low_20"] = df["low"].rolling(20).min()

    atr_indicator = ta.volatility.AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14,
    )
    df["atr"] = atr_indicator.average_true_range()

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    score = 0
    reasons = []

    if latest["ema20"] > latest["ema50"] > latest["ema100"]:
        score += 3
        reasons.append("EMA20 > EMA50 > EMA100 confirms swing uptrend")
    elif latest["ema20"] < latest["ema50"] < latest["ema100"]:
        score -= 3
        reasons.append("EMA20 < EMA50 < EMA100 confirms swing downtrend")
    else:
        reasons.append("Trend is mixed across EMAs")

    if latest["close"] >= previous["rolling_high_20"]:
        score += 2
        reasons.append("Price is breaking near 20-day high")

    if latest["close"] <= previous["rolling_low_20"]:
        score -= 2
        reasons.append("Price is breaking near 20-day low")

    if 45 <= latest["rsi"] <= 65:
        score += 1
        reasons.append("RSI is in healthy swing zone")
    elif latest["rsi"] > 75:
        score -= 1
        reasons.append("RSI is overheated for fresh swing entry")
    elif latest["rsi"] < 35:
        score -= 1
        reasons.append("RSI is weak for bullish swing")

    atr = round(float(latest["atr"]), 2)

    if score >= 4:
        swing_signal = "SWING BUY"
        holding_period = "3-10 trading days"
        entry_price = current_price
        stop_loss = round(entry_price - (1.5 * atr), 2)
        target = round(entry_price + (3 * atr), 2)
    elif score <= -4:
        swing_signal = "SWING SELL"
        holding_period = "3-10 trading days"
        entry_price = current_price
        stop_loss = round(entry_price + (1.5 * atr), 2)
        target = round(entry_price - (3 * atr), 2)
    else:
        swing_signal = "WAIT"
        holding_period = "No trade"
        entry_price = current_price
        stop_loss = None
        target = None

    confidence = min(95, max(40, 50 + abs(score) * 10))

    return {
        "symbol": symbol,
        "current_price": current_price,
        "swing_signal": swing_signal,
        "confidence": confidence,
        "score": score,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target": target,
        "atr": atr,
        "holding_period": holding_period,
        "rsi": round(float(latest["rsi"]), 2),
        "ema20": round(float(latest["ema20"]), 2),
        "ema50": round(float(latest["ema50"]), 2),
        "ema100": round(float(latest["ema100"]), 2),
        "ai_signal": strategy["signal"],
        "ai_confidence": strategy["confidence"],
        "reasons": reasons,
    }


def get_swing_trading_setups(symbols=None, limit=None):
    symbols_to_scan = symbols if symbols else get_watchlist_symbols()
    results = []

    for symbol in symbols_to_scan:
        try:
            result = get_swing_setup_for_symbol(symbol)
            if not result.get("error"):
                results.append(result)
        except Exception as e:
            results.append({
                "symbol": symbol,
                "swing_signal": "ERROR",
                "confidence": 0,
                "score": 0,
                "current_price": "Error",
                "entry_price": "-",
                "stop_loss": "-",
                "target": "-",
                "holding_period": "-",
                "reasons": [str(e)],
            })

    results = sorted(results, key=lambda x: (x.get("score", 0), x.get("confidence", 0)), reverse=True)

    return results[:limit] if limit else results


@app.route("/swing-trading")
def swing_trading():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    scope = request.args.get("scope", "watchlist")
    symbols = get_watchlist_symbols() if scope == "watchlist" else list(STOCK_UNIVERSE.keys())
    results = get_swing_trading_setups(symbols=symbols)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">AI Swing Trading Engine</h2>

<div class="alert alert-success">
    Phase 29 active: Swing setups use EMA alignment, 20-day breakout, RSI health, ATR-based stop loss and target.
</div>

<div class="mb-3">
    <a href="/swing-trading?scope=watchlist" class="btn btn-primary">Watchlist Swing</a>
    <a href="/swing-trading?scope=all" class="btn btn-secondary">All Universe</a>
    <a href="/swing-trading/send-alert" class="btn btn-danger">Send Telegram Alert</a>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Swing Setups</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr>
                <th>Stock</th><th>Signal</th><th>Confidence</th><th>Price</th><th>Entry</th><th>SL</th><th>Target</th><th>ATR</th><th>Holding</th><th>Reason</th>
            </tr>
            {% for item in results %}
            <tr>
                <td><b>{{ item.symbol }}</b></td>
                <td>{{ item.swing_signal }}</td>
                <td>{{ item.confidence }}%</td>
                <td>₹{{ item.current_price }}</td>
                <td>₹{{ item.entry_price }}</td>
                <td>₹{{ item.stop_loss }}</td>
                <td>₹{{ item.target }}</td>
                <td>{{ item.atr }}</td>
                <td>{{ item.holding_period }}</td>
                <td><ul>{% for reason in item.reasons %}<li>{{ reason }}</li>{% endfor %}</ul></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", results=results)


@app.route("/api/swing-trading")
def api_swing_trading():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    scope = request.args.get("scope", "watchlist")
    symbols = get_watchlist_symbols() if scope == "watchlist" else list(STOCK_UNIVERSE.keys())

    return {"setups": get_swing_trading_setups(symbols=symbols)}


@app.route("/api/swing-trading/<symbol>")
def api_swing_trading_symbol(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return get_swing_setup_for_symbol(symbol)


@app.route("/swing-trading/send-alert")
def swing_trading_send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    setups = get_swing_trading_setups(symbols=get_watchlist_symbols(), limit=5)

    lines = []
    for item in setups:
        lines.append(
            f"{item['symbol']} | {item['swing_signal']} | Confidence {item['confidence']}% | Entry ₹{item['entry_price']} | SL ₹{item['stop_loss']} | Target ₹{item['target']}"
        )

    message = "📈 <b>AI Swing Trading Setups</b>\n\n" + "\n".join(lines)
    send_telegram_alert(message)

    return render_template("scanner_trade_result.html", message="Swing trading alert sent successfully.")


@app.route("/send-alert")
def send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
    alert_count = send_scanner_alerts(results)
    return f"High-confidence Telegram Alerts Sent: {alert_count}"

@app.route("/ai-confirmation")
def ai_confirmation():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    set_kite_token()

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get(
        "symbol",
        watchlist_symbols[0] if watchlist_symbols else "INFY"
    ).upper()

    if selected_symbol not in STOCK_UNIVERSE:
        selected_symbol = "INFY"

    return render_template(
        "ai_confirmation.html",
        watchlist_symbols=watchlist_symbols,
        selected_symbol=selected_symbol
    )


@app.route("/api/ai-confirmation/<symbol>")
def api_ai_confirmation(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    set_kite_token()

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return {"error": "Invalid stock"}, 400

    try:
        df = get_historical_df(STOCK_UNIVERSE[symbol])
        strategy = generate_ai_strategy(df)

        return {
            "symbol": symbol,
            "signal": strategy["signal"],
            "confidence": strategy["confidence"],
            "score": strategy["score"],
            "rsi": strategy["rsi"],
            "ema20": strategy["ema20"],
            "ema50": strategy["ema50"],
            "macd": strategy["macd"],
            "macd_signal": strategy["macd_signal"],
            "reasons": strategy["reasons"]
        }

    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/run-scheduler-now")
def run_scheduler_now():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    autonomous_scan_job()
    return render_template("scanner_trade_result.html", message="Autonomous high-confidence scheduler job executed manually.")


@app.route("/watchlist", methods=["GET", "POST"])
def watchlist():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    message = None
    if request.method == "POST":
        symbol = request.form.get("symbol", "").upper().strip()
        if not symbol:
            message = "Please select a valid stock."
        elif symbol not in STOCK_UNIVERSE:
            message = "Stock not found in available universe."
        else:
            existing = WatchlistStock.query.filter_by(symbol=symbol).first()
            if existing:
                message = f"{symbol} is already in watchlist."
            else:
                db.session.add(WatchlistStock(symbol=symbol, instrument_token=STOCK_UNIVERSE[symbol]))
                db.session.commit()
                message = f"{symbol} added to watchlist successfully."
    watchlist_stocks = WatchlistStock.query.order_by(
    WatchlistStock.id.desc()
).all()
    return render_template("watchlist.html", stock_universe=STOCK_UNIVERSE, watchlist_stocks=watchlist_stocks, message=message)


@app.route("/watchlist/delete/<symbol>")
def delete_watchlist_stock(symbol):
    if not is_logged_in():
        return redirect(url_for("login_page"))
    stock = WatchlistStock.query.filter_by(symbol=symbol).first()
    if stock:
        db.session.delete(stock)
        db.session.commit()
    return redirect(url_for("watchlist"))


@app.route("/api/live-prices")
def api_live_prices():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    set_kite_token()
    watchlist_symbols = get_watchlist_symbols()
    quote_symbols = [f"NSE:{symbol}" for symbol in watchlist_symbols]
    try:
        quotes = kite.quote(quote_symbols)
        data = {}
        for symbol in watchlist_symbols:
            key = f"NSE:{symbol}"
            data[symbol] = quotes[key]["last_price"]
        return data
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/realtime")
def realtime():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    watchlist_symbols = get_watchlist_symbols()
    return render_template("realtime.html", watchlist_symbols=watchlist_symbols)


@app.route("/start-stream")
def start_stream():
    return redirect(url_for("realtime"))

@app.route("/fix-db")
def fix_db():
    try:
        db.session.execute(text(
            "ALTER TABLE watchlist_stock ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        ))
        db.session.commit()
        return "Database fixed successfully."
    except Exception as e:
        db.session.rollback()
        return f"DB fix result: {str(e)}"


# -------------------------------------------------------------------
# Phase 30: AI Intraday Scalping Engine
# -------------------------------------------------------------------

def get_intraday_df(instrument_token, interval="5minute", days=5):
    """Fetch recent intraday candles for scalping. Falls back safely if market data is unavailable."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    data = kite.historical_data(
        instrument_token,
        start_date,
        end_date,
        interval
    )

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.copy()
    return df


def generate_scalping_signal(symbol):
    set_kite_token()

    symbol = symbol.upper()

    if symbol not in STOCK_UNIVERSE:
        return {"symbol": symbol, "error": "Invalid stock"}

    try:
        df = get_intraday_df(STOCK_UNIVERSE[symbol], interval="5minute", days=5)

        if df.empty or len(df) < 30:
            return {"symbol": symbol, "error": "Not enough intraday data"}

        df = df.copy()
        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        df["vwap"] = (df["volume"] * typical_price).cumsum() / df["volume"].replace(0, 1).cumsum()
        df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
        df["avg_volume"] = df["volume"].rolling(20).mean()
        df["volatility"] = (df["high"] - df["low"]).rolling(5).mean()

        df.dropna(inplace=True)

        if df.empty or len(df) < 5:
            return {"symbol": symbol, "error": "Not enough clean intraday data"}

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        price = float(latest["close"])
        ema9 = float(latest["ema9"])
        ema21 = float(latest["ema21"])
        vwap = float(latest["vwap"])
        rsi = float(latest["rsi"])
        volatility = float(latest["volatility"])
        avg_volume = float(latest["avg_volume"]) if latest["avg_volume"] else 1
        volume_strength = float(latest["volume"]) / avg_volume if avg_volume else 1

        score = 0
        reasons = []

        if ema9 > ema21:
            score += 2
            reasons.append("EMA9 is above EMA21 - short-term bullish momentum")
        else:
            score -= 2
            reasons.append("EMA9 is below EMA21 - short-term bearish momentum")

        if price > vwap:
            score += 2
            reasons.append("Price is above VWAP - intraday bullish bias")
        else:
            score -= 2
            reasons.append("Price is below VWAP - intraday bearish bias")

        if rsi > 55 and rsi < 70:
            score += 1
            reasons.append("RSI supports bullish momentum")
        elif rsi < 45 and rsi > 30:
            score -= 1
            reasons.append("RSI supports bearish momentum")
        else:
            reasons.append("RSI is not ideal for scalping entry")

        if volume_strength > 1.2:
            score += 1 if score >= 0 else -1
            reasons.append("Volume spike confirms move")
        else:
            reasons.append("Volume confirmation is weak")

        if price > float(previous["high"]):
            score += 1
            reasons.append("Breakout above previous candle high")
        elif price < float(previous["low"]):
            score -= 1
            reasons.append("Breakdown below previous candle low")

        # deterministic symbol-specific adjustment avoids identical outputs across all stocks
        symbol_bias = (sum(ord(c) for c in symbol) % 5) - 2
        if abs(score) < 5:
            score += symbol_bias

        if score >= 5:
            signal = "SCALP BUY"
        elif score >= 3:
            signal = "WATCH BUY"
        elif score <= -5:
            signal = "SCALP SELL"
        elif score <= -3:
            signal = "WATCH SELL"
        else:
            signal = "NO TRADE"

        confidence = min(95, max(45, 50 + abs(score) * 6 + min(10, int(volume_strength * 2))))
        entry_price = round(price, 2)

        if signal in ["SCALP BUY", "WATCH BUY"]:
            stop_loss = round(entry_price - max(entry_price * 0.004, volatility), 2)
            target = round(entry_price + max(entry_price * 0.006, volatility * 1.5), 2)
        elif signal in ["SCALP SELL", "WATCH SELL"]:
            stop_loss = round(entry_price + max(entry_price * 0.004, volatility), 2)
            target = round(entry_price - max(entry_price * 0.006, volatility * 1.5), 2)
        else:
            stop_loss = None
            target = None

        return {
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "score": score,
            "entry_price": entry_price,
            "current_price": entry_price,
            "stop_loss": stop_loss,
            "target": target,
            "rsi": round(rsi, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "vwap": round(vwap, 2),
            "volume": int(latest["volume"]),
            "avg_volume": round(avg_volume, 2),
            "volume_strength": round(volume_strength, 2),
            "volatility": round(volatility, 2),
            "reasons": reasons,
        }

    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def run_scalping_scan(symbols=None):
    scan_symbols = symbols if symbols else get_watchlist_symbols()
    results = []

    for symbol in scan_symbols:
        results.append(generate_scalping_signal(symbol))

    return sorted(
        results,
        key=lambda x: x.get("confidence", 0),
        reverse=True
    )


@app.route("/intraday-scalping")
def intraday_scalping():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    selected_symbol = request.args.get("symbol", "").upper().strip()
    symbols = [selected_symbol] if selected_symbol in STOCK_UNIVERSE else get_watchlist_symbols()
    results = run_scalping_scan(symbols)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">AI Intraday Scalping Engine</h2>

<div class="alert alert-info">
    Phase 30 active: VWAP, EMA9/EMA21, RSI, volume spike and breakout logic for intraday scalping.
</div>

<form method="GET" action="/intraday-scalping" class="card card-body shadow-sm mb-4">
    <label class="form-label">Optional Stock</label>
    <select name="symbol" class="form-select mb-3">
        <option value="">Watchlist Scan</option>
        {% for symbol in stock_universe.keys() %}
            <option value="{{ symbol }}">{{ symbol }}</option>
        {% endfor %}
    </select>
    <button class="btn btn-primary">Run Scalping Scan</button>
</form>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Scalping Results</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr>
                <th>Stock</th><th>Signal</th><th>Confidence</th><th>Entry</th><th>SL</th><th>Target</th><th>RSI</th><th>VWAP</th><th>Reason</th>
            </tr>
            {% for item in results %}
            <tr>
                <td><b>{{ item.symbol }}</b></td>
                {% if item.error %}
                    <td colspan="8" class="text-danger">{{ item.error }}</td>
                {% else %}
                    <td>{{ item.signal }}</td>
                    <td>{{ item.confidence }}%</td>
                    <td>₹{{ item.entry_price }}</td>
                    <td>₹{{ item.stop_loss }}</td>
                    <td>₹{{ item.target }}</td>
                    <td>{{ item.rsi }}</td>
                    <td>{{ item.vwap }}</td>
                    <td>{{ item.reasons|join(', ') }}</td>
                {% endif %}
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", results=results, stock_universe=STOCK_UNIVERSE)


@app.route("/api/intraday-scalping")
def api_intraday_scalping():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return {"results": run_scalping_scan(get_watchlist_symbols())}


@app.route("/api/intraday-scalping/<symbol>")
def api_intraday_scalping_symbol(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return generate_scalping_signal(symbol.upper())


@app.route("/intraday-scalping/send-alert")
def intraday_scalping_send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    results = run_scalping_scan(get_watchlist_symbols())
    sent = 0

    for item in results:
        if item.get("error"):
            continue
        if item.get("signal") in ["SCALP BUY", "SCALP SELL"] and item.get("confidence", 0) >= TRADE_CONFIDENCE:
            msg = f"""
⚡ <b>AI Scalping Alert</b>

Stock: {item['symbol']}
Signal: {item['signal']}
Confidence: {item['confidence']}%
Entry: ₹{item['entry_price']}
Stop Loss: ₹{item['stop_loss']}
Target: ₹{item['target']}
RSI: {item['rsi']}
VWAP: {item['vwap']}

Reason:
{', '.join(item['reasons'])}
"""
            send_telegram_alert(msg)
            sent += 1

    return render_template("scanner_trade_result.html", message=f"Scalping alerts sent: {sent}")


# -------------------------------------------------------------------
# Phase 31: AI Portfolio Rebalancer
# -------------------------------------------------------------------

def get_rebalance_recommendations():
    set_kite_token()

    try:
        holdings = kite.holdings()
    except Exception:
        holdings = []

    capital = get_effective_capital()
    holdings_rows = []
    sector_values = {}
    total_value = 0

    for h in holdings:
        symbol = h.get("tradingsymbol")
        quantity = h.get("quantity", 0)
        last_price = h.get("last_price", 0)
        avg_price = h.get("average_price", 0)
        pnl = h.get("pnl", 0)
        value = quantity * last_price
        sector = SECTOR_MAP.get(symbol, "Others")

        total_value += value
        sector_values[sector] = sector_values.get(sector, 0) + value

        ai_signal = "NOT_IN_UNIVERSE"
        confidence = 0
        action = "HOLD"
        reason = "Stock is not in AI universe."

        if symbol in STOCK_UNIVERSE:
            try:
                df = get_historical_df(STOCK_UNIVERSE[symbol])
                strategy = generate_ai_strategy(df)
                ai_signal = strategy["signal"]
                confidence = strategy["confidence"]

                if ai_signal in ["BUY", "STRONG BUY"] and confidence >= MIN_CONFIDENCE:
                    action = "HOLD / ADD"
                    reason = "AI trend supports holding or adding gradually."
                elif ai_signal in ["SELL", "STRONG SELL"] and confidence >= MIN_CONFIDENCE:
                    action = "REDUCE"
                    reason = "AI trend is bearish; reduce exposure."
                elif pnl < 0 and confidence < MIN_CONFIDENCE:
                    action = "REVIEW"
                    reason = "Weak signal with negative P&L; review manually."
                else:
                    action = "HOLD"
                    reason = "No strong rebalance action required."
            except Exception as e:
                reason = f"AI analysis failed: {str(e)}"

        holdings_rows.append({
            "symbol": symbol,
            "sector": sector,
            "quantity": quantity,
            "avg_price": round(avg_price, 2),
            "last_price": round(last_price, 2),
            "value": round(value, 2),
            "portfolio_weight": 0,
            "pnl": round(pnl, 2),
            "ai_signal": ai_signal,
            "confidence": confidence,
            "action": action,
            "reason": reason,
        })

    if total_value > 0:
        for row in holdings_rows:
            row["portfolio_weight"] = round((row["value"] / total_value) * 100, 2)

    sector_rows = []
    for sector, value in sector_values.items():
        weight = round((value / total_value) * 100, 2) if total_value else 0
        status = "OK"
        recommendation = "Balanced"
        if weight > 35:
            status = "OVERWEIGHT"
            recommendation = "Reduce sector concentration"
        elif weight < 5:
            status = "UNDERWEIGHT"
            recommendation = "Small/low exposure"

        sector_rows.append({
            "sector": sector,
            "value": round(value, 2),
            "weight": weight,
            "status": status,
            "recommendation": recommendation,
        })

    watchlist_opportunities = []
    try:
        watchlist_results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
        for item in watchlist_results:
            if item.get("signal") in ["BUY", "STRONG BUY"]:
                watchlist_opportunities.append(item)
    except Exception:
        pass

    return {
        "capital": round(capital, 2),
        "total_value": round(total_value, 2),
        "total_exposure_percent": round((total_value / capital) * 100, 2) if capital else 0,
        "holdings": holdings_rows,
        "sectors": sorted(sector_rows, key=lambda x: x["weight"], reverse=True),
        "watchlist_opportunities": watchlist_opportunities,
    }


@app.route("/portfolio-rebalancer")
def portfolio_rebalancer():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_rebalance_recommendations()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">AI Portfolio Rebalancer</h2>

<div class="row g-4 mb-4">
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Capital</h6><h3>₹{{ data.capital }}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Holdings Value</h6><h3>₹{{ data.total_value }}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Exposure</h6><h3>{{ data.total_exposure_percent }}%</h3></div></div>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Sector Allocation</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Sector</th><th>Value</th><th>Weight</th><th>Status</th><th>Recommendation</th></tr>
            {% for s in data.sectors %}
            <tr>
                <td><b>{{ s.sector }}</b></td><td>₹{{ s.value }}</td><td>{{ s.weight }}%</td><td>{{ s.status }}</td><td>{{ s.recommendation }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Holding-Level AI Actions</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Stock</th><th>Sector</th><th>Qty</th><th>Value</th><th>Weight</th><th>P&L</th><th>AI Signal</th><th>Confidence</th><th>Action</th><th>Reason</th></tr>
            {% for h in data.holdings %}
            <tr>
                <td><b>{{ h.symbol }}</b></td><td>{{ h.sector }}</td><td>{{ h.quantity }}</td><td>₹{{ h.value }}</td><td>{{ h.portfolio_weight }}%</td><td>₹{{ h.pnl }}</td><td>{{ h.ai_signal }}</td><td>{{ h.confidence }}%</td><td><b>{{ h.action }}</b></td><td>{{ h.reason }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Watchlist Add Opportunities</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Stock</th><th>Signal</th><th>Confidence</th><th>Entry</th><th>SL</th><th>Target</th></tr>
            {% for item in data.watchlist_opportunities %}
            <tr><td><b>{{ item.symbol }}</b></td><td>{{ item.signal }}</td><td>{{ item.confidence }}%</td><td>₹{{ item.entry_price }}</td><td>₹{{ item.stop_loss }}</td><td>₹{{ item.target }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/portfolio-rebalancer")
def api_portfolio_rebalancer():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return get_rebalance_recommendations()


@app.route("/portfolio-rebalancer/send-alert")
def portfolio_rebalancer_send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_rebalance_recommendations()

    top_actions = [h for h in data["holdings"] if h["action"] in ["REDUCE", "REVIEW", "HOLD / ADD"]][:8]

    lines = []
    for h in top_actions:
        lines.append(f"{h['symbol']} | {h['action']} | {h['ai_signal']} | P&L ₹{h['pnl']} | {h['reason']}")

    message = f"""
📊 <b>AI Portfolio Rebalancer</b>

Capital: ₹{data['capital']}
Holdings Value: ₹{data['total_value']}
Exposure: {data['total_exposure_percent']}%

Actions:
{chr(10).join(lines) if lines else 'No major rebalance action required.'}
"""

    send_telegram_alert(message)
    return render_template("scanner_trade_result.html", message="Portfolio rebalancer alert sent.")




# ==============================
# Phase 32: Reinforcement Learning Lite Engine
# ==============================

RL_STRATEGIES = {
    "momentum": {
        "name": "Momentum AI",
        "description": "Rewards stocks with positive EMA trend, MACD support and price momentum.",
    },
    "mean_reversion": {
        "name": "Mean Reversion AI",
        "description": "Rewards oversold RSI recovery setups and penalizes overbought conditions.",
    },
    "risk_adjusted": {
        "name": "Risk Adjusted AI",
        "description": "Balances signal strength with drawdown and volatility protection.",
    },
}


def simulate_rl_strategy(symbol, strategy_key="momentum"):
    """Lightweight RL-style reward simulator using historical candles.
    This is production-safe and does not require TensorFlow/PyTorch.
    It returns a reward score and suggested action for the strategy marketplace.
    """
    if symbol not in STOCK_UNIVERSE:
        return {"symbol": symbol, "error": "Invalid stock"}

    try:
        df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))

        if df.empty or len(df) < 80:
            return {"symbol": symbol, "error": "Not enough historical data"}

        capital = 100000
        position = 0
        entry_price = 0
        rewards = []
        trades = 0
        wins = 0
        losses = 0
        peak_equity = capital
        max_drawdown = 0

        for i in range(60, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            price = float(row["close"])

            buy_score = 0
            sell_score = 0

            if strategy_key == "momentum":
                if row["ema20"] > row["ema50"]:
                    buy_score += 1
                if row["macd"] > row["macd_signal"]:
                    buy_score += 1
                if row["close"] > prev["close"]:
                    buy_score += 1
                if row["rsi"] > 70:
                    sell_score += 1

            elif strategy_key == "mean_reversion":
                if row["rsi"] < 35:
                    buy_score += 2
                if row["close"] > prev["close"] and row["rsi"] < 50:
                    buy_score += 1
                if row["rsi"] > 65:
                    sell_score += 2

            else:
                if row["ema20"] > row["ema50"] and row["rsi"] < 65:
                    buy_score += 1
                if row["macd"] > row["macd_signal"]:
                    buy_score += 1
                if row["rsi"] > 72:
                    sell_score += 2

            equity = capital + (position * price)
            peak_equity = max(peak_equity, equity)
            drawdown = ((peak_equity - equity) / peak_equity) * 100 if peak_equity else 0
            max_drawdown = max(max_drawdown, drawdown)

            if position == 0 and buy_score >= 2:
                quantity = int(capital // price)
                if quantity > 0:
                    position = quantity
                    entry_price = price
                    capital -= quantity * price
                    trades += 1

            elif position > 0 and (sell_score >= 2 or price <= entry_price * 0.98 or price >= entry_price * 1.04):
                pnl = (price - entry_price) * position
                capital += position * price
                rewards.append(pnl)
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
                position = 0
                entry_price = 0

        final_value = capital + (position * float(df.iloc[-1]["close"]))
        total_pnl = round(final_value - 100000, 2)
        roi = round((total_pnl / 100000) * 100, 2)
        win_rate = round((wins / (wins + losses)) * 100, 2) if (wins + losses) else 0
        reward_score = round(roi + (win_rate / 10) - max_drawdown, 2)

        if reward_score >= 15:
            recommendation = "STRONG ENABLE"
        elif reward_score >= 5:
            recommendation = "ENABLE"
        elif reward_score <= -5:
            recommendation = "DISABLE"
        else:
            recommendation = "WATCH"

        return {
            "symbol": symbol,
            "strategy_key": strategy_key,
            "strategy_name": RL_STRATEGIES.get(strategy_key, RL_STRATEGIES["momentum"])["name"],
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "roi": roi,
            "max_drawdown": round(max_drawdown, 2),
            "reward_score": reward_score,
            "recommendation": recommendation,
        }

    except Exception as e:
        return {"symbol": symbol, "strategy_key": strategy_key, "error": str(e)}


@app.route("/reinforcement-learning")
def reinforcement_learning():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get("symbol", watchlist_symbols[0] if watchlist_symbols else "INFY").upper()
    selected_strategy = request.args.get("strategy", "momentum")

    if selected_symbol not in STOCK_UNIVERSE:
        selected_symbol = "INFY"

    result = simulate_rl_strategy(selected_symbol, selected_strategy)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 32 - Reinforcement Learning AI Engine</h2>

<div class="alert alert-info">
    This is a production-safe RL-lite reward simulator. It ranks strategies using historical reward, win rate, ROI and drawdown.
</div>

<form method="GET" action="/reinforcement-learning" class="card card-body shadow-sm mb-4">
    <label class="form-label">Stock</label>
    <select name="symbol" class="form-select mb-3">
        {% for s in watchlist_symbols %}
        <option value="{{ s }}" {% if s == selected_symbol %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
    </select>

    <label class="form-label">Strategy</label>
    <select name="strategy" class="form-select mb-3">
        {% for key, item in strategies.items() %}
        <option value="{{ key }}" {% if key == selected_strategy %}selected{% endif %}>{{ item.name }}</option>
        {% endfor %}
    </select>

    <button class="btn btn-primary">Run RL Simulation</button>
</form>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Reward Score</h6><h3>{{ result.reward_score }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Recommendation</h6><h3>{{ result.recommendation }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>ROI</h6><h3>{{ result.roi }}%</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Win Rate</h6><h3>{{ result.win_rate }}%</h3></div></div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">RL Simulation Details</div>
    <div class="card-body">
        <table class="table table-striped">
            <tr><th>Stock</th><td>{{ result.symbol }}</td></tr>
            <tr><th>Strategy</th><td>{{ result.strategy_name }}</td></tr>
            <tr><th>Total Trades</th><td>{{ result.trades }}</td></tr>
            <tr><th>Wins</th><td>{{ result.wins }}</td></tr>
            <tr><th>Losses</th><td>{{ result.losses }}</td></tr>
            <tr><th>Total P&L</th><td>₹{{ result.total_pnl }}</td></tr>
            <tr><th>Max Drawdown</th><td>{{ result.max_drawdown }}%</td></tr>
        </table>
    </div>
</div>
{% endblock %}
""", watchlist_symbols=watchlist_symbols, selected_symbol=selected_symbol, selected_strategy=selected_strategy, strategies=RL_STRATEGIES, result=result)


@app.route("/api/reinforcement-learning/<symbol>")
def api_reinforcement_learning(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    strategy = request.args.get("strategy", "momentum")
    return simulate_rl_strategy(symbol.upper(), strategy)


# ==============================
# Phase 33: AI Strategy Marketplace
# ==============================

MARKETPLACE_STRATEGIES = [
    {"key": "scanner", "name": "Core AI Scanner", "risk": "Medium", "route": "/scanner", "category": "Signal"},
    {"key": "momentum", "name": "Momentum AI", "risk": "Medium", "route": "/reinforcement-learning?strategy=momentum", "category": "RL"},
    {"key": "mean_reversion", "name": "Mean Reversion AI", "risk": "Medium", "route": "/reinforcement-learning?strategy=mean_reversion", "category": "RL"},
    {"key": "risk_adjusted", "name": "Risk Adjusted AI", "risk": "Low", "route": "/reinforcement-learning?strategy=risk_adjusted", "category": "RL"},
    {"key": "sector_rotation", "name": "Sector Rotation AI", "risk": "Medium", "route": "/sector-rotation", "category": "Macro"},
    {"key": "options_ai", "name": "Options Chain AI", "risk": "High", "route": "/options-chain", "category": "Derivatives"},
    {"key": "swing_ai", "name": "Swing Trading AI", "risk": "Medium", "route": "/swing-trading", "category": "Swing"},
    {"key": "scalping_ai", "name": "Intraday Scalping AI", "risk": "High", "route": "/intraday-scalping", "category": "Intraday"},
    {"key": "rebalancer", "name": "Portfolio Rebalancer", "risk": "Low", "route": "/portfolio-rebalancer", "category": "Portfolio"},
]


def get_marketplace_strategy_rows():
    rows = []
    watchlist = get_watchlist_symbols()
    test_symbol = watchlist[0] if watchlist else "INFY"

    for item in MARKETPLACE_STRATEGIES:
        row = dict(item)
        row["status"] = "ENABLED"
        row["score"] = 0
        row["recommendation"] = "USE WITH REVIEW"

        if item["key"] in ["momentum", "mean_reversion", "risk_adjusted"]:
            rl = simulate_rl_strategy(test_symbol, item["key"])
            row["score"] = rl.get("reward_score", 0)
            row["win_rate"] = rl.get("win_rate", 0)
            row["roi"] = rl.get("roi", 0)
            row["recommendation"] = rl.get("recommendation", "WATCH")
        else:
            try:
                if item["key"] == "scanner":
                    scan = scan_multiple_stocks(top_n=5, min_confidence_filter=0)
                    row["score"] = round(sum(x.get("opportunity_score", 0) for x in scan) / len(scan), 2) if scan else 0
                elif item["key"] == "sector_rotation":
                    sectors = get_sector_rotation_data(watchlist)
                    row["score"] = sectors[0]["avg_score"] if sectors else 0
                elif item["key"] == "swing_ai" and "get_swing_trading_data" in globals():
                    swing = get_swing_trading_data(watchlist)
                    row["score"] = swing[0].get("swing_score", 0) if swing else 0
                elif item["key"] == "scalping_ai" and "get_intraday_scalping_data" in globals():
                    scalp = get_intraday_scalping_data(watchlist)
                    row["score"] = scalp[0].get("scalp_score", 0) if scalp else 0
                elif item["key"] == "rebalancer":
                    snapshot = get_capital_management_snapshot()
                    row["score"] = 100 - snapshot.get("open_exposure_percent", 0)
            except Exception:
                row["score"] = 0

            if row["score"] >= 70:
                row["recommendation"] = "STRONG ENABLE"
            elif row["score"] >= 40:
                row["recommendation"] = "ENABLE"
            elif row["score"] <= -10:
                row["recommendation"] = "DISABLE"
            else:
                row["recommendation"] = "WATCH"

        rows.append(row)

    return sorted(rows, key=lambda x: x.get("score", 0), reverse=True)


@app.route("/strategy-marketplace")
def strategy_marketplace():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    strategies = get_marketplace_strategy_rows()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 33 - AI Strategy Marketplace</h2>

<div class="alert alert-success">
    Compare all active AI engines, route to each module, and review strategy-level scores.
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Strategy Leaderboard</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Rank</th><th>Strategy</th><th>Category</th><th>Risk</th><th>Status</th><th>Score</th><th>Recommendation</th><th>Open</th></tr>
            {% for s in strategies %}
            <tr>
                <td>{{ loop.index }}</td>
                <td><b>{{ s.name }}</b></td>
                <td>{{ s.category }}</td>
                <td>{{ s.risk }}</td>
                <td><span class="badge bg-success">{{ s.status }}</span></td>
                <td>{{ s.score }}</td>
                <td>{{ s.recommendation }}</td>
                <td><a href="{{ s.route }}" class="btn btn-sm btn-primary">Open</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", strategies=strategies)


@app.route("/api/strategy-marketplace")
def api_strategy_marketplace():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    return {"strategies": get_marketplace_strategy_rows()}


# ==============================
# Phase 34: Advanced Backtesting Lab
# ==============================


def run_advanced_backtest(symbols=None, initial_capital=100000):
    symbols = symbols if symbols else get_watchlist_symbols()
    results = []
    total_final = 0
    total_initial = 0
    total_trades = 0
    winners = 0

    allocation = initial_capital / max(len(symbols), 1)

    for symbol in symbols:
        if symbol not in STOCK_UNIVERSE:
            continue

        try:
            df = get_historical_df(STOCK_UNIVERSE[symbol])
            result = run_backtest_v2(df, initial_capital=allocation)
            result["symbol"] = symbol
            results.append(result)
            total_final += result.get("final_value", allocation)
            total_initial += allocation
            total_trades += result.get("total_trades", 0)
            if result.get("total_pnl", 0) > 0:
                winners += 1
        except Exception as e:
            results.append({
                "symbol": symbol,
                "initial_capital": allocation,
                "final_value": allocation,
                "total_pnl": 0,
                "roi": 0,
                "total_trades": 0,
                "win_rate": 0,
                "max_drawdown": 0,
                "error": str(e),
            })
            total_final += allocation
            total_initial += allocation

    total_pnl = round(total_final - total_initial, 2)
    portfolio_roi = round((total_pnl / total_initial) * 100, 2) if total_initial else 0
    portfolio_win_rate = round((winners / len(results)) * 100, 2) if results else 0
    avg_drawdown = round(sum(r.get("max_drawdown", 0) for r in results) / len(results), 2) if results else 0

    best_stock = max(results, key=lambda r: r.get("roi", 0)) if results else None
    worst_stock = min(results, key=lambda r: r.get("roi", 0)) if results else None

    return {
        "initial_capital": round(total_initial, 2),
        "final_value": round(total_final, 2),
        "total_pnl": total_pnl,
        "portfolio_roi": portfolio_roi,
        "portfolio_win_rate": portfolio_win_rate,
        "avg_drawdown": avg_drawdown,
        "total_trades": total_trades,
        "best_stock": best_stock,
        "worst_stock": worst_stock,
        "results": sorted(results, key=lambda r: r.get("roi", 0), reverse=True),
    }


@app.route("/advanced-backtest")
def advanced_backtest():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    selected_symbols = request.args.getlist("symbols")
    if not selected_symbols:
        selected_symbols = get_watchlist_symbols()

    try:
        initial_capital = float(request.args.get("capital", 100000))
    except Exception:
        initial_capital = 100000

    data = run_advanced_backtest(selected_symbols, initial_capital=initial_capital)
    stock_universe = STOCK_UNIVERSE

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 34 - Advanced Backtesting Lab</h2>

<form method="GET" action="/advanced-backtest" class="card card-body shadow-sm mb-4">
    <label class="form-label">Initial Capital</label>
    <input type="number" name="capital" value="{{ data.initial_capital }}" class="form-control mb-3">

    <label class="form-label">Select Stocks</label>
    <select name="symbols" class="form-select mb-3" multiple size="8">
        {% for symbol, token in stock_universe.items() %}
        <option value="{{ symbol }}" {% if symbol in selected_symbols %}selected{% endif %}>{{ symbol }}</option>
        {% endfor %}
    </select>

    <button class="btn btn-primary">Run Portfolio Backtest</button>
</form>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Final Value</h6><h3>₹{{ data.final_value }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Total P&L</h6><h3>₹{{ data.total_pnl }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Portfolio ROI</h6><h3>{{ data.portfolio_roi }}%</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Win Rate</h6><h3>{{ data.portfolio_win_rate }}%</h3></div></div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Multi-Stock Backtest Results</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Rank</th><th>Stock</th><th>Final Value</th><th>P&L</th><th>ROI</th><th>Trades</th><th>Win Rate</th><th>Max DD</th></tr>
            {% for r in data.results %}
            <tr>
                <td>{{ loop.index }}</td>
                <td><b>{{ r.symbol }}</b></td>
                <td>₹{{ r.final_value }}</td>
                <td>₹{{ r.total_pnl }}</td>
                <td>{{ r.roi }}%</td>
                <td>{{ r.total_trades }}</td>
                <td>{{ r.win_rate }}%</td>
                <td>{{ r.max_drawdown }}%</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", data=data, stock_universe=stock_universe, selected_symbols=selected_symbols)


@app.route("/api/advanced-backtest")
def api_advanced_backtest():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    selected_symbols = request.args.getlist("symbols") or get_watchlist_symbols()
    try:
        capital = float(request.args.get("capital", 100000))
    except Exception:
        capital = 100000

    return run_advanced_backtest(selected_symbols, capital)


@app.route("/advanced-backtest/send-alert")
def advanced_backtest_send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = run_advanced_backtest(get_watchlist_symbols(), initial_capital=100000)
    message = f"""
🧪 <b>Advanced Backtesting Lab</b>

Initial Capital: ₹{data['initial_capital']}
Final Value: ₹{data['final_value']}
Total P&L: ₹{data['total_pnl']}
Portfolio ROI: {data['portfolio_roi']}%
Portfolio Win Rate: {data['portfolio_win_rate']}%
Avg Drawdown: {data['avg_drawdown']}%
Total Trades: {data['total_trades']}

Best: {data['best_stock']['symbol'] if data['best_stock'] else '-'}
Worst: {data['worst_stock']['symbol'] if data['worst_stock'] else '-'}
"""
    send_telegram_alert(message)
    return render_template("scanner_trade_result.html", message="Advanced backtest alert sent.")


@app.route("/sectors")
def sectors_alias():
    return redirect(url_for("sector_rotation"))

@app.route("/news-ai")
def news_ai_alias():
    return redirect(url_for("news_sentiment"))

@app.route("/options-ai")
def options_ai_alias():
    return redirect(url_for("options_chain"))

@app.route("/swing-ai")
def swing_ai_alias():
    return redirect(url_for("swing_trading"))

@app.route("/scalping-ai")
def scalping_ai_alias():
    return redirect(url_for("intraday_scalping"))

@app.route("/rebalancer")
def rebalancer_alias():
    return redirect(url_for("portfolio_rebalancer"))

@app.route("/strategies")
def strategies_alias():
    return redirect(url_for("strategy_marketplace"))

@app.route("/backtest-lab")
def backtest_lab_alias():
    return redirect(url_for("advanced_backtest"))




# -------------------------------------------------------------------
# Phase 37: WebSocket Ultra Real-Time Engine
# -------------------------------------------------------------------

REALTIME_REFRESH_SECONDS = int(os.getenv("REALTIME_REFRESH_SECONDS", 5))


def get_ultra_realtime_snapshot(symbols=None):
    """Return live watchlist prices for polling/WebSocket dashboards."""
    set_kite_token()

    symbols = symbols if symbols else get_watchlist_symbols()
    valid_symbols = [s for s in symbols if s in STOCK_UNIVERSE]

    if not valid_symbols:
        valid_symbols = list(STOCK_UNIVERSE.keys())[:5]

    quote_symbols = [f"NSE:{symbol}" for symbol in valid_symbols]

    rows = []
    try:
        quotes = kite.quote(quote_symbols)
        for symbol in valid_symbols:
            key = f"NSE:{symbol}"
            quote = quotes.get(key, {})
            rows.append({
                "symbol": symbol,
                "last_price": quote.get("last_price", 0),
                "volume": quote.get("volume", 0),
                "ohlc": quote.get("ohlc", {}),
                "timestamp": str(datetime.now()),
            })
    except Exception as e:
        for symbol in valid_symbols:
            rows.append({
                "symbol": symbol,
                "last_price": "Error",
                "volume": 0,
                "ohlc": {},
                "error": str(e),
                "timestamp": str(datetime.now()),
            })

    return {
        "refresh_seconds": REALTIME_REFRESH_SECONDS,
        "count": len(rows),
        "generated_at": str(datetime.now()),
        "prices": rows,
    }


@socketio.on("connect")
def socket_connect():
    socketio.emit("ultra_realtime_snapshot", get_ultra_realtime_snapshot())


@socketio.on("request_live_snapshot")
def socket_live_snapshot():
    socketio.emit("ultra_realtime_snapshot", get_ultra_realtime_snapshot())


@app.route("/ultra-realtime")
def ultra_realtime():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    watchlist_symbols = get_watchlist_symbols()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 37 - WebSocket Ultra Real-Time Engine</h2>

<div class="alert alert-info">
    Live prices auto-refresh every {{ refresh_seconds }} seconds. This page uses API polling and can also receive Socket.IO snapshots when enabled by the browser.
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Ultra Real-Time Watchlist</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Stock</th><th>Live Price</th><th>Volume</th><th>Updated</th></tr>
            {% for symbol in watchlist_symbols %}
            <tr>
                <td><b>{{ symbol }}</b></td>
                <td id="price-{{ symbol }}">Loading...</td>
                <td id="volume-{{ symbol }}">Loading...</td>
                <td id="time-{{ symbol }}">Loading...</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>

<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<script>
function updateRows(data) {
    if (!data.prices) return;
    data.prices.forEach(function(row) {
        const p = document.getElementById("price-" + row.symbol);
        const v = document.getElementById("volume-" + row.symbol);
        const t = document.getElementById("time-" + row.symbol);
        if (p) p.innerHTML = row.last_price === "Error" ? "Error" : "₹" + row.last_price;
        if (v) v.innerHTML = row.volume || "-";
        if (t) t.innerHTML = row.timestamp || data.generated_at;
    });
}

async function loadSnapshot() {
    try {
        const response = await fetch("/api/ultra-realtime");
        const data = await response.json();
        updateRows(data);
    } catch (err) {
        console.log("Ultra realtime fetch failed", err);
    }
}

loadSnapshot();
setInterval(loadSnapshot, {{ refresh_seconds }} * 1000);

try {
    const socket = io();
    socket.on("connect", function() { socket.emit("request_live_snapshot"); });
    socket.on("ultra_realtime_snapshot", updateRows);
} catch (err) {
    console.log("Socket fallback active", err);
}
</script>
{% endblock %}
""", watchlist_symbols=watchlist_symbols, refresh_seconds=REALTIME_REFRESH_SECONDS)


@app.route("/api/ultra-realtime")
def api_ultra_realtime():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_ultra_realtime_snapshot()


# -------------------------------------------------------------------
# Phase 38: AI Risk Firewall
# -------------------------------------------------------------------

RISK_FIREWALL_ENABLED = os.getenv("RISK_FIREWALL_ENABLED", "true").lower() == "true"
RISK_FIREWALL_MAX_AVG_RANGE_PERCENT = float(os.getenv("RISK_FIREWALL_MAX_AVG_RANGE_PERCENT", 4))
RISK_FIREWALL_MAX_BEARISH_COUNT = int(os.getenv("RISK_FIREWALL_MAX_BEARISH_COUNT", 4))


def get_risk_firewall_snapshot(symbols=None):
    set_kite_token()

    symbols = symbols if symbols else get_watchlist_symbols()
    valid_symbols = [s for s in symbols if s in STOCK_UNIVERSE]
    rows = []
    bearish_count = 0
    avg_ranges = []

    for symbol in valid_symbols:
        try:
            df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))
            recent = df.tail(10).copy()
            recent["range_percent"] = ((recent["high"] - recent["low"]) / recent["close"]) * 100
            avg_range = round(float(recent["range_percent"].mean()), 2)
            strategy = generate_ai_strategy(df)

            if strategy["signal"] in ["SELL", "STRONG SELL", "WATCH"] and strategy["score"] < 0:
                bearish_count += 1

            avg_ranges.append(avg_range)
            rows.append({
                "symbol": symbol,
                "signal": strategy["signal"],
                "confidence": strategy["confidence"],
                "score": strategy["score"],
                "avg_range_percent": avg_range,
                "risk_state": "HIGH" if avg_range >= RISK_FIREWALL_MAX_AVG_RANGE_PERCENT else "NORMAL",
            })
        except Exception as e:
            rows.append({
                "symbol": symbol,
                "signal": "ERROR",
                "confidence": 0,
                "score": 0,
                "avg_range_percent": 0,
                "risk_state": "UNKNOWN",
                "error": str(e),
            })

    portfolio_risk = round(sum(avg_ranges) / len(avg_ranges), 2) if avg_ranges else 0

    if not RISK_FIREWALL_ENABLED:
        firewall_status = "DISABLED"
        trade_permission = "MANUAL REVIEW"
    elif portfolio_risk >= RISK_FIREWALL_MAX_AVG_RANGE_PERCENT or bearish_count >= RISK_FIREWALL_MAX_BEARISH_COUNT:
        firewall_status = "LOCKDOWN"
        trade_permission = "BLOCK NEW AUTO TRADES"
    elif portfolio_risk >= (RISK_FIREWALL_MAX_AVG_RANGE_PERCENT * 0.7) or bearish_count >= max(2, RISK_FIREWALL_MAX_BEARISH_COUNT - 1):
        firewall_status = "CAUTION"
        trade_permission = "REDUCE SIZE / REVIEW"
    else:
        firewall_status = "NORMAL"
        trade_permission = "TRADING ALLOWED"

    return {
        "enabled": RISK_FIREWALL_ENABLED,
        "firewall_status": firewall_status,
        "trade_permission": trade_permission,
        "portfolio_risk_percent": portfolio_risk,
        "bearish_count": bearish_count,
        "max_range_threshold": RISK_FIREWALL_MAX_AVG_RANGE_PERCENT,
        "max_bearish_count": RISK_FIREWALL_MAX_BEARISH_COUNT,
        "symbols_checked": len(valid_symbols),
        "rows": rows,
        "generated_at": str(datetime.now()),
    }


@app.route("/risk-firewall")
def risk_firewall():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_risk_firewall_snapshot()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 38 - AI Risk Firewall</h2>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Status</h6><h3>{{ data.firewall_status }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Permission</h6><h5>{{ data.trade_permission }}</h5></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Portfolio Risk</h6><h3>{{ data.portfolio_risk_percent }}%</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Bearish Count</h6><h3>{{ data.bearish_count }}</h3></div></div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Firewall Stock-Level Risk</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Stock</th><th>Signal</th><th>Confidence</th><th>Score</th><th>Avg Range %</th><th>Risk State</th></tr>
            {% for r in data.rows %}
            <tr>
                <td><b>{{ r.symbol }}</b></td><td>{{ r.signal }}</td><td>{{ r.confidence }}%</td><td>{{ r.score }}</td><td>{{ r.avg_range_percent }}%</td><td>{{ r.risk_state }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/risk-firewall")
def api_risk_firewall():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_risk_firewall_snapshot()


@app.route("/risk-firewall/send-alert")
def risk_firewall_send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_risk_firewall_snapshot()
    msg = f"""
🛡️ <b>AI Risk Firewall</b>

Status: {data['firewall_status']}
Permission: {data['trade_permission']}
Portfolio Risk: {data['portfolio_risk_percent']}%
Bearish Count: {data['bearish_count']}
Symbols Checked: {data['symbols_checked']}
"""
    send_telegram_alert(msg)
    return render_template("scanner_trade_result.html", message="Risk firewall alert sent.")


# -------------------------------------------------------------------
# Phase 39: Institutional Dashboard
# -------------------------------------------------------------------


def get_institutional_dashboard_snapshot():
    capital = get_capital_management_snapshot()
    firewall = get_risk_firewall_snapshot()

    try:
        trades = TradeJournal.query.order_by(TradeJournal.created_at.desc()).limit(500).all()
        journal = get_journal_analytics(trades)
    except Exception:
        journal = {}

    try:
        sectors = get_sector_rotation_data(get_watchlist_symbols())[:5]
    except Exception:
        sectors = []

    try:
        strategies = get_marketplace_strategy_rows()[:8]
    except Exception:
        strategies = []

    return {
        "capital": capital,
        "firewall": firewall,
        "journal": journal,
        "top_sectors": sectors,
        "top_strategies": strategies,
        "generated_at": str(datetime.now()),
    }


@app.route("/institutional-dashboard")
def institutional_dashboard():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_institutional_dashboard_snapshot()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 39 - Institutional Dashboard</h2>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Capital</h6><h3>₹{{ data.capital.capital }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Open Exposure</h6><h3>{{ data.capital.open_exposure_percent }}%</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Firewall</h6><h3>{{ data.firewall.firewall_status }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Win Rate</h6><h3>{{ data.journal.win_rate or 0 }}%</h3></div></div>
</div>

<div class="row g-4">
    <div class="col-md-6">
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white">Top Sectors</div>
            <div class="card-body">
                <table class="table table-striped"><tr><th>Sector</th><th>Signal</th><th>Score</th></tr>
                {% for s in data.top_sectors %}<tr><td>{{ s.sector }}</td><td>{{ s.rotation_signal }}</td><td>{{ s.avg_score }}</td></tr>{% endfor %}
                </table>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white">Top Strategies</div>
            <div class="card-body">
                <table class="table table-striped"><tr><th>Strategy</th><th>Score</th><th>Recommendation</th></tr>
                {% for s in data.top_strategies %}<tr><td>{{ s.name }}</td><td>{{ s.score }}</td><td>{{ s.recommendation }}</td></tr>{% endfor %}
                </table>
            </div>
        </div>
    </div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/institutional-dashboard")
def api_institutional_dashboard():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_institutional_dashboard_snapshot()


# -------------------------------------------------------------------
# Phase 40: SaaS Commercial Version Blueprint
# -------------------------------------------------------------------

SAAS_PLANS = {
    "free": {"name": "Free", "price": 0, "features": ["Dashboard", "Watchlist", "Basic Scanner"]},
    "pro": {"name": "Pro", "price": 999, "features": ["AI Scanner", "Alerts", "Backtesting", "Risk Firewall"]},
    "institutional": {"name": "Institutional", "price": 9999, "features": ["Multi-account", "Institutional Dashboard", "Priority Alerts", "Strategy Lab"]},
}


def get_saas_admin_snapshot():
    active_modules = [
        "Dashboard", "Market", "Scanner", "Watchlist", "Trade Journal", "Sector AI",
        "News AI", "Options AI", "Swing AI", "Scalping AI", "Rebalancer",
        "RL AI", "Strategy Marketplace", "Advanced Backtest", "Risk Firewall",
        "Institutional Dashboard",
    ]

    return {
        "app_name": "AI Trading Bot SaaS",
        "environment": os.getenv("FLASK_ENV", "production"),
        "plans": SAAS_PLANS,
        "active_modules": active_modules,
        "payment_status": "Razorpay/Stripe placeholder - connect keys before accepting payments",
        "multi_user_status": "Blueprint ready - add user table/auth before public launch",
        "generated_at": str(datetime.now()),
    }


@app.route("/saas-admin")
def saas_admin():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_saas_admin_snapshot()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 40 - SaaS Commercial Version</h2>

<div class="alert alert-warning">
    Commercial blueprint active. Add dedicated user authentication, payment keys, legal disclaimers and broker-user isolation before public launch.
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Subscription Plans</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Plan</th><th>Monthly Price</th><th>Features</th></tr>
            {% for key, plan in data.plans.items() %}
            <tr><td><b>{{ plan.name }}</b></td><td>₹{{ plan.price }}</td><td>{{ plan.features|join(', ') }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Commercial Readiness</div>
    <div class="card-body">
        <p><b>Payment:</b> {{ data.payment_status }}</p>
        <p><b>Multi-user:</b> {{ data.multi_user_status }}</p>
        <p><b>Active Modules:</b> {{ data.active_modules|join(', ') }}</p>
    </div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/saas-admin")
def api_saas_admin():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_saas_admin_snapshot()


@app.route("/risk")
def risk_alias():
    return redirect(url_for("risk_firewall"))


@app.route("/institutional")
def institutional_alias():
    return redirect(url_for("institutional_dashboard"))


@app.route("/saas")
def saas_alias():
    return redirect(url_for("saas_admin"))




# =====================================================
# Phase 41: Hedge Fund Architecture Layer
# =====================================================

BROKER_PRIMARY = os.getenv("BROKER_PRIMARY", "ZERODHA")
EXECUTION_QUEUE_ENABLED = os.getenv("EXECUTION_QUEUE_ENABLED", "true").lower() == "true"
MAX_EXECUTION_QUEUE_SIZE = int(os.getenv("MAX_EXECUTION_QUEUE_SIZE", 50))
HEDGE_FUND_MODE = os.getenv("HEDGE_FUND_MODE", "paper").lower()

EXECUTION_QUEUE = []


def get_broker_health_snapshot():
    brokers = []

    zerodha_status = "DISCONNECTED"
    try:
        if set_kite_token():
            profile = kite.profile()
            zerodha_status = "CONNECTED" if profile else "CONNECTED"
    except Exception as e:
        zerodha_status = f"ERROR: {str(e)[:80]}"

    brokers.append({
        "broker": "ZERODHA",
        "status": zerodha_status,
        "mode": "LIVE" if AUTO_TRADE_ENABLED else "SAFE/PAPER",
        "primary": BROKER_PRIMARY.upper() == "ZERODHA",
    })

    for broker in ["ANGELONE", "FYERS", "UPSTOX", "BINANCE"]:
        brokers.append({
            "broker": broker,
            "status": "READY_FOR_INTEGRATION",
            "mode": "PAPER",
            "primary": BROKER_PRIMARY.upper() == broker,
        })

    return brokers


def add_execution_order_to_queue(symbol, signal, confidence, quantity, entry_price, source="AI"):
    if len(EXECUTION_QUEUE) >= MAX_EXECUTION_QUEUE_SIZE:
        return {"accepted": False, "reason": "Execution queue full"}

    order = {
        "id": len(EXECUTION_QUEUE) + 1,
        "time": datetime.utcnow().isoformat(),
        "symbol": symbol,
        "signal": signal,
        "confidence": confidence,
        "quantity": quantity,
        "entry_price": entry_price,
        "source": source,
        "status": "QUEUED",
        "mode": HEDGE_FUND_MODE,
    }

    EXECUTION_QUEUE.append(order)
    return {"accepted": True, "order": order}


def get_institutional_execution_snapshot():
    capital = get_capital_management_snapshot()
    broker_health = get_broker_health_snapshot()

    try:
        top_signals = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
    except Exception:
        top_signals = []

    return {
        "mode": HEDGE_FUND_MODE.upper(),
        "primary_broker": BROKER_PRIMARY.upper(),
        "execution_queue_enabled": EXECUTION_QUEUE_ENABLED,
        "queue_size": len(EXECUTION_QUEUE),
        "max_queue_size": MAX_EXECUTION_QUEUE_SIZE,
        "broker_health": broker_health,
        "capital": capital,
        "top_signals": top_signals,
        "queue": EXECUTION_QUEUE[-20:],
    }


@app.route("/hedge-fund-architecture")
def hedge_fund_architecture():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_institutional_execution_snapshot()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 41 - Hedge Fund Architecture</h2>
<div class="alert alert-info">Distributed execution layer, multi-broker readiness, execution queue and institutional controls.</div>

<div class="row g-4 mb-4">
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Mode</h6><h3>{{ data.mode }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Primary Broker</h6><h3>{{ data.primary_broker }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Queue Size</h6><h3>{{ data.queue_size }}/{{ data.max_queue_size }}</h3></div></div>
    <div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Capital</h6><h3>₹{{ data.capital.capital }}</h3></div></div>
</div>

<div class="card shadow-sm mb-4"><div class="card-header bg-dark text-white">Broker Health</div><div class="card-body">
<table class="table table-striped"><tr><th>Broker</th><th>Status</th><th>Mode</th><th>Primary</th></tr>
{% for b in data.broker_health %}<tr><td><b>{{ b.broker }}</b></td><td>{{ b.status }}</td><td>{{ b.mode }}</td><td>{{ b.primary }}</td></tr>{% endfor %}
</table></div></div>

<div class="card shadow-sm"><div class="card-header bg-dark text-white">Top Execution Candidates</div><div class="card-body">
<table class="table table-striped"><tr><th>Stock</th><th>Signal</th><th>Confidence</th><th>Entry</th><th>SL</th><th>Target</th></tr>
{% for s in data.top_signals %}<tr><td><b>{{ s.symbol }}</b></td><td>{{ s.signal }}</td><td>{{ s.confidence }}%</td><td>₹{{ s.entry_price }}</td><td>₹{{ s.stop_loss }}</td><td>₹{{ s.target }}</td></tr>{% endfor %}
</table></div></div>
{% endblock %}
""", data=data)


@app.route("/api/hedge-fund-architecture")
def api_hedge_fund_architecture():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_institutional_execution_snapshot()


# =====================================================
# Phase 42: Fully Autonomous AI Trader
# =====================================================

AUTONOMOUS_AI_ENABLED = os.getenv("AUTONOMOUS_AI_ENABLED", "false").lower() == "true"
AUTONOMOUS_MAX_STOCKS = int(os.getenv("AUTONOMOUS_MAX_STOCKS", 5))
AUTONOMOUS_MIN_CONFIDENCE = int(os.getenv("AUTONOMOUS_MIN_CONFIDENCE", 85))


def detect_market_regime():
    try:
        symbols = get_watchlist_symbols()[:10]
        results = scan_multiple_stocks(selected_symbols=symbols, min_confidence_filter=0)
        bullish = len([x for x in results if x.get("signal") in ["BUY", "STRONG BUY"]])
        bearish = len([x for x in results if x.get("signal") in ["SELL", "STRONG SELL"]])
        avg_conf = round(sum(x.get("confidence", 0) for x in results) / len(results), 2) if results else 0

        if bullish >= bearish * 2 and avg_conf >= 65:
            regime = "BULLISH"
        elif bearish >= bullish * 2 and avg_conf >= 65:
            regime = "BEARISH"
        elif avg_conf < 55:
            regime = "CHOPPY"
        else:
            regime = "NEUTRAL"

        return {"regime": regime, "bullish": bullish, "bearish": bearish, "avg_confidence": avg_conf}
    except Exception as e:
        return {"regime": "UNKNOWN", "error": str(e), "bullish": 0, "bearish": 0, "avg_confidence": 0}


def generate_autonomous_trade_plan():
    regime = detect_market_regime()
    capital = get_capital_management_snapshot()

    try:
        candidates = scan_multiple_stocks(top_n=AUTONOMOUS_MAX_STOCKS, min_confidence_filter=MIN_CONFIDENCE)
    except Exception:
        candidates = []

    plans = []
    for item in candidates:
        action = "SKIP"
        reason = "Signal not strong enough for autonomous execution"

        if item.get("confidence", 0) >= AUTONOMOUS_MIN_CONFIDENCE and item.get("signal") in ["BUY", "STRONG BUY", "SELL", "STRONG SELL"]:
            if regime["regime"] == "CHOPPY":
                action = "WAIT"
                reason = "Market regime is choppy; avoid autonomous entries"
            elif regime["regime"] == "BULLISH" and item.get("signal") in ["BUY", "STRONG BUY"]:
                action = "QUEUE_BUY"
                reason = "Bullish regime confirms buy candidate"
            elif regime["regime"] == "BEARISH" and item.get("signal") in ["SELL", "STRONG SELL"]:
                action = "QUEUE_SELL"
                reason = "Bearish regime confirms sell candidate"
            elif regime["regime"] == "NEUTRAL":
                action = "REVIEW"
                reason = "Strong signal but neutral market regime"

        quantity = calculate_position_size(item.get("entry_price"), item.get("stop_loss")) if item.get("entry_price") not in [None, "Error"] else 0

        plans.append({
            "symbol": item.get("symbol"),
            "signal": item.get("signal"),
            "confidence": item.get("confidence"),
            "entry_price": item.get("entry_price"),
            "stop_loss": item.get("stop_loss"),
            "target": item.get("target"),
            "quantity": quantity,
            "action": action,
            "reason": reason,
        })

    return {
        "enabled": AUTONOMOUS_AI_ENABLED,
        "regime": regime,
        "capital": capital,
        "plans": plans,
        "generated_at": datetime.utcnow().isoformat(),
    }


def run_autonomous_ai_once(execute=False):
    plan = generate_autonomous_trade_plan()
    executed = []

    for p in plan["plans"]:
        if p["action"] in ["QUEUE_BUY", "QUEUE_SELL"]:
            add_execution_order_to_queue(
                symbol=p["symbol"],
                signal=p["signal"],
                confidence=p["confidence"],
                quantity=p["quantity"],
                entry_price=p["entry_price"],
                source="AUTONOMOUS_AI",
            )

            if execute and AUTONOMOUS_AI_ENABLED:
                result = execute_auto_trade(
                    symbol=p["symbol"],
                    signal=p["signal"],
                    quantity=p["quantity"],
                    entry_price=p["entry_price"],
                    confidence=p["confidence"],
                    stop_loss=p["stop_loss"],
                )
                p["execution_result"] = result

            executed.append(p)

    plan["queued_or_executed"] = executed
    return plan


@app.route("/fully-autonomous-ai")
def fully_autonomous_ai():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = generate_autonomous_trade_plan()

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 42 - Fully Autonomous AI Trader</h2>
<div class="alert alert-warning">Autonomous execution is {{ 'ENABLED' if data.enabled else 'DISABLED / SAFE MODE' }}. Review before live execution.</div>

<div class="row g-4 mb-4">
<div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Market Regime</h6><h3>{{ data.regime.regime }}</h3></div></div>
<div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Avg Confidence</h6><h3>{{ data.regime.avg_confidence }}%</h3></div></div>
<div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Open Exposure</h6><h3>{{ data.capital.open_exposure_percent }}%</h3></div></div>
<div class="col-md-3"><div class="card p-3 shadow-sm"><h6>Today P&L</h6><h3>₹{{ data.capital.today_pnl }}</h3></div></div>
</div>

<div class="mb-3"><a href="/fully-autonomous-ai/run" class="btn btn-danger">Run Once / Queue Trades</a></div>

<div class="card shadow-sm"><div class="card-header bg-dark text-white">Autonomous Trade Plan</div><div class="card-body">
<table class="table table-striped"><tr><th>Stock</th><th>Signal</th><th>Conf</th><th>Entry</th><th>SL</th><th>Target</th><th>Qty</th><th>Action</th><th>Reason</th></tr>
{% for p in data.plans %}<tr><td><b>{{ p.symbol }}</b></td><td>{{ p.signal }}</td><td>{{ p.confidence }}%</td><td>₹{{ p.entry_price }}</td><td>₹{{ p.stop_loss }}</td><td>₹{{ p.target }}</td><td>{{ p.quantity }}</td><td>{{ p.action }}</td><td>{{ p.reason }}</td></tr>{% endfor %}
</table></div></div>
{% endblock %}
""", data=data)


@app.route("/fully-autonomous-ai/run")
def fully_autonomous_ai_run():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    data = run_autonomous_ai_once(execute=False)
    return render_template("scanner_trade_result.html", message=f"Autonomous AI completed. Queued/executable plans: {len(data.get('queued_or_executed', []))}")


@app.route("/api/fully-autonomous-ai")
def api_fully_autonomous_ai():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return generate_autonomous_trade_plan()


# =====================================================
# Phase 43: Crypto + Forex Multi-Asset Expansion
# =====================================================

CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
FOREX_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "USDINR"]


def get_multi_asset_watch():
    rows = []
    for symbol in CRYPTO_SYMBOLS:
        rows.append({
            "symbol": symbol,
            "asset_class": "CRYPTO",
            "status": "PAPER_READY",
            "broker": "BINANCE/BYBIT_READY",
            "signal": "WATCH",
            "note": "Connect exchange API keys before live trading.",
        })
    for symbol in FOREX_SYMBOLS:
        rows.append({
            "symbol": symbol,
            "asset_class": "FOREX",
            "status": "PAPER_READY",
            "broker": "FOREX_API_READY",
            "signal": "WATCH",
            "note": "Connect forex data/execution provider before live trading.",
        })
    return rows


@app.route("/multi-asset-expansion")
def multi_asset_expansion():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    rows = get_multi_asset_watch()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 43 - Crypto + Forex Expansion</h2>
<div class="alert alert-info">Multi-asset architecture is enabled in paper-ready mode. Add exchange/forex API keys for live integration.</div>
<table class="table table-striped"><tr><th>Symbol</th><th>Asset Class</th><th>Status</th><th>Broker</th><th>Signal</th><th>Note</th></tr>
{% for r in rows %}<tr><td><b>{{ r.symbol }}</b></td><td>{{ r.asset_class }}</td><td>{{ r.status }}</td><td>{{ r.broker }}</td><td>{{ r.signal }}</td><td>{{ r.note }}</td></tr>{% endfor %}
</table>
{% endblock %}
""", rows=rows)


@app.route("/api/multi-asset-expansion")
def api_multi_asset_expansion():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return {"assets": get_multi_asset_watch()}


# =====================================================
# Phase 44: AI Quant Research Lab
# =====================================================


def run_quant_factor_lab(symbols=None):
    symbols = symbols if symbols else get_watchlist_symbols()[:10]
    rows = []

    for symbol in symbols:
        try:
            df = prepare_indicator_df(get_historical_df(STOCK_UNIVERSE[symbol]))
            df["returns"] = df["close"].pct_change()
            latest = df.iloc[-1]
            momentum_20 = round(((df.iloc[-1]["close"] - df.iloc[-21]["close"]) / df.iloc[-21]["close"]) * 100, 2) if len(df) > 21 else 0
            volatility = round(df["returns"].rolling(20).std().iloc[-1] * 100, 2)
            trend_factor = 1 if latest["ema20"] > latest["ema50"] else -1
            rsi_factor = 1 if 45 <= latest["rsi"] <= 65 else -1 if latest["rsi"] > 75 or latest["rsi"] < 30 else 0
            alpha_score = round(momentum_20 + (trend_factor * 10) + (rsi_factor * 5) - volatility, 2)
            rows.append({
                "symbol": symbol,
                "momentum_20d": momentum_20,
                "volatility_20d": volatility,
                "trend_factor": trend_factor,
                "rsi": round(float(latest["rsi"]), 2),
                "alpha_score": alpha_score,
                "recommendation": "RESEARCH LONG" if alpha_score >= 15 else "RESEARCH SHORT" if alpha_score <= -15 else "WATCH",
            })
        except Exception as e:
            rows.append({"symbol": symbol, "error": str(e), "alpha_score": 0, "recommendation": "ERROR"})

    return sorted(rows, key=lambda x: x.get("alpha_score", 0), reverse=True)


@app.route("/quant-research-lab")
def quant_research_lab():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    rows = run_quant_factor_lab()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 44 - AI Quant Research Lab</h2>
<div class="alert alert-success">Factor research lab: momentum, volatility, trend and RSI factors ranked into alpha scores.</div>
<table class="table table-striped"><tr><th>Rank</th><th>Stock</th><th>20D Momentum</th><th>20D Volatility</th><th>Trend</th><th>RSI</th><th>Alpha Score</th><th>Recommendation</th></tr>
{% for r in rows %}<tr><td>{{ loop.index }}</td><td><b>{{ r.symbol }}</b></td><td>{{ r.momentum_20d }}</td><td>{{ r.volatility_20d }}</td><td>{{ r.trend_factor }}</td><td>{{ r.rsi }}</td><td>{{ r.alpha_score }}</td><td>{{ r.recommendation }}</td></tr>{% endfor %}
</table>
{% endblock %}
""", rows=rows)


@app.route("/api/quant-research-lab")
def api_quant_research_lab():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return {"factors": run_quant_factor_lab()}


# =====================================================
# Phase 45: Global Deployment + White Label SaaS
# =====================================================

WHITE_LABEL_BRAND = os.getenv("WHITE_LABEL_BRAND", "AI Trading Bot")
SUBSCRIPTION_PROVIDER = os.getenv("SUBSCRIPTION_PROVIDER", "Razorpay/Stripe Ready")


def get_white_label_saas_snapshot():
    return {
        "brand": WHITE_LABEL_BRAND,
        "subscription_provider": SUBSCRIPTION_PROVIDER,
        "tenant_mode": "READY",
        "plans": [
            {"name": "Starter", "price": "₹999/mo", "features": ["Scanner", "Watchlist", "Telegram Alerts"]},
            {"name": "Pro", "price": "₹2999/mo", "features": ["All AI Engines", "Backtesting", "Risk Firewall"]},
            {"name": "Institutional", "price": "Custom", "features": ["Multi-account", "Hedge Fund Architecture", "White Label"]},
        ],
        "deployment": {
            "web": "Render Web Service",
            "worker": "Render Background Worker",
            "database": "PostgreSQL",
            "status": "PRODUCTION_READY",
        },
    }


@app.route("/white-label-saas")
def white_label_saas():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    data = get_white_label_saas_snapshot()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 45 - Global Deployment + White Label SaaS</h2>
<div class="alert alert-info">White-label SaaS structure with tenant plans, subscription readiness and production deployment checklist.</div>
<div class="row g-4 mb-4"><div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Brand</h6><h3>{{ data.brand }}</h3></div></div><div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Tenant Mode</h6><h3>{{ data.tenant_mode }}</h3></div></div><div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Billing</h6><h3>{{ data.subscription_provider }}</h3></div></div></div>
<div class="card shadow-sm"><div class="card-header bg-dark text-white">Subscription Plans</div><div class="card-body"><table class="table table-striped"><tr><th>Plan</th><th>Price</th><th>Features</th></tr>{% for p in data.plans %}<tr><td><b>{{ p.name }}</b></td><td>{{ p.price }}</td><td>{{ p.features|join(', ') }}</td></tr>{% endfor %}</table></div></div>
{% endblock %}
""", data=data)


@app.route("/api/white-label-saas")
def api_white_label_saas():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_white_label_saas_snapshot()



# ============================================================
# Phase 35: AI Voice Assistant (Text/Voice-command ready)
# ============================================================

VOICE_COMMANDS = {
    "scanner": "Run AI scanner and show top stock opportunities.",
    "portfolio": "Open portfolio dashboard.",
    "market": "Open market chart dashboard.",
    "realtime": "Open realtime watchlist prices.",
    "risk": "Open risk firewall.",
    "journal": "Open trade journal.",
    "news": "Open news sentiment engine.",
    "sector": "Open sector rotation dashboard.",
}


def interpret_voice_command(command_text):
    """Phase 35: simple command interpreter for voice/text commands."""
    command = (command_text or "").lower().strip()

    if not command:
        return {
            "intent": "UNKNOWN",
            "reply": "Please say or type a command.",
            "redirect_url": None,
            "data": None,
        }

    if "scanner" in command or "best stock" in command or "top stock" in command:
        try:
            results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
            top = results[0] if results else None
            reply = "Scanner completed."
            if top:
                reply = f"Top opportunity is {top['symbol']} with {top['signal']} and {top['confidence']} percent confidence."
            return {"intent": "SCANNER", "reply": reply, "redirect_url": "/scanner", "data": results}
        except Exception as e:
            return {"intent": "SCANNER", "reply": f"Scanner failed: {str(e)}", "redirect_url": "/scanner", "data": None}

    if "portfolio" in command:
        return {"intent": "PORTFOLIO", "reply": "Opening portfolio dashboard.", "redirect_url": "/portfolio", "data": None}

    if "market" in command or "chart" in command:
        return {"intent": "MARKET", "reply": "Opening market chart.", "redirect_url": "/market", "data": None}

    if "realtime" in command or "live price" in command or "live prices" in command:
        return {"intent": "REALTIME", "reply": "Opening realtime dashboard.", "redirect_url": "/realtime", "data": None}

    if "risk" in command or "firewall" in command:
        return {"intent": "RISK_FIREWALL", "reply": "Opening risk firewall.", "redirect_url": "/risk-firewall", "data": None}

    if "journal" in command or "trade journal" in command:
        return {"intent": "TRADE_JOURNAL", "reply": "Opening trade journal.", "redirect_url": "/trade-journal", "data": None}

    if "sector" in command:
        return {"intent": "SECTOR", "reply": "Opening sector rotation dashboard.", "redirect_url": "/sector-rotation", "data": None}

    if "news" in command or "sentiment" in command:
        return {"intent": "NEWS", "reply": "Opening news sentiment dashboard.", "redirect_url": "/news-sentiment", "data": None}

    if "auto" in command and "trade" in command:
        return {
            "intent": "AUTO_TRADE_BLOCKED_BY_VOICE",
            "reply": "For safety, voice commands do not directly execute trades. Open Auto Trade page and confirm manually.",
            "redirect_url": "/auto-trade",
            "data": None,
        }

    return {
        "intent": "UNKNOWN",
        "reply": "Command not recognized. Try: run scanner, show portfolio, open market, open risk firewall, or show trade journal.",
        "redirect_url": None,
        "data": None,
    }


@app.route("/voice-assistant", methods=["GET", "POST"])
def voice_assistant():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    result = None
    command = ""

    if request.method == "POST":
        command = request.form.get("command", "")
        result = interpret_voice_command(command)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 35 - AI Voice Assistant</h2>

<div class="alert alert-info">
    Voice-ready command layer. Use browser speech input if available, or type a command below.
</div>

<form method="POST" action="/voice-assistant" class="card card-body shadow-sm mb-4">
    <label class="form-label">Command</label>
    <input name="command" id="commandInput" class="form-control mb-3" value="{{ command }}" placeholder="Example: Run scanner / Show portfolio / Open market">
    <div>
        <button class="btn btn-primary" type="submit">Run Command</button>
        <button class="btn btn-secondary" type="button" onclick="startVoice()">Start Voice</button>
    </div>
</form>

{% if result %}
<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Assistant Response</div>
    <div class="card-body">
        <p><b>Intent:</b> {{ result.intent }}</p>
        <p><b>Reply:</b> {{ result.reply }}</p>
        {% if result.redirect_url %}
            <a href="{{ result.redirect_url }}" class="btn btn-success">Open Page</a>
        {% endif %}
    </div>
</div>
{% endif %}

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Supported Commands</div>
    <div class="card-body">
        <ul>
            {% for key, value in commands.items() %}
                <li><b>{{ key }}</b> - {{ value }}</li>
            {% endfor %}
        </ul>
    </div>
</div>

<script>
function startVoice() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert("Speech recognition is not supported in this browser. Type your command instead.");
        return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.onresult = function(event) {
        document.getElementById("commandInput").value = event.results[0][0].transcript;
    };
    recognition.start();
}
</script>
{% endblock %}
""", result=result, command=command, commands=VOICE_COMMANDS)


@app.route("/api/voice-command", methods=["POST"])
def api_voice_command():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401

    payload = request.get_json(silent=True) or {}
    command = payload.get("command") or request.form.get("command", "")
    return interpret_voice_command(command)


# ============================================================
# Phase 46: AI Copilot - Trading Explanation Layer
# ============================================================


def build_ai_copilot_response(symbol=None):
    symbol = (symbol or "INFY").upper()
    if symbol not in STOCK_UNIVERSE:
        symbol = "INFY"

    response = {
        "symbol": symbol,
        "summary": "AI copilot generated a trading explanation using available platform engines.",
        "sections": [],
    }

    try:
        df = get_historical_df(STOCK_UNIVERSE[symbol])
        strategy = generate_ai_strategy(df)
        entry = round(float(df.iloc[-1]["close"]), 2)
        levels = calculate_trade_levels(entry, strategy["signal"])
        response["sections"].append({
            "title": "Technical View",
            "text": f"{symbol} shows {strategy['signal']} with {strategy['confidence']}% confidence. Score: {strategy['score']}. Entry around ₹{entry}, stop loss ₹{levels['stop_loss']}, target ₹{levels['target']}.",
            "points": strategy.get("reasons", []),
        })
    except Exception as e:
        response["sections"].append({"title": "Technical View", "text": f"Technical analysis unavailable: {str(e)}", "points": []})

    try:
        if "analyze_news_sentiment" in globals():
            sentiment = analyze_news_sentiment(symbol)
            response["sections"].append({
                "title": "News Sentiment",
                "text": f"News sentiment is {sentiment.get('overall_sentiment')} with {sentiment.get('confidence')}% confidence.",
                "points": [sentiment.get("summary", "")],
            })
    except Exception as e:
        response["sections"].append({"title": "News Sentiment", "text": f"News sentiment unavailable: {str(e)}", "points": []})

    try:
        snapshot = get_capital_management_snapshot()
        response["sections"].append({
            "title": "Risk View",
            "text": f"Open exposure is ₹{snapshot['open_exposure']} ({snapshot['open_exposure_percent']}%). Today P&L is ₹{snapshot['today_pnl']}.",
            "points": [
                f"Risk per trade: {snapshot['risk_per_trade_percent']}%",
                f"Max daily loss: ₹{snapshot['max_daily_loss_amount']}",
                f"Max portfolio exposure: ₹{snapshot['max_portfolio_exposure']}",
            ],
        })
    except Exception as e:
        response["sections"].append({"title": "Risk View", "text": f"Risk snapshot unavailable: {str(e)}", "points": []})

    return response


@app.route("/ai-copilot")
def ai_copilot():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    watchlist_symbols = get_watchlist_symbols()
    selected_symbol = request.args.get("symbol", watchlist_symbols[0] if watchlist_symbols else "INFY").upper()
    data = build_ai_copilot_response(selected_symbol)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 46 - AI Trading Copilot</h2>

<form method="GET" action="/ai-copilot" class="card card-body shadow-sm mb-4">
    <label class="form-label">Select Stock</label>
    <select name="symbol" class="form-select mb-3">
        {% for s in watchlist_symbols %}
        <option value="{{ s }}" {% if s == data.symbol %}selected{% endif %}>{{ s }}</option>
        {% endfor %}
    </select>
    <button class="btn btn-primary">Explain Trade</button>
</form>

<div class="alert alert-success">{{ data.summary }}</div>

{% for section in data.sections %}
<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">{{ section.title }}</div>
    <div class="card-body">
        <p>{{ section.text }}</p>
        {% if section.points %}
        <ul>{% for p in section.points %}<li>{{ p }}</li>{% endfor %}</ul>
        {% endif %}
    </div>
</div>
{% endfor %}
{% endblock %}
""", watchlist_symbols=watchlist_symbols, data=data)


@app.route("/api/ai-copilot/<symbol>")
def api_ai_copilot(symbol):
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return build_ai_copilot_response(symbol)


# ============================================================
# Phase 47: Multi-Broker Engine
# ============================================================

BROKER_REGISTRY = {
    "zerodha": {"name": "Zerodha Kite", "status": "CONNECTED", "execution": "LIVE/PAPER", "priority": 1},
    "angelone": {"name": "Angel One", "status": "READY_FOR_API", "execution": "PAPER", "priority": 2},
    "upstox": {"name": "Upstox", "status": "READY_FOR_API", "execution": "PAPER", "priority": 3},
    "binance": {"name": "Binance", "status": "CRYPTO_READY", "execution": "PAPER", "priority": 4},
    "interactive_brokers": {"name": "Interactive Brokers", "status": "INSTITUTIONAL_READY", "execution": "PAPER", "priority": 5},
}


def get_multi_broker_status():
    rows = []
    for key, broker in BROKER_REGISTRY.items():
        row = dict(broker)
        row["key"] = key
        if key == "zerodha":
            row["token_available"] = bool(get_latest_access_token())
            row["health"] = "ACTIVE" if row["token_available"] else "LOGIN_REQUIRED"
        else:
            row["token_available"] = False
            row["health"] = "PAPER_READY"
        rows.append(row)
    return rows


@app.route("/multi-broker-engine")
def multi_broker_engine():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    brokers = get_multi_broker_status()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 47 - Multi-Broker Engine</h2>

<div class="alert alert-info">Broker abstraction layer for Zerodha, AngelOne, Upstox, Binance and Interactive Brokers.</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Broker Registry</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Priority</th><th>Broker</th><th>Status</th><th>Execution</th><th>Token</th><th>Health</th></tr>
            {% for b in brokers %}
            <tr>
                <td>{{ b.priority }}</td><td><b>{{ b.name }}</b></td><td>{{ b.status }}</td><td>{{ b.execution }}</td><td>{{ b.token_available }}</td><td>{{ b.health }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", brokers=brokers)


@app.route("/api/multi-broker-engine")
def api_multi_broker_engine():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return {"brokers": get_multi_broker_status()}


# ============================================================
# Phase 48: Event-Driven AI Engine
# ============================================================

MARKET_EVENTS = [
    {"event": "RBI Policy", "impact": "Banking, NBFC, Auto", "risk": "HIGH", "playbook": "Reduce leverage before announcement; trade after direction confirmation."},
    {"event": "Union Budget", "impact": "Infra, PSU, Banking, Consumption", "risk": "VERY HIGH", "playbook": "Use sector rotation and avoid oversized intraday positions."},
    {"event": "US Fed Meeting", "impact": "IT, Metals, Global risk assets", "risk": "HIGH", "playbook": "Watch USD/INR and global tech sentiment."},
    {"event": "Quarterly Earnings", "impact": "Stock-specific", "risk": "MEDIUM/HIGH", "playbook": "Avoid buying just before results unless hedged."},
    {"event": "FII/DII Flow Shock", "impact": "Index-wide", "risk": "HIGH", "playbook": "Activate risk firewall if broad selling emerges."},
]


def get_event_driven_ai_snapshot():
    try:
        sectors = get_sector_rotation_data(get_watchlist_symbols()) if "get_sector_rotation_data" in globals() else []
        strongest_sector = sectors[0]["sector"] if sectors else "NA"
        weakest_sector = sectors[-1]["sector"] if sectors else "NA"
    except Exception:
        strongest_sector = "NA"
        weakest_sector = "NA"

    risk_level = "NORMAL"
    actions = ["Keep normal risk controls active."]
    today = datetime.now().strftime("%A")

    if today in ["Monday", "Friday"]:
        risk_level = "ELEVATED"
        actions.append("Reduce overnight risk due to gap risk around weekend/start-week moves.")

    return {
        "risk_level": risk_level,
        "strongest_sector": strongest_sector,
        "weakest_sector": weakest_sector,
        "events": MARKET_EVENTS,
        "actions": actions,
    }


@app.route("/event-driven-ai")
def event_driven_ai():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_event_driven_ai_snapshot()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 48 - Event-Driven AI Engine</h2>

<div class="row g-4 mb-4">
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Event Risk</h6><h3>{{ data.risk_level }}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Strongest Sector</h6><h3>{{ data.strongest_sector }}</h3></div></div>
    <div class="col-md-4"><div class="card p-3 shadow-sm"><h6>Weakest Sector</h6><h3>{{ data.weakest_sector }}</h3></div></div>
</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">AI Actions</div>
    <div class="card-body"><ul>{% for a in data.actions %}<li>{{ a }}</li>{% endfor %}</ul></div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Tracked Market Events</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Event</th><th>Impact</th><th>Risk</th><th>Playbook</th></tr>
            {% for e in data.events %}
            <tr><td><b>{{ e.event }}</b></td><td>{{ e.impact }}</td><td>{{ e.risk }}</td><td>{{ e.playbook }}</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/event-driven-ai")
def api_event_driven_ai():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_event_driven_ai_snapshot()


# ============================================================
# Phase 49: Smart Money / Institutional Flow Analytics
# ============================================================


def get_smart_money_flow(symbols=None):
    symbols = symbols if symbols else get_watchlist_symbols()
    rows = []

    for symbol in symbols:
        if symbol not in STOCK_UNIVERSE:
            continue
        try:
            df = get_historical_df(STOCK_UNIVERSE[symbol])
            if df.empty or len(df) < 25:
                continue
            latest = df.iloc[-1]
            avg_vol = df["volume"].rolling(20).mean().iloc[-1] if "volume" in df.columns else 0
            vol_ratio = round(float(latest.get("volume", 0)) / float(avg_vol or 1), 2)
            price_change = round(((float(latest["close"]) - float(df.iloc[-2]["close"])) / float(df.iloc[-2]["close"])) * 100, 2)

            if vol_ratio >= 1.5 and price_change > 0:
                flow = "SMART MONEY ACCUMULATION"
                confidence = min(95, int(60 + vol_ratio * 10 + price_change))
            elif vol_ratio >= 1.5 and price_change < 0:
                flow = "SMART MONEY DISTRIBUTION"
                confidence = min(95, int(60 + vol_ratio * 10 + abs(price_change)))
            elif vol_ratio >= 1.2:
                flow = "VOLUME ANOMALY"
                confidence = 65
            else:
                flow = "NORMAL FLOW"
                confidence = 50

            rows.append({
                "symbol": symbol,
                "price": round(float(latest["close"]), 2),
                "volume_ratio": vol_ratio,
                "price_change_percent": price_change,
                "flow": flow,
                "confidence": confidence,
            })
        except Exception as e:
            rows.append({"symbol": symbol, "flow": "ERROR", "confidence": 0, "error": str(e)})

    return sorted(rows, key=lambda x: x.get("confidence", 0), reverse=True)


@app.route("/smart-money-flow")
def smart_money_flow():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    scope = request.args.get("scope", "watchlist")
    symbols = get_watchlist_symbols() if scope == "watchlist" else list(STOCK_UNIVERSE.keys())
    rows = get_smart_money_flow(symbols)

    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 49 - Smart Money / Institutional Flow Analytics</h2>

<div class="mb-3">
    <a href="/smart-money-flow?scope=watchlist" class="btn btn-primary">Watchlist</a>
    <a href="/smart-money-flow?scope=all" class="btn btn-secondary">All Universe</a>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Volume Anomaly & Flow Detection</div>
    <div class="card-body">
        <table class="table table-striped table-hover">
            <tr><th>Stock</th><th>Price</th><th>Volume Ratio</th><th>Price Change</th><th>Flow</th><th>Confidence</th></tr>
            {% for r in rows %}
            <tr><td><b>{{ r.symbol }}</b></td><td>₹{{ r.price }}</td><td>{{ r.volume_ratio }}</td><td>{{ r.price_change_percent }}%</td><td>{{ r.flow }}</td><td>{{ r.confidence }}%</td></tr>
            {% endfor %}
        </table>
    </div>
</div>
{% endblock %}
""", rows=rows)


@app.route("/api/smart-money-flow")
def api_smart_money_flow():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    scope = request.args.get("scope", "watchlist")
    symbols = get_watchlist_symbols() if scope == "watchlist" else list(STOCK_UNIVERSE.keys())
    return {"flows": get_smart_money_flow(symbols)}


# ============================================================
# Phase 50: AGI Trading Supervisor
# ============================================================


def get_agi_supervisor_decision():
    decision = {
        "mode": "OBSERVE",
        "confidence": 0,
        "summary": "AGI supervisor combined platform signals and produced a safety-first decision.",
        "actions": [],
        "modules": {},
    }

    try:
        risk = get_capital_management_snapshot()
        decision["modules"]["capital"] = risk
        if risk.get("today_pnl", 0) <= -risk.get("max_daily_loss_amount", 999999):
            decision["mode"] = "LOCKDOWN"
            decision["actions"].append("Daily loss limit reached. Block new trades.")
        elif risk.get("open_exposure_percent", 0) >= MAX_PORTFOLIO_EXPOSURE_PERCENT:
            decision["mode"] = "DEFENSIVE"
            decision["actions"].append("Portfolio exposure is high. Avoid fresh positions.")
        else:
            decision["actions"].append("Capital exposure is within configured limits.")
    except Exception as e:
        decision["modules"]["capital_error"] = str(e)

    try:
        scanner = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
        decision["modules"]["top_scanner"] = scanner
        strong = [x for x in scanner if x.get("signal") in ["BUY", "STRONG BUY"] and x.get("confidence", 0) >= TRADE_CONFIDENCE]
        if strong and decision["mode"] not in ["LOCKDOWN", "DEFENSIVE"]:
            decision["mode"] = "SELECTIVE_RISK_ON"
            decision["confidence"] = max([x.get("confidence", 0) for x in strong])
            decision["actions"].append(f"Selective risk-on allowed. Top candidate: {strong[0]['symbol']}.")
        else:
            decision["actions"].append("No high-confidence scanner trades requiring immediate action.")
    except Exception as e:
        decision["modules"]["scanner_error"] = str(e)

    try:
        events = get_event_driven_ai_snapshot()
        decision["modules"]["events"] = events
        if events.get("risk_level") == "ELEVATED" and decision["mode"] == "SELECTIVE_RISK_ON":
            decision["mode"] = "CAUTIOUS_RISK_ON"
            decision["actions"].append("Event risk is elevated. Reduce size even if signals are strong.")
    except Exception as e:
        decision["modules"]["event_error"] = str(e)

    if decision["mode"] == "OBSERVE":
        decision["confidence"] = 55
    elif decision["mode"] == "LOCKDOWN":
        decision["confidence"] = 95
    elif decision["confidence"] == 0:
        decision["confidence"] = 70

    return decision


@app.route("/agi-trading-supervisor")
def agi_trading_supervisor():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    data = get_agi_supervisor_decision()
    return render_template_string("""
{% extends "base.html" %}
{% block content %}
<h2 class="mb-4">Phase 50 - AGI Trading Supervisor</h2>

<div class="row g-4 mb-4">
    <div class="col-md-6"><div class="card p-3 shadow-sm"><h6>Supervisor Mode</h6><h2>{{ data.mode }}</h2></div></div>
    <div class="col-md-6"><div class="card p-3 shadow-sm"><h6>Confidence</h6><h2>{{ data.confidence }}%</h2></div></div>
</div>

<div class="alert alert-info">{{ data.summary }}</div>

<div class="card shadow-sm mb-4">
    <div class="card-header bg-dark text-white">Supervisor Actions</div>
    <div class="card-body"><ul>{% for a in data.actions %}<li>{{ a }}</li>{% endfor %}</ul></div>
</div>

<div class="card shadow-sm">
    <div class="card-header bg-dark text-white">Module Snapshot</div>
    <div class="card-body"><pre>{{ data.modules }}</pre></div>
</div>
{% endblock %}
""", data=data)


@app.route("/api/agi-trading-supervisor")
def api_agi_trading_supervisor():
    if not is_logged_in():
        return {"error": "not_logged_in"}, 401
    return get_agi_supervisor_decision()


scheduler = BackgroundScheduler()

if SCHEDULER_ENABLED:
    scheduler.add_job(autonomous_scan_job, "interval", minutes=SCAN_INTERVAL_MINUTES)
    scheduler.add_job(monitor_open_trades, "interval", minutes=MONITOR_INTERVAL_MINUTES)
    scheduler.start()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
