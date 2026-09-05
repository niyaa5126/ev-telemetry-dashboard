import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="EV Battery Telemetry & BMS Diagnostics", layout="wide")
st.title("⚡ EV Battery Telemetry & BMS Safety Monitor")

def load_data():
    conn = sqlite3.connect("data/telemetry.db")
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
    st.warning("No records found. Run `python src/logger.py` to produce telemetry.")
