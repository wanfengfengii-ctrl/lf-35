CREATE_TABLE_DRIP_POINTS = """
CREATE TABLE IF NOT EXISTS drip_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
)
"""

CREATE_TABLE_MONITORING_DATA = """
CREATE TABLE IF NOT EXISTS monitoring_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drip_point_id INTEGER NOT NULL,
    record_time TEXT NOT NULL,
    drip_interval REAL NOT NULL,
    temperature REAL,
    humidity REAL,
    salinity REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE,
    UNIQUE(drip_point_id, record_time)
)
"""

CREATE_TABLE_ANOMALY_RECORDS = """
CREATE TABLE IF NOT EXISTS anomaly_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drip_point_id INTEGER NOT NULL,
    anomaly_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE
)
"""

CREATE_INDEX_MONITORING_TIME = """
CREATE INDEX IF NOT EXISTS idx_monitoring_drip_time
ON monitoring_data(drip_point_id, record_time)
"""

ALL_TABLES = [
    CREATE_TABLE_DRIP_POINTS,
    CREATE_TABLE_MONITORING_DATA,
    CREATE_TABLE_ANOMALY_RECORDS,
    CREATE_INDEX_MONITORING_TIME,
]
