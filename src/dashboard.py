import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import random
import os

st.set_page_config(page_title="EV Battery Telemetry & 16S BMS Balancer", layout="wide")
st.title("⚡ EV Battery Telemetry & 16S BMS Balancer")

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
    cur.execute("SELECT COUNT(*) FROM battery_telemetry")
    if cur.fetchone()[0] == 0:
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

# Initialize 16-cell state in Streamlit session memory
if "cells" not in st.session_state:
    st.session_state.cells = [round(3.25 + random.uniform(-0.02, 0.03), 3) for _ in range(16)]
    st.session_state.cells[4] = 3.330  # Intentional high-voltage outlier
    st.session_state.cells[11] = 3.210 # Intentional low-voltage outlier

# Sidebar Controls
with st.sidebar:
    st.header("Powertrain Simulator")
    if st.button("Generate Telemetry Batch"):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        seed_batch(conn, cur, count=10)
        conn.close()
        st.success("New CAN frames ingested!")
        st.rerun()

    st.divider()
    st.header("16S Cell Balancer Control")
    balance_threshold = st.slider("Bleed Threshold (mV)", min_value=10, max_value=50, value=25)
    
    if st.button("Execute Passive Balance Cycle"):
        min_v = min(st.session_state.cells)
        # Bleed cells higher than min_v + threshold
        updated_cells = []
        for v in st.session_state.cells:
            if (v - min_v) * 1000 > balance_threshold:
                updated_cells.append(round(v - 0.015, 3))  # Simulated shunt resistor discharge
            else:
                updated_cells.append(v)
        st.session_state.cells = updated_cells
        st.success("Passive shunt balancing pulse applied!")
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

    # 16S Cell Monitoring Section
    st.subheader("🔋 16S Series Cell Voltages & Passive Bleed Status")
    cells = st.session_state.cells
    delta_v_mv = round((max(cells) - min(cells)) * 1000, 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Max Cell Voltage", f"{max(cells):.3f} V")
    c2.metric("Min Cell Voltage", f"{min(cells):.3f} V")
    c3.metric("Cell Delta (ΔV)", f"{delta_v_mv} mV", delta=f"{'-' if delta_v_mv > 30 else 'OK'}")

    cell_df = pd.DataFrame({
        "Cell Index": [f"Cell {i+1}" for i in range(16)],
        "Voltage (V)": cells,
        "Balancing Active": ["BLEED ACTIVE" if (v - min(cells))*1000 > balance_threshold else "IDLE" for v in cells]
    })

    st.bar_chart(cell_df.set_index("Cell Index")["Voltage (V)"])
    st.dataframe(cell_df.T, width="stretch")

    st.divider()

    st.subheader("📈 Real-Time Powertrain Dynamics")
    chart_data = data.sort_values("id")
    st.line_chart(chart_data.set_index("timestamp")[["pack_voltage", "current_draw", "bms_temp"]])

    st.subheader("📋 Ingested Telemetry Logs")
    st.dataframe(data, width="stretch")
