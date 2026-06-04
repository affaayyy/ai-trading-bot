from flask import Flask, request, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from kiteconnect import KiteConnect, KiteTicker
from dotenv import load_dotenv

import os
import threading
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.offline import plot
from datetime import datetime


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback_secret_key")

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
)

database_url = os.getenv("DATABASE_URL", "sqlite:///local.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

kite = KiteConnect(api_key=api_key)


AUTO_TRADE_ENABLED = os.getenv("AUTO_TRADE_ENABLED", "false").lower() == "true"
MAX_ORDER_QTY = int(os.getenv("MAX_ORDER_QTY", 1))
MAX_TRADES_PER_DAY = int(os.getenv("MAX_TRADES_PER_DAY", 3))
MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", 500))

STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 1))
TARGET_PERCENT = float(os.getenv("TARGET_PERCENT", 2))


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


with app.app_context():
    db.create_all()


def is_logged_in():
    return "access_token" in session


def set_kite_token():
    if is_logged_in():
        kite.set_access_token(session["access_token"])


def get_historical_df():
    instrument_token = 408065

    data = kite.historical_data(
        instrument_token,
        "2024-01-01",
        "2024-12-31",
        "day"
    )

    return pd.DataFrame(data)


def generate_ai_strategy(df):
    df["rsi"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    macd = ta.trend.MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    bollinger = ta.volatility.BollingerBands(close=df["close"])
    df["bb_high"] = bollinger.bollinger_hband()
    df["bb_low"] = bollinger.bollinger_lband()

    latest = df.iloc[-1]

    score = 0
    reasons = []

    if latest["rsi"] < 30:
        score += 2
        reasons.append("RSI indicates oversold market")
    elif latest["rsi"] > 70:
        score -= 2
        reasons.append("RSI indicates overbought market")

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

    if latest["close"] < latest["bb_low"]:
        score += 1
        reasons.append("Price below lower Bollinger Band")
    elif latest["close"] > latest["bb_high"]:
        score -= 1
        reasons.append("Price above upper Bollinger Band")

    if score >= 4:
        signal = "STRONG BUY"
    elif score >= 2:
        signal = "BUY"
    elif score <= -4:
        signal = "STRONG SELL"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    confidence = min(abs(score) * 20, 100)

    return {
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "rsi": round(latest["rsi"], 2),
        "ema20": round(latest["ema20"], 2),
        "ema50": round(latest["ema50"], 2),
        "macd": round(latest["macd"], 2),
        "macd_signal": round(latest["macd_signal"], 2),
        "reasons": reasons
    }


def risk_check(symbol, signal, quantity):
    today = datetime.utcnow().date()

    today_orders = OrderLog.query.filter(
        db.func.date(OrderLog.created_at) == today,
        OrderLog.status.in_(["SUCCESS", "AUTO_SUCCESS"])
    ).count()

    if today_orders >= MAX_TRADES_PER_DAY:
        return False, "Daily trade limit reached"

    if quantity > MAX_ORDER_QTY:
        return False, "Quantity exceeds max allowed limit"

    if signal not in ["BUY", "STRONG BUY", "SELL", "STRONG SELL"]:
        return False, "Signal is not actionable"

    return True, "Risk check passed"


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
        "target": round(target, 2) if target else None
    }


def execute_auto_trade(symbol, signal, quantity=1, entry_price=None):
    if not AUTO_TRADE_ENABLED:
        return "Auto trading disabled. Running in safe mode."

    if signal in ["BUY", "STRONG BUY"]:
        transaction_type = kite.TRANSACTION_TYPE_BUY
    elif signal in ["SELL", "STRONG SELL"]:
        transaction_type = kite.TRANSACTION_TYPE_SELL
    else:
        return "No trade placed. Signal is HOLD."

    allowed, reason = risk_check(symbol, signal, quantity)

    if not allowed:
        return f"Trade blocked: {reason}"

    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=kite.PRODUCT_CNC,
            order_type=kite.ORDER_TYPE_MARKET
        )

        db.session.add(OrderLog(
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            status="AUTO_SUCCESS",
            order_id=order_id
        ))

        db.session.commit()

        levels = calculate_trade_levels(entry_price, signal) if entry_price else {}

        return f"""
Auto trade placed successfully.
Order ID: {order_id}
Stop Loss: {levels.get('stop_loss')}
Target: {levels.get('target')}
"""

    except Exception as e:
        db.session.add(OrderLog(
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            status="AUTO_FAILED",
            order_id=None
        ))

        db.session.commit()

        return f"Auto trade failed: {str(e)}"


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

        equity_curve.append({
            "date": row["date"],
            "equity": round(current_equity, 2)
        })

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

                trades.append({
                    "date": row["date"],
                    "action": "BUY",
                    "price": round(price, 2),
                    "quantity": quantity,
                    "pnl": 0,
                    "reason": "AI BUY Signal"
                })

        elif sell_signal or stop_loss_hit or target_hit:
            capital += position * price
            pnl = (price - entry_price) * position

            reason = "AI SELL Signal"
            if stop_loss_hit:
                reason = "Stop Loss Hit"
            elif target_hit:
                reason = "Target Hit"

            trades.append({
                "date": row["date"],
                "action": "SELL",
                "price": round(price, 2),
                "quantity": position,
                "pnl": round(pnl, 2),
                "reason": reason
            })

            position = 0
            entry_price = 0

    final_value = capital + (position * df.iloc[-1]["close"])
    total_pnl = final_value - initial_capital
    roi = (total_pnl / initial_capital) * 100

    sell_trades = [t for t in trades if t["action"] == "SELL"]
    winning_trades = [t for t in sell_trades if t["pnl"] > 0]

    win_rate = 0
    if sell_trades:
        win_rate = (len(winning_trades) / len(sell_trades)) * 100

    return {
        "initial_capital": initial_capital,
        "final_value": round(final_value, 2),
        "total_pnl": round(total_pnl, 2),
        "roi": round(roi, 2),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2),
        "trades": trades,
        "equity_curve": equity_curve
    }


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
    session["access_token"] = data["access_token"]

    print("ACCESS TOKEN:", data["access_token"])

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

    market_data = []

    for symbol in symbols:
        price = quotes[symbol]["last_price"]
        market_signal = "HOLD" if price > 1000 else "WATCH"

        market_data.append({
            "symbol": symbol,
            "price": price,
            "signal": market_signal
        })

        db.session.add(SignalLog(
            symbol=symbol,
            price=price,
            signal=strategy["signal"],
            confidence=strategy["confidence"],
            score=strategy["score"]
        ))

    db.session.commit()

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

    fig.update_layout(
        title="INFY AI Trading Chart",
        height=550
    )

    chart = plot(fig, output_type="div")

    gpt_reasoning = "AI signal generated using RSI, EMA20, EMA50, MACD, and Bollinger Bands."

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
        gpt_reasoning=gpt_reasoning,
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

    return render_template(
        "portfolio.html",
        profile=profile,
        holdings=holdings,
        cash=cash
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
                order_type=kite.ORDER_TYPE_MARKET
            )

            message = f"Order placed successfully. Order ID: {order_id}"
            status = "SUCCESS"

        except Exception as e:
            order_id = None
            message = f"Order failed: {str(e)}"
            status = "FAILED"

        db.session.add(OrderLog(
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            status=status,
            order_id=order_id
        ))

        db.session.commit()

    return render_template("orders.html", message=message)


@app.route("/history")
def history():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    signals = SignalLog.query.order_by(SignalLog.created_at.desc()).limit(50).all()
    orders = OrderLog.query.order_by(OrderLog.created_at.desc()).limit(50).all()

    return render_template(
        "history.html",
        signals=signals,
        orders=orders
    )


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

    levels = calculate_trade_levels(
        latest_price,
        strategy["signal"]
    )

    result = execute_auto_trade(
        symbol="INFY",
        signal=strategy["signal"],
        quantity=1,
        entry_price=latest_price
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
        latest_price=round(latest_price, 2)
    )


@app.route("/backtest")
def backtest():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    set_kite_token()

    df = get_historical_df()
    result = run_backtest_v2(df)

    equity_fig = go.Figure()

    equity_fig.add_trace(go.Scatter(
        x=[e["date"] for e in result["equity_curve"]],
        y=[e["equity"] for e in result["equity_curve"]],
        mode="lines",
        name="Equity Curve"
    ))

    equity_fig.update_layout(
        title="Backtest Equity Curve",
        xaxis_title="Date",
        yaxis_title="Portfolio Value",
        height=450
    )

    equity_chart = plot(equity_fig, output_type="div")

    return render_template(
        "backtest.html",
        result=result,
        equity_chart=equity_chart
    )


live_prices = {}

TOKENS = {
    408065: "INFY",
    738561: "RELIANCE",
    2953217: "TCS",
    341249: "HDFCBANK"
}


@app.route("/realtime")
def realtime():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    return render_template("realtime.html")


def start_kite_stream():
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    kws = KiteTicker(api_key, access_token)

    def on_ticks(ws, ticks):
        for tick in ticks:
            token = tick["instrument_token"]
            price = tick["last_price"]
            symbol = TOKENS.get(token, str(token))

            live_prices[symbol] = price

            socketio.emit("price_update", {
                "symbol": symbol,
                "price": price
            })

    def on_connect(ws, response):
        tokens = list(TOKENS.keys())
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        print("Realtime WebSocket connected")

    def on_close(ws, code, reason):
        print("Realtime WebSocket closed:", code, reason)

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    kws.connect(threaded=True)


@app.route("/start-stream")
def start_stream():
    if not is_logged_in():
        return redirect(url_for("login_page"))

    thread = threading.Thread(target=start_kite_stream)
    thread.daemon = True
    thread.start()

    return redirect(url_for("realtime"))


if __name__ == "__main__":
    socketio.run(
        app,
        debug=True,
        allow_unsafe_werkzeug=True
    )