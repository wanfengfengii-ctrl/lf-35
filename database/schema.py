CREATE_TABLE_CAVE_AREAS = """
CREATE TABLE IF NOT EXISTS cave_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT,
    geological_type TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
)
"""

CREATE_TABLE_CAVE_ZONES = """
CREATE TABLE IF NOT EXISTS cave_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    layer TEXT,
    elevation REAL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (area_id) REFERENCES cave_areas(id) ON DELETE CASCADE,
    UNIQUE(area_id, code)
)
"""

CREATE_TABLE_DEVICES = """
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    model TEXT,
    manufacturer TEXT,
    sensor_type TEXT,
    install_date TEXT,
    status TEXT NOT NULL DEFAULT '在用',
    drip_point_id INTEGER,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE SET NULL
)
"""

CREATE_TABLE_CALIBRATION_RECORDS = """
CREATE TABLE IF NOT EXISTS calibration_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    calibration_date TEXT NOT NULL,
    operator TEXT,
    before_value REAL,
    after_value REAL,
    error REAL,
    certificate_no TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_DRIP_POINTS = """
CREATE TABLE IF NOT EXISTS drip_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area_id INTEGER,
    zone_id INTEGER,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT,
    elevation REAL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (area_id) REFERENCES cave_areas(id) ON DELETE SET NULL,
    FOREIGN KEY (zone_id) REFERENCES cave_zones(id) ON DELETE SET NULL
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
    quality_score REAL,
    batch_id INTEGER,
    is_manual INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE,
    UNIQUE(drip_point_id, record_time)
)
"""

CREATE_TABLE_DATA_IMPORT_BATCHES = """
CREATE TABLE IF NOT EXISTS data_import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drip_point_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    quality_score REAL,
    imported_by TEXT,
    imported_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE
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
    status TEXT NOT NULL DEFAULT '待处理',
    handler TEXT,
    handling_time TEXT,
    handling_result TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_HANDLING_RECORDS = """
CREATE TABLE IF NOT EXISTS handling_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    anomaly_id INTEGER NOT NULL,
    handler TEXT NOT NULL,
    handle_time TEXT NOT NULL,
    status TEXT NOT NULL,
    measures TEXT,
    result TEXT,
    follow_up_date TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (anomaly_id) REFERENCES anomaly_records(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_QUALITY_CONTROL_RECORDS = """
CREATE TABLE IF NOT EXISTS quality_control_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    drip_point_id INTEGER,
    check_type TEXT NOT NULL,
    row_num INTEGER,
    field_name TEXT,
    original_value TEXT,
    issue_description TEXT,
    severity TEXT,
    handled INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES data_import_batches(id) ON DELETE CASCADE,
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE
)
"""

CREATE_INDEX_MONITORING_TIME = """
CREATE INDEX IF NOT EXISTS idx_monitoring_drip_time
ON monitoring_data(drip_point_id, record_time)
"""

CREATE_INDEX_ANOMALY_STATUS = """
CREATE INDEX IF NOT EXISTS idx_anomaly_status
ON anomaly_records(status, risk_level)
"""

CREATE_INDEX_CALIBRATION_DEVICE = """
CREATE INDEX IF NOT EXISTS idx_calibration_device
ON calibration_records(device_id, calibration_date)
"""

CREATE_TABLE_MAINTENANCE_WORK_ORDERS = """
CREATE TABLE IF NOT EXISTS maintenance_work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    anomaly_id INTEGER,
    drip_point_id INTEGER,
    area_id INTEGER,
    zone_id INTEGER,
    anomaly_type TEXT,
    risk_level TEXT NOT NULL DEFAULT '中',
    assignee TEXT,
    status TEXT NOT NULL DEFAULT '待处理',
    priority TEXT NOT NULL DEFAULT '普通',
    plan_inspect_time TEXT,
    actual_arrive_time TEXT,
    handle_duration INTEGER,
    description TEXT,
    inspection_content TEXT,
    measures TEXT,
    recheck_conclusion TEXT,
    notes TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    closed_at TEXT,
    FOREIGN KEY (anomaly_id) REFERENCES anomaly_records(id) ON DELETE SET NULL,
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE SET NULL,
    FOREIGN KEY (area_id) REFERENCES cave_areas(id) ON DELETE SET NULL,
    FOREIGN KEY (zone_id) REFERENCES cave_zones(id) ON DELETE SET NULL
)
"""

CREATE_TABLE_INSPECTION_RECORDS = """
CREATE TABLE IF NOT EXISTS inspection_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    inspector TEXT NOT NULL,
    inspect_time TEXT NOT NULL,
    inspection_content TEXT,
    measures TEXT,
    result TEXT,
    recheck_conclusion TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_WORK_ORDER_ATTACHMENTS = """
CREATE TABLE IF NOT EXISTS work_order_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    uploaded_by TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_INDEX_WORK_ORDER_STATUS = """
CREATE INDEX IF NOT EXISTS idx_work_order_status
ON maintenance_work_orders(status, risk_level, assignee)
"""

CREATE_INDEX_WORK_ORDER_TIME = """
CREATE INDEX IF NOT EXISTS idx_work_order_time
ON maintenance_work_orders(plan_inspect_time, created_at)
"""

CREATE_INDEX_INSPECTION_ORDER = """
CREATE INDEX IF NOT EXISTS idx_inspection_order
ON inspection_records(work_order_id, inspect_time)
"""

CREATE_TABLE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    real_name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    department TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    last_login TEXT
)
"""

CREATE_TABLE_USER_PERMISSIONS = """
CREATE TABLE IF NOT EXISTS user_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    permission TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, permission)
)
"""

CREATE_TABLE_APPROVAL_RECORDS = """
CREATE TABLE IF NOT EXISTS approval_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    approver_id INTEGER,
    approver_name TEXT,
    approval_step INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approval_opinion TEXT,
    approval_time TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_INSPECTION_ROUTES = """
CREATE TABLE IF NOT EXISTS inspection_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_name TEXT NOT NULL,
    route_code TEXT NOT NULL UNIQUE,
    area_id INTEGER,
    description TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (area_id) REFERENCES cave_areas(id) ON DELETE SET NULL
)
"""

CREATE_TABLE_ROUTE_POINTS = """
CREATE TABLE IF NOT EXISTS route_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    drip_point_id INTEGER NOT NULL,
    sequence INTEGER NOT NULL DEFAULT 0,
    estimated_duration INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (route_id) REFERENCES inspection_routes(id) ON DELETE CASCADE,
    FOREIGN KEY (drip_point_id) REFERENCES drip_points(id) ON DELETE CASCADE,
    UNIQUE(route_id, drip_point_id)
)
"""

CREATE_TABLE_ROUTE_ASSIGNMENTS = """
CREATE TABLE IF NOT EXISTS route_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER NOT NULL,
    assignee TEXT NOT NULL,
    plan_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    actual_start_time TEXT,
    actual_end_time TEXT,
    completed_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (route_id) REFERENCES inspection_routes(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_REMINDER_RECORDS = """
CREATE TABLE IF NOT EXISTS reminder_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    reminder_type TEXT NOT NULL,
    reminder_content TEXT,
    recipient TEXT,
    reminder_time TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_WORK_ORDER_ESCALATIONS = """
CREATE TABLE IF NOT EXISTS work_order_escalations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    escalation_level INTEGER NOT NULL DEFAULT 1,
    escalation_reason TEXT,
    escalated_to TEXT,
    escalated_by TEXT,
    escalation_time TEXT NOT NULL,
    response TEXT,
    response_time TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_TABLE_WORK_ORDER_HISTORY = """
CREATE TABLE IF NOT EXISTS work_order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_order_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    operator TEXT,
    operation_time TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    remarks TEXT,
    FOREIGN KEY (work_order_id) REFERENCES maintenance_work_orders(id) ON DELETE CASCADE
)
"""

CREATE_INDEX_USER_ROLE = """
CREATE INDEX IF NOT EXISTS idx_user_role
ON users(role, status)
"""

CREATE_INDEX_APPROVAL_ORDER = """
CREATE INDEX IF NOT EXISTS idx_approval_order
ON approval_records(work_order_id, approval_status)
"""

CREATE_INDEX_REMINDER_ORDER = """
CREATE INDEX IF NOT EXISTS idx_reminder_order
ON reminder_records(work_order_id, is_read)
"""

CREATE_INDEX_ESCALATION_ORDER = """
CREATE INDEX IF NOT EXISTS idx_escalation_order
ON work_order_escalations(work_order_id, escalation_level)
"""

CREATE_INDEX_ROUTE_ASSIGNEE = """
CREATE INDEX IF NOT EXISTS idx_route_assignee
ON route_assignments(assignee, plan_date, status)
"""

ALL_TABLES = [
    CREATE_TABLE_CAVE_AREAS,
    CREATE_TABLE_CAVE_ZONES,
    CREATE_TABLE_DRIP_POINTS,
    CREATE_TABLE_DEVICES,
    CREATE_TABLE_CALIBRATION_RECORDS,
    CREATE_TABLE_MONITORING_DATA,
    CREATE_TABLE_DATA_IMPORT_BATCHES,
    CREATE_TABLE_ANOMALY_RECORDS,
    CREATE_TABLE_HANDLING_RECORDS,
    CREATE_TABLE_QUALITY_CONTROL_RECORDS,
    CREATE_TABLE_MAINTENANCE_WORK_ORDERS,
    CREATE_TABLE_INSPECTION_RECORDS,
    CREATE_TABLE_WORK_ORDER_ATTACHMENTS,
    CREATE_TABLE_USERS,
    CREATE_TABLE_USER_PERMISSIONS,
    CREATE_TABLE_APPROVAL_RECORDS,
    CREATE_TABLE_INSPECTION_ROUTES,
    CREATE_TABLE_ROUTE_POINTS,
    CREATE_TABLE_ROUTE_ASSIGNMENTS,
    CREATE_TABLE_REMINDER_RECORDS,
    CREATE_TABLE_WORK_ORDER_ESCALATIONS,
    CREATE_TABLE_WORK_ORDER_HISTORY,
    CREATE_INDEX_MONITORING_TIME,
    CREATE_INDEX_ANOMALY_STATUS,
    CREATE_INDEX_CALIBRATION_DEVICE,
    CREATE_INDEX_WORK_ORDER_STATUS,
    CREATE_INDEX_WORK_ORDER_TIME,
    CREATE_INDEX_INSPECTION_ORDER,
    CREATE_INDEX_USER_ROLE,
    CREATE_INDEX_APPROVAL_ORDER,
    CREATE_INDEX_REMINDER_ORDER,
    CREATE_INDEX_ESCALATION_ORDER,
    CREATE_INDEX_ROUTE_ASSIGNEE,
]
