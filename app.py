from flask import Flask, request, render_template, session, redirect, url_for, has_request_context
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from kiteconnect import KiteConnect, KiteTicker
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

import os
import threading
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
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 15))


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


class TokenStore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


def get_latest_access_token():
    if has_request_context() and "access_token" in session:
        return session["access_token"]

    latest_token = TokenStore.query.order_by(TokenStore.created_at.desc()).first()
    return latest_token.access_token if latest_token else None


def is_logged_in():
    return get_latest_access_token() is not None


def set_kite_token():
    token = get_latest_access_token()
    if token:
        kite.set_access_token(token)
        return True
    return False


def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return "Telegram not configured"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        return str(e)


def get_historical_df(instrument_token=408065):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=365)

    data = kite.historical_data(
        instrument_token,
        start_date,
        end_date,
        "day",
    )

    return pd.DataFrame(data)


def generate_ai_strategy(df):
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    macd = ta.trend.MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

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


def risk_check(symbol, signal, quantity, confidence):
    today = datetime.utcnow().date()

    today_orders = OrderLog.query.filter(
        db.func.date(OrderLog.created_at) == today
    ).count()

    if today_orders >= MAX_TRADES_PER_DAY:
        return False, "Daily trade limit reached"

    if quantity > MAX_ORDER_QTY:
        return False, "Quantity exceeds limit"

    if signal not in ["BUY", "SELL", "STRONG BUY", "STRONG SELL"]:
        return False, "Signal not actionable"

    if confidence < TRADE_CONFIDENCE:
        return False, f"Confidence below trade threshold {TRADE_CONFIDENCE}%"

    return True, "Risk check passed"


def execute_auto_trade(symbol, signal, quantity=1, entry_price=None, confidence=0):
    if not AUTO_TRADE_ENABLED:
        return "SAFE MODE ENABLED\n\nAuto trading disabled."

    if signal in ["BUY", "STRONG BUY"]:
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif signal in ["SELL", "STRONG SELL"]:
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        return "No trade placed. Signal is not actionable."

    allowed, reason = risk_check(symbol, signal, quantity, confidence)

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

        db.session.add(
            OrderLog(
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                status="AUTO_SUCCESS",
                order_id=order_id,
            )
        )
        db.session.commit()

        levels = calculate_trade_levels(entry_price, signal)

        return f"""
AUTO TRADE EXECUTED

Stock: {symbol}
Signal: {signal}
Confidence: {confidence}%
Order ID: {order_id}
Stop Loss: {levels["stop_loss"]}
Target: {levels["target"]}
"""

    except Exception as e:
        db.session.add(
            OrderLog(
                symbol=symbol,
                transaction_type="AUTO",
                quantity=quantity,
                status="AUTO_FAILED",
                order_id=None,
            )
        )
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

        holdings_data.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "average_price": round(avg_price, 2),
                "last_price": round(last_price, 2),
                "invested": round(invested, 2),
                "current_value": round(value, 2),
                "pnl": round(pnl, 2),
            }
        )

    pnl_percent = (total_pnl / total_invested) * 100 if total_invested > 0 else 0

    return {
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_pnl": round(total_pnl, 2),
        "pnl_percent": round(pnl_percent, 2),
        "holdings_data": holdings_data,
    }


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

    symbols_to_scan = selected_symbols if selected_symbols else list(STOCK_UNIVERSE.keys())
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

            item = {
                "symbol": symbol,
                "price": current_price,
                "current_price": current_price,
                "entry_price": entry_price,
                "stop_loss": levels["stop_loss"],
                "target": levels["target"],
                "signal": strategy["signal"],
                "raw_signal": strategy["raw_signal"],
                "confidence": strategy["confidence"],
                "score": strategy["score"],
                "opportunity_score": opportunity_score,
                "rsi": strategy["rsi"],
                "ema20": strategy["ema20"],
                "ema50": strategy["ema50"],
                "reasons": ", ".join(strategy["reasons"]),
            }

            if item["confidence"] >= min_confidence_filter:
                scan_results.append(item)

        except Exception as e:
            scan_results.append(
                {
                    "symbol": symbol,
                    "price": "Error",
                    "current_price": "Error",
                    "entry_price": "Error",
                    "stop_loss": "-",
                    "target": "-",
                    "signal": "ERROR",
                    "raw_signal": "ERROR",
                    "confidence": 0,
                    "score": 0,
                    "opportunity_score": 0,
                    "rsi": "-",
                    "ema20": "-",
                    "ema50": "-",
                    "reasons": str(e),
                }
            )

    scan_results = sorted(scan_results, key=lambda x: x["opportunity_score"], reverse=True)

    if top_n:
        scan_results = scan_results[:top_n]

    return scan_results


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

                trades.append(
                    {
                        "date": row["date"],
                        "action": "BUY",
                        "price": round(price, 2),
                        "quantity": quantity,
                        "pnl": 0,
                        "reason": "AI BUY Signal",
                    }
                )

        elif sell_signal or stop_loss_hit or target_hit:
            capital += position * price
            pnl = (price - entry_price) * position

            reason = "AI SELL Signal"

            if stop_loss_hit:
                reason = "Stop Loss Hit"
            elif target_hit:
                reason = "Target Hit"

            trades.append(
                {
                    "date": row["date"],
                    "action": "SELL",
                    "price": round(price, 2),
                    "quantity": position,
                    "pnl": round(pnl, 2),
                    "reason": reason,
                }
            )

            position = 0
            entry_price = 0

    final_value = capital + (position * df.iloc[-1]["close"])
    total_pnl = final_value - initial_capital
    roi = (total_pnl / initial_capital) * 100

    sell_trades = [t for t in trades if t["action"] == "SELL"]
    winning_trades = [t for t in sell_trades if t["pnl"] > 0]
    win_rate = (len(winning_trades) / len(sell_trades)) * 100 if sell_trades else 0

    return {
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_pnl": round(total_pnl, 2),
        "roi": round(roi, 2),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2),
        "trades": trades,
        "equity_curve": equity_curve,
    }


def autonomous_scan_job():
    with app.app_context():
        try:
            if not set_kite_token():
                print("No valid Zerodha token found. Please login once today.", flush=True)
                return

            results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
            alert_count = send_scanner_alerts(results)

            for item in results:
                if item["confidence"] >= TRADE_CONFIDENCE:
                    execute_auto_trade(
                        symbol=item["symbol"],
                        signal=item["signal"],
                        quantity=1,
                        entry_price=item["entry_price"],
                        confidence=item["confidence"],
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

    symbols = ["NSE:INFY", "NSE:RELIANCE", "NSE:TCS", "NSE:HDFCBANK"]
    quotes = kite.quote(symbols)

    df = get_historical_df()
    strategy = generate_ai_strategy(df)

    live_quote = kite.quote(["NSE:INFY"])
    live_price = live_quote["NSE:INFY"]["last_price"]

    market_data = []

    for symbol in symbols:
        price = quotes[symbol]["last_price"]

        market_data.append(
            {
                "symbol": symbol,
                "price": price,
                "signal": "HOLD" if price > 1000 else "WATCH",
            }
        )

        db.session.add(
            SignalLog(
                symbol=symbol,
                price=price,
                signal=strategy["signal"],
                confidence=strategy["confidence"],
                score=strategy["score"],
            )
        )

    db.session.commit()

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Candlestick",
        )
    )

    fig.add_trace(go.Scatter(x=df["date"], y=df["ema20"], mode="lines", name="EMA20"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ema50"], mode="lines", name="EMA50"))

    fig.add_trace(
        go.Scatter(
            x=[datetime.now()],
            y=[live_price],
            mode="markers+text",
            name="Live Price",
            text=[f"Live ₹{live_price}"],
            textposition="top center",
        )
    )

    fig.update_layout(
        title=f"INFY AI Trading Chart - Live Price ₹{live_price}",
        height=550,
    )

    chart = plot(fig, output_type="div")

    return render_template(
        "market.html",
        latest_rsi=strategy["rsi"],
        latest_ema20=strategy["ema20"],
        latest_ema50=strategy["ema50"],
        macd=strategy["macd"],
        macd_signal=strategy["macd_signal"],
        ai_signal=strategy["signal"],
        confidence=strategy["confidence"],
        score=strategy["score"],
        reasons=strategy["reasons"],
        gpt_reasoning="AI signal generated using RSI, EMA20, EMA50, MACD, and Bollinger Bands.",
        market_data=market_data,
        chart=chart,
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
        allocation_fig.add_trace(
            go.Pie(
                labels=[h["symbol"] for h in analytics["holdings_data"]],
                values=[h["current_value"] for h in analytics["holdings_data"]],
                hole=0.4,
            )
        )
        allocation_fig.update_layout(title="Portfolio Allocation", height=400)
        allocation_chart = plot(allocation_fig, output_type="div")
    else:
        allocation_chart = "<p>No holdings available.</p>"

    return render_template(
        "portfolio.html",
        profile=profile,
        cash=cash,
        analytics=analytics,
        allocation_chart=allocation_chart,
    )


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
            order_id = kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                product=kite.PRODUCT_CNC,
                order_type=kite.ORDER_TYPE_MARKET,
            )

            message = f"Order placed successfully. Order ID: {order_id}"
            status = "SUCCESS"

        except Exception as e:
            order_id = None
            message = f"Order failed: {str(e)}"
            status = "FAILED"

        db.session.add(
            OrderLog(
                symbol=symbol,
                transaction_type=transaction_type,
                quantity=quantity,
                status=status,
                order_id=order_id,
            )
        )
        db.session.commit()

    return render_template("orders.html", message=message)


@app.route("/history")
def history():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    signals = SignalLog.query.order_by(SignalLog.created_at.desc()).limit(50).all()
    orders = OrderLog.query.order_by(OrderLog.created_at.desc()).limit(50).all()

    return render_template("history.html", signals=signals, orders=orders)


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

    df = get_historical_df()
    strategy = generate_ai_strategy(df)
    latest_price = df.iloc[-1]["close"]
    levels = calculate_trade_levels(latest_price, strategy["signal"])

    result = execute_auto_trade(
        symbol="INFY",
        signal=strategy["signal"],
        quantity=1,
        entry_price=latest_price,
        confidence=strategy["confidence"],
    )

    return render_template(
        "auto_trade.html",
        signal=strategy["signal"],
        confidence=strategy["confidence"],
        score=strategy["score"],
        result=result,
        auto_enabled=AUTO_TRADE_ENABLED,
        stop_loss=levels["stop_loss"],
        target=levels["target"],
        latest_price=round(latest_price, 2),
    )


@app.route("/backtest")
def backtest():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    set_kite_token()

    df = get_historical_df()
    result = run_backtest_v2(df)

    equity_fig = go.Figure()
    equity_fig.add_trace(
        go.Scatter(
            x=[e["date"] for e in result["equity_curve"]],
            y=[e["equity"] for e in result["equity_curve"]],
            mode="lines",
            name="Equity Curve",
        )
    )

    equity_fig.update_layout(
        title="Backtest Equity Curve",
        xaxis_title="Date",
        yaxis_title="Portfolio Value",
        height=450,
    )

    equity_chart = plot(equity_fig, output_type="div")

    return render_template(
        "backtest.html",
        result=result,
        equity_chart=equity_chart,
    )


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
        results = scan_multiple_stocks(
            selected_symbols=selected_symbols,
            min_confidence_filter=min_confidence_filter_value,
        )
    else:
        results = scan_multiple_stocks(
            top_n=5,
            min_confidence_filter=min_confidence_filter_value,
        )

    return render_template(
        "scanner.html",
        results=results,
        stock_universe=STOCK_UNIVERSE,
        selected_symbols=selected_symbols,
        min_confidence=min_confidence_filter,
    )


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
        results = scan_multiple_stocks(
            selected_symbols=selected_symbols,
            min_confidence_filter=min_confidence_filter_value,
        )
    else:
        results = scan_multiple_stocks(
            top_n=5,
            min_confidence_filter=min_confidence_filter_value,
        )

    alert_count = send_scanner_alerts(results)

    return render_template(
        "scanner_trade_result.html",
        message=f"High-confidence alerts sent successfully. Total alerts: {alert_count}",
    )


@app.route("/scanner/paper-trade/<symbol>/<action>")
def scanner_paper_trade(symbol, action):
    if not is_logged_in():
        return redirect(url_for("login_page"))

    message = f"""
PAPER TRADE EXECUTED

Stock: {symbol}
Action: {action}
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

    result = execute_auto_trade(
        symbol=symbol,
        signal=strategy["signal"],
        quantity=1,
        entry_price=entry_price,
        confidence=strategy["confidence"],
    )

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


@app.route("/send-alert")
def send_alert():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    results = scan_multiple_stocks(top_n=5, min_confidence_filter=MIN_CONFIDENCE)
    alert_count = send_scanner_alerts(results)

    return f"High-confidence Telegram Alerts Sent: {alert_count}"


@app.route("/run-scheduler-now")
def run_scheduler_now():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    autonomous_scan_job()

    return render_template(
        "scanner_trade_result.html",
        message="Autonomous high-confidence scheduler job executed manually.",
    )


live_prices = {}

TOKENS = {
    408065: "INFY",
    738561: "RELIANCE",
    2953217: "TCS",
    341249: "HDFCBANK",
}


@app.route("/realtime")
def realtime():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    return render_template("realtime.html")


def start_kite_stream():
    access_token = get_latest_access_token()

    if not access_token:
        print("No access token found for live stream", flush=True)
        return

    kws = KiteTicker(api_key, access_token)

    def on_ticks(ws, ticks):
        for tick in ticks:
            token = tick["instrument_token"]
            price = tick["last_price"]
            symbol = TOKENS.get(token, str(token))

            live_prices[symbol] = price

            socketio.emit(
                "price_update",
                {
                    "symbol": symbol,
                    "price": price,
                },
            )

            print(f"{symbol}: {price}", flush=True)

    def on_connect(ws, response):
        tokens = list(TOKENS.keys())
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        print("Live stream connected", flush=True)

    def on_close(ws, code, reason):
        print("Live stream closed:", code, reason, flush=True)

    def on_error(ws, code, reason):
        print("Live stream error:", code, reason, flush=True)

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close
    kws.on_error = on_error

    kws.connect(threaded=True)


@app.route("/start-stream")
def start_stream():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    thread = threading.Thread(target=start_kite_stream)
    thread.daemon = True
    thread.start()

    return redirect(url_for("realtime"))


scheduler = BackgroundScheduler()

if SCHEDULER_ENABLED:
    scheduler.add_job(
        autonomous_scan_job,
        "interval",
        minutes=SCAN_INTERVAL_MINUTES,
    )

    scheduler.start()


if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        allow_unsafe_werkzeug=True,
    )