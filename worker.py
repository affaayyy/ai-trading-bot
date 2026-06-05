from app import app, autonomous_scan_job
import time

print("AI Trading Scheduler Worker started")

while True:
    with app.app_context():
        autonomous_scan_job()

    time.sleep(15 * 60)