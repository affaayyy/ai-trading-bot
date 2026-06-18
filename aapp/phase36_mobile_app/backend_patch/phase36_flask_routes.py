# Add these routes to your Flask app.py before scheduler section.
# They are designed to work with your current functions:
# get_capital_management_snapshot, get_watchlist_symbols, scan_multiple_stocks,
# set_kite_token, kite, calculate_portfolio_analytics, SignalLog, TradeJournal.

@app.route('/api/mobile/dashboard')
def api_mobile_dashboard():
    if not is_logged_in():
        return {'error': 'not_logged_in'}, 401

    snapshot = get_capital_management_snapshot()
    watchlist = get_watchlist_symbols()

    return {
        'capital': snapshot.get('capital', 0),
        'open_exposure': snapshot.get('open_exposure', 0),
        'today_pnl': snapshot.get('today_pnl', 0),
        'watchlist_count': len(watchlist),
        'risk_status': 'OK' if snapshot.get('open_exposure_percent', 0) < 80 else 'HIGH EXPOSURE',
    }


@app.route('/api/mobile/scanner')
def api_mobile_scanner():
    if not is_logged_in():
        return {'error': 'not_logged_in'}, 401

    results = scan_multiple_stocks(top_n=10, min_confidence_filter=0)
    return {'results': results}


@app.route('/api/mobile/portfolio')
def api_mobile_portfolio():
    if not is_logged_in():
        return {'error': 'not_logged_in'}, 401

    set_kite_token()
    try:
        holdings = kite.holdings()
        analytics = calculate_portfolio_analytics(holdings)
        return {
            'total_invested': analytics.get('total_invested', 0),
            'current_value': analytics.get('current_value', 0),
            'total_pnl': analytics.get('total_pnl', 0),
            'pnl_percent': analytics.get('pnl_percent', 0),
            'holdings': analytics.get('holdings_data', []),
        }
    except Exception as e:
        return {'error': str(e), 'holdings': []}, 500


@app.route('/api/mobile/alerts')
def api_mobile_alerts():
    if not is_logged_in():
        return {'error': 'not_logged_in'}, 401

    alerts = []

    try:
        signals = SignalLog.query.order_by(SignalLog.created_at.desc()).limit(10).all()
        for item in signals:
            alerts.append({
                'title': f'{item.symbol} - {item.signal}',
                'message': f'Confidence {item.confidence}% | Score {item.score} | Price ₹{item.price}',
                'time': str(item.created_at),
            })
    except Exception:
        pass

    try:
        trades = TradeJournal.query.order_by(TradeJournal.created_at.desc()).limit(10).all()
        for item in trades:
            alerts.append({
                'title': f'Trade {item.symbol} - {item.status}',
                'message': f'{item.signal} | Qty {item.quantity} | P&L ₹{item.pnl}',
                'time': str(item.created_at),
            })
    except Exception:
        pass

    return {'alerts': alerts[:20]}


@app.route('/api/mobile/voice-command', methods=['POST'])
def api_mobile_voice_command():
    if not is_logged_in():
        return {'error': 'not_logged_in'}, 401

    data = request.get_json(silent=True) or {}
    command = (data.get('command') or '').lower().strip()

    if not command:
        return {'response': 'Please provide a command.'}

    if 'scanner' in command or 'scan' in command:
        results = scan_multiple_stocks(top_n=5, min_confidence_filter=0)
        summary = ', '.join([f"{x.get('symbol')} {x.get('signal')} {x.get('confidence')}%" for x in results])
        return {'response': f'Top scanner results: {summary}'}

    if 'portfolio' in command:
        snapshot = get_capital_management_snapshot()
        return {'response': f"Capital ₹{snapshot.get('capital')}, Exposure ₹{snapshot.get('open_exposure')}, Today P&L ₹{snapshot.get('today_pnl')}"}

    if 'risk' in command:
        snapshot = get_capital_management_snapshot()
        return {'response': f"Risk check: exposure {snapshot.get('open_exposure_percent')}%, max portfolio exposure {snapshot.get('max_portfolio_exposure_percent')}%."}

    if 'watchlist' in command:
        return {'response': f"Watchlist stocks: {', '.join(get_watchlist_symbols())}"}

    return {'response': 'Command received. Supported commands: run scanner, show portfolio, show risk, show watchlist.'}
