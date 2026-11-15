"""Train and evaluate occupancy regressors from supplied parking records."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeRegressor

BASE=Path(__file__).parent
DATA=BASE/"data"/"india_smart_parking_dataset_1000.csv"
MODEL=BASE/"models"/"parking_model.pkl"
TARGET="occupancy_rate"

def prepare_dataset(df):
    """Normalize compatible uploads into model features and occupancy target."""
    df=df.copy()
    if TARGET not in df and {"occupied","capacity"} <= set(df):
        df[TARGET]=100*pd.to_numeric(df.occupied,errors="coerce")/pd.to_numeric(df.capacity,errors="coerce").replace(0,np.nan)
    if TARGET not in df: raise ValueError("Provide occupancy_rate or both occupied and capacity columns.")
    if "hour" not in df and "time" in df: df["hour"]=pd.to_datetime(df.time.astype(str),errors="coerce").dt.hour
    if "day_of_week" not in df and "date" in df: df["day_of_week"]=pd.to_datetime(df.date,errors="coerce").dt.dayofweek
    if "month" not in df and "date" in df: df["month"]=pd.to_datetime(df.date,errors="coerce").dt.month
    if "day_of_week" in df and df.day_of_week.dtype==object:
        names={"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
        df["day_of_week"]=df.day_of_week.map(names).fillna(pd.to_numeric(df.day_of_week,errors="coerce"))
    aliases={"parking_name":"location","parking_location":"location","traffic_level":"traffic","weather":"weather"}
    for source,target in aliases.items():
        if source in df and target not in df: df[target]=df[source]
    features=[c for c in ["hour","day_of_week","month","location","capacity","occupied","traffic","weather"] if c in df]
    if not features: raise ValueError("No supported features found. Supported: hour, date/time, location, capacity, occupied, traffic_level, weather.")
    for col in ["hour","day_of_week","month","capacity","occupied"]:
        if col in df: df[col]=pd.to_numeric(df[col],errors="coerce")
    data=df[features+[TARGET]].replace([np.inf,-np.inf],np.nan).dropna(subset=[TARGET])
    data[TARGET]=data[TARGET].clip(0,100)
    if len(data)<12: raise ValueError("At least 12 valid labeled rows are required for a held-out evaluation.")
    return data,features

def evaluate_dataset(df):
    data,features=prepare_dataset(df); X=data[features]; y=data[TARGET]
    categorical=[c for c in features if X[c].dtype==object]; numeric=[c for c in features if c not in categorical]
    transform=ColumnTransformer([("numeric",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),numeric),
                                 ("categorical",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("encode",OneHotEncoder(handle_unknown="ignore"))]),categorical)])
    xtr,xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42)
    candidates={"Random Forest":RandomForestRegressor(n_estimators=180,min_samples_leaf=2,random_state=42),"Decision Tree":DecisionTreeRegressor(min_samples_leaf=4,random_state=42),"Linear Regression":LinearRegression()}
    fitted=[]; rows=[]
    for name,estimator in candidates.items():
        pipe=Pipeline([("features",transform),("model",estimator)])
        pipe.fit(xtr,ytr); pred=pipe.predict(xte)
        rows.append({"Model":name,"MAE (percentage points)":round(mean_absolute_error(yte,pred),2),"RMSE (percentage points)":round(mean_squared_error(yte,pred)**.5,2),"R²":round(r2_score(yte,pred),3)})
        fitted.append((rows[-1]["MAE (percentage points)"],pipe,name))
    best=min(fitted,key=lambda x:x[0]); return rows,(best[1],features,best[2],rows,len(data))

def train_models(dataset=None):
    """Train selected model and persist pipeline plus evaluation provenance."""
    source=pd.read_csv(DATA) if dataset is None else dataset
    scores,bundle=evaluate_dataset(source)
    model,features,name,metrics,count=bundle
    MODEL.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({"model":model,"features":features,"model_name":name,"metrics":metrics,"training_rows":count},MODEL)
    return metrics

if __name__=="__main__":
    print(train_models())
