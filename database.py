import sqlite3
import hashlib
import pandas as pd
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'smart_parking.db')

def init_db():
    """Initialize the database and create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Predictions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        city TEXT,
        location TEXT,
        prediction_type TEXT,
        input_data TEXT,
        result TEXT,
        confidence REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Parking table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parking_spots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        city TEXT,
        latitude REAL,
        longitude REAL,
        total_slots INTEGER,
        occupied_slots INTEGER,
        status TEXT
    )
    ''')
    
    # Traffic table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traffic_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zone_name TEXT,
        city TEXT,
        density_level TEXT,
        vehicle_count INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Reports table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        report_name TEXT,
        report_type TEXT,
        file_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Add default admin if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_pw = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                       ('admin', hashed_pw, 'admin@smartparking.ai', 'admin'))
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def add_user(username, password, email, role='user'):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                       (username, hashed_pw, email, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
    user = cursor.fetchone()
    conn.close()
    return user

def save_prediction(user_id, city, location, p_type, input_data, result, confidence):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO predictions (user_id, city, location, prediction_type, input_data, result, confidence)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, city, location, p_type, str(input_data), str(result), confidence))
    conn.commit()
    conn.close()

def save_upload_metadata(filename, row_count, columns):
    """Record uploaded dataset provenance without storing the file contents."""
    conn = get_connection()
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS dataset_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT NOT NULL,
            row_count INTEGER NOT NULL, columns_json TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.execute("INSERT INTO dataset_uploads (filename, row_count, columns_json) VALUES (?, ?, ?)",
                     (filename, int(row_count), json.dumps(list(columns))))
        conn.commit()
    finally:
        conn.close()

def get_user_predictions(user_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM predictions WHERE user_id = ? ORDER BY timestamp DESC", conn, params=(user_id,))
    conn.close()
    if 'confidence' not in df.columns:
        df['confidence'] = 0.0
    else:
        df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce').fillna(0.0)
    return df

def get_all_users():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, username, email, role, created_at FROM users", conn)
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
