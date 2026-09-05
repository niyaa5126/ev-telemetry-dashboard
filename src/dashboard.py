import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="EV Battery Telemetry", layout="wide")
st.title("⚡ Electric Vehicle Battery Telemetry Dashboard")

def load_data():
    conn = sqlite3.connect("data/telemetry.db")
    df = pd.read_sql_query("SELECT * FROM battery_telemetry ORDER BY id DESC LIMIT 30", conn)
    conn.close()
    return df

data = load_data()

if not data.empty:
    latest = data.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pack Voltage", f"{latest['pack_voltage']} V")
    col2.metric("Current Draw", f"{latest['current_draw']} A")
    col3.metric("BMS Temp", f"{latest['bms_temp']} °C")
    col4.metric("State of Charge", f"{latest['soc_percent']} %")
    
    st.subheader("📈 Telemetry Trends")
    st.line_chart(data.set_index("timestamp")[["pack_voltage", "current_draw", "bms_temp"]])
    
    st.subheader("📋 Recent Records")
    st.dataframe(data)
else:
    st.warning("No telemetry records found. Run `src/logger.py` to stream data.")
