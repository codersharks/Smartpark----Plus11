"""Data-backed SmartPark dashboard and analytics pages."""
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

DATA = Path(__file__).parent / "data"
THEME = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#dce9ff", margin=dict(l=12,r=12,t=38,b=12))

@st.cache_data
def load_parking():
    """Read the bundled structured demonstration dataset."""
    path = DATA / "india_smart_parking_dataset_1000.csv"
    df = pd.read_csv(path)
    required = {"parking_name", "city", "latitude", "longitude", "capacity", "occupied", "available", "occupancy_rate", "date", "time", "weather", "traffic_level"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    df["capacity"] = pd.to_numeric(df.capacity, errors="coerce")
    df["occupied"] = pd.to_numeric(df.occupied, errors="coerce")
    df = df.dropna(subset=["capacity", "occupied", "date", "time"])
    df["occupied"] = df.occupied.clip(lower=0).where(lambda x: x <= df.capacity, df.capacity)
    df["available"] = (df.capacity - df.occupied).clip(lower=0)
    df["timestamp"] = pd.to_datetime(df.date.astype(str) + " " + df.time.astype(str), errors="coerce")
    df["hour"] = df.timestamp.dt.hour
    df["weekday"] = df.timestamp.dt.day_name()
    return df.dropna(subset=["timestamp"])

def _chart(fig, height=310):
    fig.update_layout(**THEME, height=height)
    st.plotly_chart(fig, use_container_width=True)

def _header(kicker, title, desc):
    st.markdown(f'<div class="hero"><div class="kicker">{kicker}</div><h1>{title}</h1><p>{desc}</p></div>', unsafe_allow_html=True)

def show_dashboard():
    _header("SMART CITY OPERATIONS  /  OVERVIEW", "Parking intelligence, at a glance", "Occupancy and demand signals from the bundled parking records.")
    try: df = load_parking()
    except (OSError, ValueError, pd.errors.ParserError) as e:
        st.error(f"Could not load parking dataset: {e}"); return
    latest = df.sort_values("timestamp").groupby("parking_name", as_index=False).tail(1)
    capacity = int(latest.capacity.sum()); occupied = int(latest.occupied.sum()); available = capacity-occupied
    pct = occupied / capacity * 100 if capacity else 0
    predicted = pd.to_numeric(latest.get("predicted_occupancy_rate", pd.Series(dtype=float)), errors="coerce").mean()
    traffic = latest.traffic_level.mode().iat[0] if not latest.empty else "Unavailable"
    st.caption(f"{len(df):,} records · {df.city.nunique()} cities · Snapshot based on the latest record per parking site. Bundled dataset; not a live feed.")
    cards = st.columns(6)
    for c, label, value, hint in zip(cards, ["Total spaces","Occupied","Available","Occupancy","Model forecast","Traffic level"], [f"{capacity:,}",f"{occupied:,}",f"{available:,}",f"{pct:.1f}%",f"{predicted:.1f}%" if pd.notna(predicted) else "Not available",str(traffic)], ["Across listed sites","Latest site records","Currently reported free","Of listed capacity","Mean site forecast" if pd.notna(predicted) else "No forecast column","Most common at sites"]):
        with c: st.markdown(f'<div class="metric-card"><div>{label}</div><strong>{value}</strong><small>{hint}</small></div>', unsafe_allow_html=True)
    left,right=st.columns([1,1])
    with left:
        st.subheader("Capacity utilization")
        _chart(px.pie(names=["Occupied","Available"],values=[occupied,available],hole=.68,color_discrete_sequence=["#31d6ff","#7858ff"]))
    with right:
        st.subheader("Occupancy by site")
        by=latest.assign(occupancy_pct=100*latest.occupied/latest.capacity).sort_values("occupancy_pct")
        _chart(px.bar(by,x="occupancy_pct",y="parking_name",color="occupancy_pct",orientation="h",labels={"occupancy_pct":"Occupancy (%)","parking_name":"Site"},color_continuous_scale=["#20d6c7","#418cff","#b34fff"],hover_data=["city","occupied","capacity"]))
    left,right=st.columns(2)
    with left:
        st.subheader("Observed hourly occupancy")
        hourly=df.groupby("hour").agg(occupied=("occupied","mean"),capacity=("capacity","mean")).reset_index()
        hourly["occupancy_pct"]=hourly.occupied/hourly.capacity*100
        _chart(px.line(hourly,x="hour",y="occupancy_pct",markers=True,labels={"hour":"Hour of day","occupancy_pct":"Mean occupancy (%)"}))
    with right:
        st.subheader("Traffic mix")
        _chart(px.pie(df, names="traffic_level", hole=.58, color="traffic_level", color_discrete_map={"Low":"#28d8be","Medium":"#6397ff","High":"#b35cff","Critical":"#ff5878"}))
    st.subheader("Occupancy by weekday and hour")
    heat=df.pivot_table(index="weekday",columns="hour",values="occupancy_rate",aggfunc="mean")
    order=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    heat=heat.reindex([x for x in order if x in heat.index])
    _chart(px.imshow(heat,aspect="auto",color_continuous_scale="Viridis",labels=dict(x="Hour",y="Day",color="Occupancy (%)")), height=340)
    st.subheader("Operational recommendations")
    fullest=by.iloc[-1]; emptiest=by.iloc[0]
    if pct>=80: st.warning(f"Network occupancy is {pct:.0f}%. Check {emptiest.parking_name} in {emptiest.city}, currently at {emptiest.occupancy_pct:.0f}% occupancy, before directing drivers elsewhere.")
    else: st.info(f"Network occupancy is {pct:.0f}%. {emptiest.parking_name} in {emptiest.city} has the lowest observed occupancy ({emptiest.occupancy_pct:.0f}%), while {fullest.parking_name} is the fullest ({fullest.occupancy_pct:.0f}%).")

def show_locations():
    _header("ASSET DIRECTORY", "Parking locations", "Search current site records and compare capacity, availability, and reported status.")
    df=load_parking(); latest=df.sort_values("timestamp").groupby("parking_name",as_index=False).tail(1).copy()
    a,b=st.columns([2,1]); query=a.text_input("Search location or city"); cities=["All cities"]+sorted(latest.city.dropna().unique().tolist()); city=b.selectbox("City",cities)
    if query: latest=latest[latest.parking_name.str.contains(query,case=False,na=False)|latest.city.str.contains(query,case=False,na=False)]
    if city!="All cities": latest=latest[latest.city==city]
    latest["Occupancy %"]=(latest.occupied/latest.capacity*100).round(1); latest["Status"]=np.select([latest["Occupancy %"]>=90,latest["Occupancy %"]>=70],["Nearly full","Filling"],default="Available")
    st.dataframe(latest[["parking_name","city","capacity","occupied","available","Occupancy %","Status","timestamp"]].rename(columns={"parking_name":"Location","city":"City","capacity":"Capacity","occupied":"Occupied","available":"Available","timestamp":"Updated from record"}),use_container_width=True,hide_index=True)
    st.subheader("Site map")
    st.caption("Map coordinates are from the bundled dataset; values are not live telemetry.")
    st.map(latest.rename(columns={"latitude":"lat","longitude":"lon"})[["lat","lon"]],zoom=4)

def show_traffic():
    _header("NETWORK FLOW", "Traffic analytics", "Explore traffic intensity associated with the parking records.")
    df=load_parking(); levels=[x for x in ["Low","Medium","High","Critical"] if x in df.traffic_level.unique()]
    a,b=st.columns(2)
    with a:
        st.subheader("Traffic intensity distribution"); _chart(px.histogram(df,x="traffic_level",category_orders={"traffic_level":levels},color="traffic_level",labels={"traffic_level":"Intensity","count":"Records"}))
    with b:
        st.subheader("Traffic level by hour"); _chart(px.histogram(df,x="hour",color="traffic_level",barmode="group",category_orders={"traffic_level":levels},labels={"hour":"Hour of day","count":"Records"}))
    if "traffic_volume" in df:
        st.subheader("Traffic volume trend"); _chart(px.line(df.groupby("hour",as_index=False).traffic_volume.mean(),x="hour",y="traffic_volume",markers=True))
    else: st.info("The supplied parking dataset has traffic intensity categories but no numeric traffic volume or timestamped independent traffic series. Numeric volume forecasting is unavailable.")
    st.dataframe(df.groupby("traffic_level",as_index=False).agg(records=("parking_name","size"),sites=("parking_name","nunique")),hide_index=True,use_container_width=True)

def show_reports():
    _header("REPORTING", "Reports & model evidence", "Export source records and inspect supported model evaluation without invented scores.")
    df=load_parking(); period=st.selectbox("Reporting period",["Daily","Weekly","Monthly"])
    freq={"Daily":"D","Weekly":"W","Monthly":"MS"}[period]
    report=df.set_index("timestamp").groupby("parking_name").resample(freq).agg(records=("occupied","size"),mean_occupied=("occupied","mean"),mean_capacity=("capacity","mean"),mean_occupancy_pct=("occupancy_rate","mean")).reset_index()
    st.dataframe(report,use_container_width=True,hide_index=True)
    st.download_button("Download report CSV",report.to_csv(index=False).encode(),file_name=f"smartpark_{period.lower()}_report.csv",mime="text/csv")
    st.subheader("Actual vs dataset forecast")
    if "predicted_occupancy_rate" in df:
        sample=df.dropna(subset=["predicted_occupancy_rate","occupancy_rate"])
        _chart(px.scatter(sample,x="occupancy_rate",y="predicted_occupancy_rate",color="traffic_level",labels={"occupancy_rate":"Reported occupancy (%)","predicted_occupancy_rate":"Dataset forecast (%)"},hover_data=["parking_name","city"]))
        st.caption("This compares the dataset's supplied forecast column with reported occupancy. It is not an evaluation of the bundled model.")
    else: st.info("The dataset has no predicted_occupancy_rate column, so actual-versus-predicted comparison is unavailable.")
    st.subheader("Saved model evaluation")
    model_path=Path(__file__).parent/"models"/"parking_model.pkl"
    if model_path.exists():
        try:
            import joblib
            artifact=joblib.load(model_path)
            if isinstance(artifact,dict) and artifact.get("metrics"):
                st.dataframe(pd.DataFrame(artifact["metrics"]),use_container_width=True,hide_index=True)
                st.caption(f"Selected model: {artifact.get('model_name','unknown')} · Evaluated on held-out records from {artifact.get('training_rows','unknown')} labeled rows.")
            else: st.info("A legacy model artifact exists without evaluation provenance. It will be replaced when you make a prediction or train from uploaded data.")
        except Exception as e: st.warning(f"Unable to read model evaluation metadata: {e}")
    else: st.info("No evaluated model has been saved yet. Request a prediction to train on bundled data, or upload a CSV to compare and save models.")
    st.subheader("Train and evaluate a model on uploaded records")
    st.caption("Model scores are only shown after a valid upload and a held-out evaluation. Bundled records are demonstration data and may not represent independent observations.")
    upload=st.file_uploader("Upload CSV",type=["csv"],key="report_upload")
    if upload:
        try:
            uploaded=pd.read_csv(upload)
            has_target="occupancy_rate" in uploaded or {"occupied","capacity"} <= set(uploaded)
            supported={"hour","date","time","day_of_week","month","parking_name","location","capacity","occupied","traffic_level","traffic","weather"}
            unsupported=sorted(set(uploaded.columns)-supported-{"occupancy_rate","latitude","longitude","available","city","parking_id","vehicle_type","parking_fee_per_hour","avg_parking_duration_hours","predicted_occupancy_rate"})
            if not has_target: st.error("Unsupported CSV: include occupancy_rate, or both occupied and capacity. Supported optional predictors include hour/date/time, location, traffic, and weather.")
            else:
                if unsupported: st.info("Unused columns (not supported as model features): "+", ".join(unsupported))
                st.success(f"CSV valid: {len(uploaded):,} rows; {len(uploaded.columns)} columns.")
                st.dataframe(uploaded.head(10),use_container_width=True)
                if st.button("Train, compare, and save best model from upload"):
                    from train_model import train_models
                    from database import save_upload_metadata
                    scores=train_models(uploaded)
                    save_upload_metadata(upload.name, len(uploaded), uploaded.columns.tolist())
                    st.dataframe(pd.DataFrame(scores),use_container_width=True,hide_index=True)
                    st.success("Best evaluated pipeline saved. The Prediction Center will use this dataset until another training run replaces it.")
        except Exception as e: st.error(f"Could not read uploaded CSV: {e}")
