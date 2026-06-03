from flask import Flask, request, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from kiteconnect import KiteConnect
from dotenv import load_dotenv

import os
import pandas as pd
import ta
import plotly.graph_objects as go
from plotly.offline import plot
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///local.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")

kite = KiteConnect(api_key=api_key)


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

    instrument_token = 408065

    data = kite.historical_data(
        instrument_token,
        "2024-01-01",
        "2024-12-31",
        "day"
    )

    df = pd.DataFrame(data)
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

        signal_log = SignalLog(
            symbol=symbol,
            price=price,
            signal=strategy["signal"],
            confidence=strategy["confidence"],
            score=strategy["score"]
        )

        db.session.add(signal_log)

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

    gpt_reasoning = """
    AI signal generated using RSI, EMA20, EMA50, MACD, and Bollinger Bands.
    """

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

        order_log = OrderLog(
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            status=status,
            order_id=order_id
        )

        db.session.add(order_log)
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


if __name__ == "__main__":
    app.run(debug=True)
