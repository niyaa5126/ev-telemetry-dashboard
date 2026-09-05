# EV Battery Telemetry System & Analytics Dashboard

An end-to-end telemetry pipeline simulating Battery Management System (BMS) data acquisition, local SQLite time-series persistence, and interactive real-time telemetry visualization.

## Overview
- **Pack Voltage**: Dynamic pack voltage tracking under active discharge loads.
- **Current Draw**: Dynamic amp draw simulation across driving cycles.
- **Thermal Monitoring**: Continuous BMS and cell temperature metrics.
- **State of Charge (SoC)**: Algorithmic battery depletion tracking.

## Architecture
- **Data Ingestion (`src/logger.py`)**: Simulates sensor bus inputs and serializes incoming packets into an indexed SQLite store.
- **Visualization Engine (`src/dashboard.py`)**: Multi-metric live dashboard built with Streamlit and Pandas.
- **Persistence (`data/telemetry.db`)**: Local ACID-compliant datastore for fast timeseries metric queries.

## Quickstart
```bash
git clone https://github.com/niyaa5126/ev-telemetry-dashboard.git
cd ev-telemetry-dashboard
pip install -r requirements.txt
python src/logger.py
python -m streamlit run src/dashboard.py
```
