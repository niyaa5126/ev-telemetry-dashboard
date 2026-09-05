import sqlite3
import random
import time
import os

os.makedirs("data", exist_ok=True)
conn = sqlite3.connect("data/telemetry.db")
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS battery_telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        pack_voltage REAL,
        current_draw REAL,
        bms_temp REAL,
        soc_percent REAL,
        status_flag TEXT
    )
""")
conn.commit()

print("⚡ Starting BMS Telemetry with Dynamic Fault Injection...")

base_voltage = 52.0
soc = 98.0

try:
    for i in range(25):
        # Introduce intermittent fault injection
        inject_thermal = (i in [8, 9, 10])
        inject_overcurrent = (i in [16, 17])

        if inject_thermal:
            temp = round(random.uniform(48.5, 55.0), 1)
        else:
            temp = round(random.uniform(28.0, 41.0), 1)

        if inject_overcurrent:
            current = round(random.uniform(45.0, 60.0), 2)
        else:
            current = round(random.uniform(5.0, 25.0), 2)

        voltage = round(base_voltage - (current * 0.04) + random.uniform(-0.15, 0.15), 2)
        soc = round(max(0.0, soc - (current * 0.008)), 2)

        # Classify BMS alert conditions
        status = "NORMAL"
        if temp >= 45.0:
            status = "CRITICAL: THERMAL RUNAWAY RISK"
        elif current >= 40.0:
            status = "WARNING: OVERCURRENT DISCHARGE"
        elif voltage < 44.0:
            status = "CRITICAL: UNDERVOLTAGE SAG"

        cursor.execute("""
            INSERT INTO battery_telemetry (pack_voltage, current_draw, bms_temp, soc_percent, status_flag)
            VALUES (?, ?, ?, ?, ?)
        """, (voltage, current, temp, soc, status))
        conn.commit()

        print(f"[{time.strftime('%X')}] V: {voltage}V | I: {current}A | Temp: {temp}°C | SoC: {soc}% | [{status}]")
        time.sleep(0.6)

    print("✔ Telemetry stream generated and saved to data/telemetry.db")
finally:
    conn.close()
