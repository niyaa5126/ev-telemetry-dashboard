import streamlit as st
import sqlite3
import pandas as pd
import random
import os

st.set_page_config(page_title="EV Battery Telemetry & BMS Diagnostics", layout="wide")
st.title("⚡ EV Battery Telemetry & BMS Safety Monitor")

DB_PATH = "data/telemetry.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
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
    
    # Check if empty, seed default simulation records
    cur.execute("SELECT COUNT(*) FROM battery_telemetry")
    count = cur.fetchone()[0]
    if count == 0:
        seed_batch(conn, cur, count=25)
    conn.close()

def seed_batch(conn, cur, count=10):
    base_voltage = 52.0
    soc = 98.0
    for i in range(count):
        inject_thermal = (i in [6, 7])
        inject_overcurrent = (i in [14, 15])
        temp = round(random.uniform(48.5, 54.0), 1) if inject_thermal else round(random.uniform(28.0, 41.0), 1)
        current = round(random.uniform(45.0, 58.0), 2) if inject_overcurrent else round(random.uniform(5.0, 24.0), 2)
        voltage = round(base_voltage - (current * 0.04) + random.uniform(-0.15, 0.15), 2)
        soc = round(max(0.0, soc - (current * 0.008)), 2)

        status = "NORMAL"
        if temp >= 45.0:
            status = "CRITICAL: THERMAL RUNAWAY RISK"
        elif current >= 40.0:
            status = "WARNING: OVERCURRENT DISCHARGE"
        elif voltage < 44.0:
            status = "CRITICAL: UNDERVOLTAGE SAG"

        cur.execute("""
            INSERT INTO battery_telemetry (pack_voltage, current_draw, bms_temp, soc_percent, status_flag)
            VALUES (?, ?, ?, ?, ?)
        """, (voltage, current, temp, soc, status))
    conn.commit()

init_db()

# Sidebar Control for Live Demos
with st.sidebar:
    st.header("Powertrain Simulator")
    if st.button("Generate New Telemetry Batch"):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        seed_batch(conn, cur, count=10)
        conn.close()
        st.success("New CAN telemetry frames ingested!")
        st.rerun()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM battery_telemetry ORDER BY id DESC LIMIT 40", conn)
    conn.close()
    return df

data = load_data()

if not data.empty:
    latest = data.iloc[0]
    status = latest.get("status_flag", "NORMAL")

    if "CRITICAL" in status:
        st.error(f"🚨 BMS FAULT DETECTED: {status}")
    elif "WARNING" in status:
        st.warning(f"⚠️ BMS SYSTEM WARNING: {status}")
    else:
        st.success("✅ Powertrain & BMS Status: ALL SYSTEMS NOMINAL")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pack Voltage", f"{latest['pack_voltage']} V")
    col2.metric("Current Draw", f"{latest['current_draw']} A")
    col3.metric("BMS Temp", f"{latest['bms_temp']} °C")
    col4.metric("State of Charge", f"{latest['soc_percent']} %")

    st.divider()

    st.subheader("📈 Real-Time Powertrain Dynamics")
    chart_data = data.sort_values("id")
    st.line_chart(chart_data.set_index("timestamp")[["pack_voltage", "current_draw", "bms_temp"]])

    st.subheader("📋 Ingested Telemetry Logs")
    st.dataframe(data, width="stretch")
else:
    st.warning("No records found.")
