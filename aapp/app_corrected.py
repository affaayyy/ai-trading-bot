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
    created_aAt = db.Column(db.DateTime, default=datetime.utcnow)


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

        if stocks:
            return [stock.symbol for stock in stocks]

    except Exception as e:
        print("Watchlist load error:", str(e), flush=True)

    return ["INFY", "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK"]


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
        raw_df = get_historical_df(STOCK_UNIVERSE[selected_symbol])

        if raw_df is None or raw_df.empty or len(raw_df) < 60:
            raise Exception("Historical data empty or insufficient")

    except Exception as e:
        print("Market historical data error:", str(e), flush=True)

        selected_symbol = "INFY"
        raw_df = get_historical_df(STOCK_UNIVERSE["INFY"])

        if raw_df is None or raw_df.empty:
            return render_template(
                "scanner_trade_result.html",
                message="Market data unavailable. Please check Zerodha access token and try again."
            )

    df = prepare_indicator_df(raw_df)
    df.dropna(inplace=True)

    if df.empty:
        return render_template(
            "scanner_trade_result.html",
            message="Market indicators could not be calculated because data is insufficient."
        )

    strategy = generate_ai_strategy(df)

    entry_price = round(float(df.iloc[-1]["close"]), 2)
    live_price = round(get_live_price(selected_symbol, entry_price), 2)

    levels = calculate_trade_levels(
        entry_price,
        strategy["signal"]
    )

    market_data = []

    try:
        valid_watchlist_symbols = [
            symbol for symbol in watchlist_symbols
            if symbol in STOCK_UNIVERSE
        ][:8]

        quote_symbols = [
            f"NSE:{symbol}"
            for symbol in valid_watchlist_symbols
        ]

        if quote_symbols:
            quotes = kite.quote(quote_symbols)

            for symbol in valid_watchlist_symbols:
                key = f"NSE:{symbol}"

                price = quotes.get(key, {}).get("last_price")

                if price is None:
                    continue

                market_data.append({
                    "symbol": symbol,
                    "price": price,
                    "signal": "HOLD" if price > 1000 else "WATCH"
                })

                db.session.add(
                    SignalLog(
                        symbol=symbol,
                        price=price,
                        signal=strategy["signal"],
                        confidence=strategy["confidence"],
                        score=strategy["score"]
                    )
                )

            db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Market quote error:", str(e), flush=True)

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Candlestick"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ema20"],
            mode="lines",
            name="EMA20"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["ema50"],
            mode="lines",
            name="EMA50"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[datetime.now()],
            y=[live_price],
            mode="markers+text",
            name="Live Price",
            text=[f"Live ₹{live_price}"],
            textposition="top center"
        )
    )

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

scheduler = BackgroundScheduler()

if SCHEDULER_ENABLED:
    scheduler.add_job(autonomous_scan_job, "interval", minutes=SCAN_INTERVAL_MINUTES)
    scheduler.add_job(monitor_open_trades, "interval", minutes=MONITOR_INTERVAL_MINUTES)
    scheduler.start()


if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
