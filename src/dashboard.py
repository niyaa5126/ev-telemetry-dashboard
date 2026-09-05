import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import random
import os

st.set_page_config(page_title="EV Battery Telemetry, BMS Balancer & SoH Monitor", layout="wide")
st.title("⚡ EV Battery Telemetry, BMS Balancer & SoH Monitor")

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
            soh_percent REAL DEFAULT 98.5,
            cycle_count INTEGER DEFAULT 142,
            status_flag TEXT
        )
    """)
    conn.commit()

    # Automatic schema migration for existing SQLite files
    cur.execute("PRAGMA table_info(battery_telemetry)")
    columns = [row[1] for row in cur.fetchall()]
    
    if "soh_percent" not in columns:
        cur.execute("ALTER TABLE battery_telemetry ADD COLUMN soh_percent REAL DEFAULT 98.5")
    if "cycle_count" not in columns:
        cur.execute("ALTER TABLE battery_telemetry ADD COLUMN cycle_count INTEGER DEFAULT 142")
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM battery_telemetry")
    if cur.fetchone()[0] == 0:
        seed_batch(conn, cur, count=25)
    conn.close()

def seed_batch(conn, cur, count=10):
    base_voltage = 52.0
    soc = 96.0
    base_cycles = 142

    for i in range(count):
        inject_thermal = (i in [6, 7])
        inject_overcurrent = (i in [14, 15])
        temp = round(random.uniform(48.5, 53.0), 1) if inject_thermal else round(random.uniform(28.0, 39.0), 1)
        current = round(random.uniform(45.0, 56.0), 2) if inject_overcurrent else round(random.uniform(5.0, 24.0), 2)
        voltage = round(base_voltage - (current * 0.04) + random.uniform(-0.15, 0.15), 2)
        soc = round(max(0.0, soc - (current * 0.008)), 2)

        cycles = base_cycles + i
        thermal_penalty = 1.8 if temp >= 45.0 else 1.0
        degradation = (cycles * 0.018 * thermal_penalty)
        soh = round(max(50.0, 100.0 - degradation), 2)

        status = "NORMAL"
        if temp >= 45.0:
            status = "CRITICAL: THERMAL RUNAWAY RISK"
        elif current >= 40.0:
            status = "WARNING: OVERCURRENT DISCHARGE"
        elif voltage < 44.0:
            status = "CRITICAL: UNDERVOLTAGE SAG"
        elif soh < 80.0:
            status = "WARNING: BATTERY EOL DEGRADATION (SOH < 80%)"

        cur.execute("""
            INSERT INTO battery_telemetry (pack_voltage, current_draw, bms_temp, soc_percent, soh_percent, cycle_count, status_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (voltage, current, temp, soc, soh, cycles, status))
    conn.commit()

init_db()

# Session State for 16-cell balancing
if "cells" not in st.session_state:
    st.session_state.cells = [round(3.25 + random.uniform(-0.02, 0.03), 3) for _ in range(16)]
    st.session_state.cells[4] = 3.330
    st.session_state.cells[11] = 3.210

# Sidebar
with st.sidebar:
    st.header("Powertrain Mode")
    mode = st.radio("Telemetry Stream Source", ["Cloud Software Emulation", "Hardware Serial (COM / USB)"])
    
    if mode == "Hardware Serial (COM / USB)":
        st.text_input("Port", value="COM3")
        st.selectbox("Baud Rate", [9600, 115200], index=1)
        st.caption("Listening for CSV/JSON stream from Arduino or ESP32...")
    else:
        if st.button("Generate Telemetry Batch"):
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            seed_batch(conn, cur, count=10)
            conn.close()
            st.success("Batch ingested!")
            st.rerun()

    st.divider()
    st.header("16S Cell Balancer Control")
    balance_threshold = st.slider("Bleed Threshold (mV)", 10, 50, 25)
    if st.button("Execute Passive Balance Cycle"):
        min_v = min(st.session_state.cells)
        st.session_state.cells = [
            round(v - 0.015, 3) if (v - min_v) * 1000 > balance_threshold else v
            for v in st.session_state.cells
        ]
        st.success("Passive shunt discharge cycle applied!")
        st.rerun()

def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM battery_telemetry ORDER BY id DESC LIMIT 40", conn)
    conn.close()
    return df

data = load_data()

if not data.empty:
    # Ensure columns exist safely in dataframe
    if "soh_percent" not in data.columns:
        data["soh_percent"] = 98.5
    if "cycle_count" not in data.columns:
        data["cycle_count"] = 142

    latest = data.iloc[0]
    status = latest.get("status_flag", "NORMAL")

    if "CRITICAL" in status:
        st.error(f"🚨 BMS FAULT DETECTED: {status}")
    elif "WARNING" in status:
        st.warning(f"⚠️ BMS SYSTEM WARNING: {status}")
    else:
        st.success("✅ Powertrain & BMS Status: ALL SYSTEMS NOMINAL")

    # Key Telemetry Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pack Voltage", f"{latest['pack_voltage']} V")
    c2.metric("Current Draw", f"{latest['current_draw']} A")
    c3.metric("BMS Temp", f"{latest['bms_temp']} °C")
    c4.metric("State of Charge (SoC)", f"{latest['soc_percent']} %")
    c5.metric("State of Health (SoH)", f"{latest['soh_percent']} %", delta=f"{round(latest['soh_percent'] - 100, 1)}%")

    st.divider()

    # Degradation Analysis Section
    st.subheader("🔬 Battery Life & State of Health (SoH) Analytics")
    col_soh1, col_soh2 = st.columns(2)
    with col_soh1:
        st.markdown(f"""
        - **Equivalent Full Cycles (EFC)**: `{latest['cycle_count']}` cycles
        - **Nominal Pack Capacity**: `50.0 Ah`
        - **Remaining Usable Capacity**: `{round(50.0 * (latest['soh_percent'] / 100.0), 2)} Ah`
        - **End-of-Life (EOL) Threshold**: `80.0% SoH` (Automotive Standard)
        """)
    with col_soh2:
        chart_soh = data.sort_values("id")
        st.line_chart(chart_soh.set_index("cycle_count")["soh_percent"])

    st.divider()

    # 16S Cell Balancer Section
    st.subheader("🔋 16S Series Cell Voltages & Shunt Balancing")
    cells = st.session_state.cells
    delta_v_mv = round((max(cells) - min(cells)) * 1000, 1)

    bc1, bc2, bc3 = st.columns(3)
    bc1.metric("Max Cell Voltage", f"{max(cells):.3f} V")
    bc2.metric("Min Cell Voltage", f"{min(cells):.3f} V")
    bc3.metric("Cell Delta (ΔV)", f"{delta_v_mv} mV", delta="EXCESSIVE" if delta_v_mv > 30 else "OK")

    cell_df = pd.DataFrame({
        "Cell Index": [f"Cell {i+1}" for i in range(16)],
        "Voltage (V)": cells,
        "Bleed Status": ["BLEED ACTIVE" if (v - min(cells))*1000 > balance_threshold else "IDLE" for v in cells]
    })
    st.bar_chart(cell_df.set_index("Cell Index")["Voltage (V)"])

    st.divider()

    # Powertrain Dynamics & Logs
    st.subheader("📈 Real-Time Powertrain Dynamics")
    chart_data = data.sort_values("id")
    st.line_chart(chart_data.set_index("timestamp")[["pack_voltage", "current_draw", "bms_temp"]])

    # CAN Sniffer
    st.subheader("🛰️ Embedded CAN Bus Frame Sniffer (ISO 11898-1)")
    sample_frames = [
        {"CAN ID": "0x401", "Payload (Hex)": "0C D5 0C D8 0C E0 0D 02", "Decoded Metrics": "Cells 1 - 4 Voltage"},
        {"CAN ID": "0x402", "Payload (Hex)": "0C D2 0C D9 0C DA 0C DC", "Decoded Metrics": "Cells 5 - 8 Voltage"},
        {"CAN ID": "0x403", "Payload (Hex)": "0C DB 0C DF 0C D0 0C D6", "Decoded Metrics": "Cells 9 - 12 Voltage"},
        {"CAN ID": "0x404", "Payload (Hex)": "0C D4 0C D7 0C D9 0C D8", "Decoded Metrics": "Cells 13 - 16 Voltage"},
        {"CAN ID": "0x301", "Payload (Hex)": "13 F1 00 E6 00 00 00 00", "Decoded Metrics": "Pack Voltage (51.05V), Current (23.0A)"},
        {"CAN ID": "0x302", "Payload (Hex)": "20 03 B1 00 00 00 00 00", "Decoded Metrics": "BMS Temp (32.0°C), SoC (94.5%)"}
    ]
    st.table(pd.DataFrame(sample_frames))

    st.subheader("📋 Ingested Telemetry Logs")
    st.dataframe(data, width="stretch")
else:
    st.warning("No telemetry records found.")
