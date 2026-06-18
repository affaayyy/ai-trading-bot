# Phase 36 Mobile App Platform

This package contains a Flutter mobile app and Flask API patch for your AI Trading Bot.

## Files

```text
mobile_app/
  pubspec.yaml
  lib/main.dart
  lib/screens/api_client.dart
  lib/screens/dashboard_screen.dart
  lib/screens/scanner_screen.dart
  lib/screens/portfolio_screen.dart
  lib/screens/alerts_screen.dart
  lib/screens/voice_screen.dart
backend_patch/
  phase36_flask_routes.py
```

## Backend Setup

1. Open `backend_patch/phase36_flask_routes.py`.
2. Copy all routes into your Flask `app.py` before the scheduler section.
3. Push to GitHub and wait for Render redeploy.
4. Test these endpoints:

```text
/api/mobile/dashboard
/api/mobile/scanner
/api/mobile/portfolio
/api/mobile/alerts
/api/mobile/voice-command
```

## Mobile App Setup

1. Install Flutter.
2. Open `mobile_app/lib/screens/api_client.dart`.
3. Replace:

```dart
https://YOUR_RENDER_URL.onrender.com
```

with your actual Render web service URL.

4. Run:

```bash
cd mobile_app
flutter pub get
flutter run
```

## Notes

This Phase 36 app is a mobile dashboard/PWA-ready MVP. It uses API polling rather than direct broker login from mobile for safety.
