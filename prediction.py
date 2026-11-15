"""Prediction Center backed by the supplied parking records."""
from datetime import date, time, datetime, timedelta
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from database import save_prediction
from train_model import train_models
from dashboard import load_parking, THEME

MODEL_PATH=Path(__file__).parent/"models"/"parking_model.pkl"

def get_parking_model():
    if not MODEL_PATH.exists(): train_models()
    saved=joblib.load(MODEL_PATH)
    # Replace legacy demo artifacts whose input schema does not match this pipeline.
    if not isinstance(saved,dict) or "model" not in saved or "features" not in saved:
        train_models()
        saved=joblib.load(MODEL_PATH)
    return saved if isinstance(saved,dict) else {"model":saved,"features":[]}

def show_parking_prediction():
    st.markdown('<div class="hero"><div class="kicker">PREDICTIVE OPERATIONS</div><h1>AI Prediction Center</h1><p>Estimate occupancy from the trained parking records and selected operating conditions.</p></div>',unsafe_allow_html=True)
    df=load_parking(); locations=sorted(df.parking_name.dropna().unique())
    with st.form("predict-form"):
        c1,c2,c3=st.columns(3)
        with c1: location=st.selectbox("Parking location",locations); target_date=st.date_input("Date",value=date.today())
        with c2: target_time=st.time_input("Time",value=time(17,0)); current=st.number_input("Current occupied spaces",min_value=0,value=0)
        with c3: capacity=st.number_input("Parking capacity",min_value=1,value=int(df.loc[df.parking_name==location,"capacity"].median())); traffic=st.selectbox("Traffic intensity",["Low","Medium","High","Critical"]); weather=st.selectbox("Weather",sorted(df.weather.dropna().astype(str).unique()))
        go=st.form_submit_button("Predict occupancy",type="primary")
    if not go: st.caption("Predictions are estimates from a supervised model fitted to the bundled demonstration dataset. The source records are not live telemetry."); return
    try:
        saved=get_parking_model(); model=saved["model"]; features=saved.get("features",[])
        target=pd.Timestamp(datetime.combine(target_date,target_time)); baseline=df[df.parking_name==location].sort_values("timestamp").iloc[-1]
        def make_row(ts):
            mapping={"hour":ts.hour,"day_of_week":ts.dayofweek,"month":ts.month,"location":location,"capacity":capacity,"occupied":current,"traffic":traffic,"weather":weather}
            # For current occupancy, use selected current value as prior occupancy only when model was trained with it.
            return {f:mapping.get(f, np.nan) for f in features}
        estimate=float(np.clip(model.predict(pd.DataFrame([make_row(target)]))[0],0,100))
        occupied=int(round(capacity*estimate/100)); available=max(0,capacity-occupied)
        demand="High" if estimate>=80 else "Moderate" if estimate>=55 else "Low"
        a,b,c=st.columns(3); a.metric("Predicted occupied",f"{occupied:,} spaces"); b.metric("Predicted available",f"{available:,} spaces"); c.metric("Expected occupancy",f"{estimate:.1f}%")
        st.caption(f"Demand level: {demand} · Model: {saved.get('model_name','Saved model')} · Estimate uses {saved.get('training_rows','unknown')} labeled training rows.")
        if estimate>=80: st.warning(f"High demand is expected at {location}. Consider checking a nearby alternative before arrival.")
        elif estimate>=55: st.info(f"Demand at {location} is expected to be moderate. Allow time to find a space.")
        else: st.success(f"The estimate suggests availability at {location}; {available:,} spaces may remain.")
        hours=pd.date_range(target,periods=24,freq="h"); curve=[float(np.clip(model.predict(pd.DataFrame([make_row(ts)]))[0],0,100)) for ts in hours]
        fig=px.area(x=hours,y=curve,labels={"x":"Time","y":"Estimated occupancy (%)"},title="Estimated demand · next 24 hours"); fig.update_layout(**THEME,height=350); st.plotly_chart(fig,use_container_width=True)
        metrics=saved.get("metrics")
        if metrics: st.caption("Held-out model evaluation (percentage-point error): "+" · ".join(f"{r['Model']}: MAE {r['MAE (percentage points)']:.1f}, RMSE {r['RMSE (percentage points)']:.1f}, R² {r['R²']:.2f}" for r in metrics))
        st.caption("Predictions are estimates based on historical demonstration records and the inputs above; conditions may change.")
        save_prediction(None,baseline.city,location,"Parking",{"date":str(target_date),"time":str(target_time),"capacity":capacity,"current_occupied":current,"traffic":traffic,"weather":weather},f"{occupied} spaces ({estimate:.1f}%)",None)
    except Exception as e: st.error(f"Could not generate a prediction: {e}")
