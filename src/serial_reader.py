"""
Hardware Serial Ingestion Bridge:
Reads serial lines from USB (Arduino/ESP32) and persists directly into telemetry.db.
"""
import sqlite3
import time
import os

try:
    import serial
except ImportError:
    serial = None

DB_PATH = "data/telemetry.db"

def run_serial_bridge(port="COM3", baud=115200):
    if serial is None:
        print("[!] pyserial is not installed. Install via: pip install pyserial")
        return

    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print(f"Connecting to microcontroller on {port} @ {baud} baud...")
    try:
        ser = serial.Serial(port, baud, timeout=1.0)
        time.sleep(2.0) # Allow MCU reset settling time
        print("Connected! Ingesting live hardware telemetry...\n")

        while True:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) >= 4:
                v, i, t, soc = float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3])
                status = "NORMAL"
                if t >= 45.0:
                    status = "CRITICAL: THERMAL RUNAWAY RISK"
                elif i >= 40.0:
                    status = "WARNING: OVERCURRENT DISCHARGE"

                cur.execute("""
                    INSERT INTO battery_telemetry (pack_voltage, current_draw, bms_temp, soc_percent, soh_percent, cycle_count, status_flag)
                    VALUES (?, ?, ?, ?, 97.4, 145, ?)
                """, (v, i, t, soc, status))
                conn.commit()
                print(f"[RX HARDWARE] V: {v}V | I: {i}A | T: {t}°C | Status: {status}")

    except KeyboardInterrupt:
        print("\nStopping hardware ingestion.")
    except Exception as e:
        print(f"[ERROR] Serial connection failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_serial_bridge()
