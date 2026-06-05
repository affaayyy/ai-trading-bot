from app import app, autonomous_scan_job
import time
from datetime import datetime

print("🚀 AI Trading Scheduler Worker started", flush=True)

while True:
    try:
        with app.app_context():
            print(f"[{datetime.now()}] Running autonomous scan...", flush=True)

            autonomous_scan_job()

            print("✅ Autonomous scan completed successfully", flush=True)

    except Exception as e:
        print(f"❌ Worker Error: {str(e)}", flush=True)

    time.sleep(15 * 60)