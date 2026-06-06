# Phase 24 + 25 Package

This package upgrades your Phase 23 trading app with:

## Phase 24: Multi-Timeframe AI Confirmation
- 5-minute, 15-minute, 1-hour, and Daily confirmation
- Trend alignment score
- Bullish/Bearish/Mixed confirmation
- Confidence boost when timeframe direction aligns with the base signal

## Phase 25: Candlestick Pattern Recognition
- Doji
- Hammer
- Shooting Star
- Bullish Engulfing
- Bearish Engulfing
- Morning Star
- Evening Star

## Files to replace/add
- Replace `app.py`
- Add folder `ai_modules/`
- Replace `templates/market.html`
- Add `templates/ai_confirmation.html`

## Add to `.env`
```env
MTF_ENABLED=true
CANDLESTICK_ENABLED=true
MTF_INTRADAY_DAYS=7
```

## Add to navbar in `base.html`
```html
<a href="/ai-confirmation" class="btn btn-outline-light btn-sm">AI Confirmation</a>
```

## Test routes
```text
/market
/ai-confirmation
/api/ai-confirmation/INFY
```
