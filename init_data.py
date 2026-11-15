import sqlite3
import os
from datetime import datetime, timedelta
import random

def get_table_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def init_sample_data():
    """Initialize database with sample data for dashboard"""
    
    db_path = os.path.join(os.path.dirname(__file__), 'database', 'smart_parking.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Initialize tables
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
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parking_zones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        total_spots INTEGER,
        occupied_spots INTEGER,
        occupancy_percent REAL,
        updated_at TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traffic_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hour INTEGER,
        entries INTEGER,
        exits INTEGER,
        revenue REAL,
        created_at TIMESTAMP
    )
    ''')
    
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
        timestamp TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dataset_uploads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        columns_json TEXT NOT NULL,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT,
        zone_name TEXT,
        message TEXT,
        severity TEXT,
        status TEXT,
        created_at TIMESTAMP
    )
    ''')
    
    conn.commit()
    
    # Check if admin user exists
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    admin = cursor.fetchone()
    
    if not admin:
        # Add admin user
        import hashlib
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', password_hash, 'admin@smartpark.com', 'admin'))
        conn.commit()
    
    # Add sample parking zones
    cursor.execute("SELECT COUNT(*) FROM parking_zones")
    if cursor.fetchone()[0] == 0:
        zones = [
            ("Main Lot (G1-G200)", 200, 162, 81.0),
            ("Level 1 (L1-100)", 100, 78, 78.0),
            ("Level 2 (L2-100)", 100, 92, 92.0),
            ("South Lot (S1-S150)", 150, 97, 65.0),
        ]
        
        now = datetime.now()
        for name, total, occupied, percent in zones:
            cursor.execute('''
                INSERT INTO parking_zones (name, total_spots, occupied_spots, occupancy_percent, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, total, occupied, percent, now))
        conn.commit()
    
    # Add sample traffic data for today
    cursor.execute("SELECT COUNT(*) FROM traffic_data")
    if cursor.fetchone()[0] == 0:
        hours_data = [
            (0, 80, 75, 400),
            (1, 95, 90, 475),
            (2, 110, 100, 550),
            (3, 140, 130, 700),
            (4, 180, 160, 900),
            (5, 220, 195, 1100),
            (6, 240, 210, 1200),
            (7, 210, 180, 1050),
            (8, 190, 160, 950),
            (9, 170, 150, 850),
            (10, 160, 145, 800),
            (11, 180, 160, 900),
            (12, 200, 180, 1000),
            (13, 190, 175, 950),
            (14, 210, 190, 1050),
            (15, 240, 220, 1200),
            (16, 280, 250, 1400),
            (17, 310, 280, 1550),
            (18, 290, 260, 1450),
            (19, 260, 230, 1300),
            (20, 200, 180, 1000),
            (21, 150, 140, 750),
            (22, 120, 110, 600),
            (23, 100, 95, 500),
        ]
        
        for hour, entries, exits, revenue in hours_data:
            cursor.execute('''
                INSERT INTO traffic_data (hour, entries, exits, revenue)
                VALUES (?, ?, ?, ?)
            ''', (hour, entries, exits, revenue))
        conn.commit()
    
    # Add sample alerts
    cursor.execute("SELECT COUNT(*) FROM alerts")
    if cursor.fetchone()[0] == 0:
        alerts = [
            ("Critical", "Level 2 (L2-100)", "Level 2 at 92% capacity - nearing full", "Critical", "Active"),
            ("Warning", "Main Lot (G1-G200)", "Peak hour approaching in 3 hours", "Warning", "Active"),
            ("Info", "South Lot (S1-S150)", "Daily revenue target achieved", "Info", "Resolved"),
        ]
        
        now = datetime.now()
        for alert_type, zone, msg, severity, status in alerts:
            cursor.execute('''
                INSERT INTO alerts (alert_type, zone_name, message, severity, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_type, zone, msg, severity, status, now))
        conn.commit()
    
    # Migrate old predictions schema if needed
    existing_predictions = get_table_columns(cursor, 'predictions')
    if existing_predictions:
        missing_columns = []
        expected_columns = {
            'city': 'TEXT',
            'location': 'TEXT',
            'prediction_type': 'TEXT',
            'input_data': 'TEXT',
            'result': 'TEXT',
            'confidence': 'REAL',
        }
        for col, col_type in expected_columns.items():
            if col not in existing_predictions:
                missing_columns.append((col, col_type))
        for col, col_type in missing_columns:
            cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col} {col_type}")
        conn.commit()
    
    conn.close()
    print("✓ Sample data initialized successfully!")

if __name__ == "__main__":
    init_sample_data()
