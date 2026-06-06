import pandas as pd
import ta


def _safe_round(value, digits=2):
    try:
        if pd.isna(value):
            return None
        return round(float(value), digits)
    except Exception:
        return None


def analyze_timeframe(df: pd.DataFrame, label: str) -> dict:
    """Analyze one OHLC dataframe and return trend confirmation details."""
    if df is None or df.empty or len(df) < 55:
        return {
            "timeframe": label,
            "signal": "NO_DATA",
            "score": 0,
            "confidence": 0,
            "rsi": None,
            "ema20": None,
            "ema50": None,
            "macd": None,
            "macd_signal": None,
            "reason": "Not enough candles for reliable analysis",
        }

    work = df.copy()
    work["rsi"] = ta.momentum.RSIIndicator(close=work["close"], window=14).rsi()
    work["ema20"] = work["close"].ewm(span=20).mean()
    work["ema50"] = work["close"].ewm(span=50).mean()

    macd = ta.trend.MACD(close=work["close"])
    work["macd"] = macd.macd()
    work["macd_signal"] = macd.macd_signal()

    latest = work.iloc[-1]
    score = 0
    reasons = []

    if latest["ema20"] > latest["ema50"]:
        score += 1
        reasons.append("EMA trend bullish")
    else:
        score -= 1
        reasons.append("EMA trend bearish")

    if latest["macd"] > latest["macd_signal"]:
        score += 1
        reasons.append("MACD bullish")
    else:
        score -= 1
        reasons.append("MACD bearish")

    if latest["rsi"] < 35:
        score += 1
        reasons.append("RSI near oversold")
    elif latest["rsi"] > 65:
        score -= 1
        reasons.append("RSI near overbought")
    else:
        reasons.append("RSI neutral")

    if score >= 2:
        signal = "BULLISH"
    elif score <= -2:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    confidence = min(100, max(35, 50 + abs(score) * 15))

    return {
        "timeframe": label,
        "signal": signal,
        "score": score,
        "confidence": confidence,
        "rsi": _safe_round(latest["rsi"]),
        "ema20": _safe_round(latest["ema20"]),
        "ema50": _safe_round(latest["ema50"]),
        "macd": _safe_round(latest["macd"]),
        "macd_signal": _safe_round(latest["macd_signal"]),
        "reason": ", ".join(reasons),
    }


def summarize_multi_timeframe(results: list) -> dict:
    valid = [item for item in results if item.get("signal") != "NO_DATA"]

    bullish = len([item for item in valid if item.get("signal") == "BULLISH"])
    bearish = len([item for item in valid if item.get("signal") == "BEARISH"])
    neutral = len([item for item in valid if item.get("signal") == "NEUTRAL"])
    total = len(valid)

    if total == 0:
        return {
            "overall_signal": "NO_DATA",
            "alignment_score": 0,
            "alignment_percent": 0,
            "confidence_boost": 0,
            "summary": "No timeframe data available",
        }

    alignment_score = bullish - bearish
    alignment_percent = round((max(bullish, bearish, neutral) / total) * 100, 2)

    if bullish >= max(2, bearish + 1):
        overall_signal = "BULLISH"
        confidence_boost = min(15, bullish * 5)
    elif bearish >= max(2, bullish + 1):
        overall_signal = "BEARISH"
        confidence_boost = min(15, bearish * 5)
    else:
        overall_signal = "MIXED"
        confidence_boost = 0

    return {
        "overall_signal": overall_signal,
        "alignment_score": alignment_score,
        "alignment_percent": alignment_percent,
        "confidence_boost": confidence_boost,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "summary": f"{bullish} bullish, {bearish} bearish, {neutral} neutral across {total} timeframes",
    }
