"""Project provenance and data-source notes."""
from pathlib import Path
import streamlit as st
from utils.theme import page_header

APP_DIR=Path(__file__).parent

def show_settings():
    page_header("Platform & Data", "Source files, data quality, and model provenance")
    st.info("The bundled parking and traffic CSVs are demonstration datasets. The application does not receive a live city feed.")
    st.subheader("Data sources")
    for filename in ["india_smart_parking_dataset_1000.csv","parking_traffic_data.csv","live_parking_status.csv","parking_locations.csv"]:
        path=APP_DIR/"data"/filename
        if path.exists(): st.write(f"**{filename}** · {path.stat().st_size:,} bytes")
    st.caption("The Overview and analytics pages use india_smart_parking_dataset_1000.csv. The CSV uploader on Reports accepts occupancy_rate, or occupied and capacity, and uses any supported time, location, traffic, and weather fields.")
    st.subheader("Prediction model")
    model=APP_DIR/"models"/"parking_model.pkl"
    if model.exists(): st.write("A model artifact exists. Legacy artifacts are retrained automatically when the Prediction Center is used.")
    else: st.write("The Random Forest, Decision Tree, and Linear Regression candidates are fitted and compared when a prediction is first requested.")
    st.caption("Reported MAE, RMSE, and R² come from a held-out split of available labeled records. They are not a guarantee of real-world accuracy.")
    st.subheader("Storage")
    st.write("Prediction requests are recorded in the local SQLite database under `database/smart_parking.db`.")
