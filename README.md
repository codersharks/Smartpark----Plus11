# SmartPark AI

A Streamlit smart parking and traffic analytics workspace. The bundled CSV files are labeled demonstration data; they are not live feeds or verified public measurements.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

The app includes a parking overview, prediction center, location directory and map, traffic analytics, CSV reports, and data/model notes. The reports page validates uploaded CSVs and can compare Random Forest, Decision Tree, and Linear Regression on a held-out split. The best model is saved with Joblib and evaluated scores; no accuracy or confidence estimate is invented. Predictions are estimates and depend on the supplied records and selected inputs.

## Dataset formats

The built-in overview expects `data/india_smart_parking_dataset_1000.csv` with location, coordinates, capacity, occupancy, date/time, weather, traffic category, and occupancy-rate fields. CSV uploads require either `occupancy_rate` or both `occupied` and `capacity`. Supported optional predictors include `hour`, `date`, `time`, `day_of_week`, `month`, `parking_name`/`location`, `traffic_level`, and `weather`.

## Project structure

- `app.py`: Streamlit navigation and entry point.
- `dashboard.py`: overview, location, traffic, and reports pages.
- `prediction.py`: model-backed occupancy prediction and 24-hour estimate.
- `train_model.py`: dataset preparation, model comparison, evaluation, and Joblib persistence.
- `database.py`: SQLite persistence for prediction history.
- `data/`: bundled demonstration CSVs and camera examples.
- `assets/style.css`: dark smart-city dashboard styling.
