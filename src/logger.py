import sqlite3
import time
import random
from datetime import datetime

def init_db():
    conn = sqlite3.connect("data/telemetry.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS battery_telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            pack_voltage REAL NOT NULL,
            current_draw REAL NOT NULL,
            bms_temp REAL NOT NULL,
            soc_percent REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_telemetry(samples=15):
    conn = sqlite3.connect("data/telemetry.db")
    cursor = conn.cursor()
    
    soc = 98.5
    voltage = 52.4
    
    print("⚡ Starting EV BMS Telemetry Stream...")
    for _ in range(samples):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current = round(random.uniform(5.0, 35.0), 2)
        voltage = round(max(44.0, voltage - (current * 0.01)), 2)
        temp = round(random.uniform(28.0, 42.5), 1)
        soc = round(max(0.0, soc - 0.2), 1)
        
        cursor.execute("""
            INSERT INTO battery_telemetry (timestamp, pack_voltage, current_draw, bms_temp, soc_percent)
            VALUES (?, ?, ?, ?, ?)
        """, (timestamp, voltage, current, temp, soc))
        conn.commit()
        
        print(f"[{timestamp}] V: {voltage}V | I: {current}A | Temp: {temp}°C | SoC: {soc}%")
        time.sleep(1)
        
    conn.close()
    print("✅ Telemetry batch successfully logged to data/telemetry.db")

if __name__ == "__main__":
    init_db()
    log_telemetry()
