import pandas as pd


def _body(row):
    return abs(float(row["close"]) - float(row["open"]))


def _range(row):
    return max(float(row["high"]) - float(row["low"]), 0.0001)


def _upper_shadow(row):
    return float(row["high"]) - max(float(row["open"]), float(row["close"]))


def _lower_shadow(row):
    return min(float(row["open"]), float(row["close"])) - float(row["low"])


def _is_bullish(row):
    return float(row["close"]) > float(row["open"])


def _is_bearish(row):
    return float(row["close"]) < float(row["open"])


def detect_candlestick_patterns(df: pd.DataFrame) -> dict:
    """Detect common candlestick patterns using recent candles."""
    if df is None or df.empty or len(df) < 3:
        return {
            "patterns": [],
            "overall_bias": "NEUTRAL",
            "pattern_score": 0,
            "confidence_boost": 0,
            "summary": "Not enough candles for pattern recognition",
        }

    candles = df.tail(3).copy().reset_index(drop=True)
    c1 = candles.iloc[-3]
    c2 = candles.iloc[-2]
    c3 = candles.iloc[-1]

    detected = []
    score = 0

    body = _body(c3)
    rng = _range(c3)
    upper = _upper_shadow(c3)
    lower = _lower_shadow(c3)

    if body <= rng * 0.12:
        detected.append({"name": "Doji", "bias": "NEUTRAL", "confidence": 60, "reason": "Small candle body indicates indecision"})

    if lower >= body * 2 and upper <= body * 0.8 and body <= rng * 0.45:
        detected.append({"name": "Hammer", "bias": "BULLISH", "confidence": 70, "reason": "Long lower wick shows buying pressure"})
        score += 1

    if upper >= body * 2 and lower <= body * 0.8 and body <= rng * 0.45:
        detected.append({"name": "Shooting Star", "bias": "BEARISH", "confidence": 70, "reason": "Long upper wick shows selling pressure"})
        score -= 1

    if _is_bearish(c2) and _is_bullish(c3) and float(c3["close"]) > float(c2["open"]) and float(c3["open"]) < float(c2["close"]):
        detected.append({"name": "Bullish Engulfing", "bias": "BULLISH", "confidence": 80, "reason": "Bullish candle engulfed previous bearish candle"})
        score += 2

    if _is_bullish(c2) and _is_bearish(c3) and float(c3["open"]) > float(c2["close"]) and float(c3["close"]) < float(c2["open"]):
        detected.append({"name": "Bearish Engulfing", "bias": "BEARISH", "confidence": 80, "reason": "Bearish candle engulfed previous bullish candle"})
        score -= 2

    if _is_bearish(c1) and _body(c2) <= _range(c2) * 0.35 and _is_bullish(c3) and float(c3["close"]) > ((float(c1["open"]) + float(c1["close"])) / 2):
        detected.append({"name": "Morning Star", "bias": "BULLISH", "confidence": 85, "reason": "Three-candle bullish reversal structure"})
        score += 2

    if _is_bullish(c1) and _body(c2) <= _range(c2) * 0.35 and _is_bearish(c3) and float(c3["close"]) < ((float(c1["open"]) + float(c1["close"])) / 2):
        detected.append({"name": "Evening Star", "bias": "BEARISH", "confidence": 85, "reason": "Three-candle bearish reversal structure"})
        score -= 2

    if score > 0:
        bias = "BULLISH"
    elif score < 0:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"

    confidence_boost = min(10, abs(score) * 4)

    if not detected:
        summary = "No strong candlestick pattern detected"
    else:
        summary = ", ".join([item["name"] for item in detected])

    return {
        "patterns": detected,
        "overall_bias": bias,
        "pattern_score": score,
        "confidence_boost": confidence_boost,
        "summary": summary,
    }
