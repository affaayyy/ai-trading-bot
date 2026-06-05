from app import app, autonomous_scan_job
import time
from datetime import datetime

print("🚀 AI Trading Scheduler Worker started")

while True:
    try:
        with app.app_context():
            print(f"\n[{datetime.now()}] Running autonomous scan...")
            autonomous_scan_job()
            print("✅ Autonomous scan completed successfully")

    except Exception as e:
        print("❌ Worker Error:", str(e))

    time.sleep(15 * 60)