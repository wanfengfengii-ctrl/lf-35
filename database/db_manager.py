import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .schema import ALL_TABLES


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "drip_monitor.db")


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._conn = None
            cls._instance._cursor = None
            cls._instance._db_path = DB_PATH
        return cls._instance

    def connect(self, db_path: str = DB_PATH):
        self._db_path = db_path
        if self._conn is None:
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._cursor = self._conn.cursor()
            self._init_tables()

    def _init_tables(self):
        for sql in ALL_TABLES:
            self._cursor.execute(sql)
        self._conn.commit()

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._cursor = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        if self._conn is None:
            self.connect(self._db_path)
        return self._cursor.execute(sql, params)

    def commit(self):
        if self._conn is not None:
            self._conn.commit()

    def rollback(self):
        if self._conn is not None:
            self._conn.rollback()

    def add_drip_point(self, code: str, name: str, location: str = "", description: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                "INSERT INTO drip_points (code, name, location, description) VALUES (?, ?, ?, ?)",
                (code, name, location, description)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "滴水点编号已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_drip_point(self, point_id: int, code: str, name: str, location: str, description: str) -> Tuple[bool, str]:
        try:
            self.execute(
                "UPDATE drip_points SET code=?, name=?, location=?, description=? WHERE id=?",
                (code, name, location, description, point_id)
            )
            self.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "滴水点编号已存在"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_drip_point(self, point_id: int) -> Tuple[bool, str]:
        data_count = self.get_monitoring_data_count(point_id)
        if data_count > 0:
            return False, f"该滴水点已有 {data_count} 条历史监测数据，禁止删除"
        
        try:
            self.execute("DELETE FROM anomaly_records WHERE drip_point_id=?", (point_id,))
            self.execute("DELETE FROM drip_points WHERE id=?", (point_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def force_delete_drip_point(self, point_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM anomaly_records WHERE drip_point_id=?", (point_id,))
            self.execute("DELETE FROM monitoring_data WHERE drip_point_id=?", (point_id,))
            self.execute("DELETE FROM drip_points WHERE id=?", (point_id,))
            self.commit()
            return True, "删除成功（含历史数据）"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_drip_point(self, point_id: int) -> Optional[Dict]:
        cursor = self.execute("SELECT * FROM drip_points WHERE id=?", (point_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_drip_point_by_code(self, code: str) -> Optional[Dict]:
        cursor = self.execute("SELECT * FROM drip_points WHERE code=?", (code,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_drip_points(self) -> List[Dict]:
        cursor = self.execute("SELECT * FROM drip_points ORDER BY code")
        return [dict(row) for row in cursor.fetchall()]

    def get_monitoring_data_count(self, point_id: int) -> int:
        cursor = self.execute("SELECT COUNT(*) FROM monitoring_data WHERE drip_point_id=?", (point_id,))
        return cursor.fetchone()[0]

    def add_monitoring_data(self, point_id: int, record_time: str, drip_interval: float,
                            temperature: Optional[float] = None, humidity: Optional[float] = None,
                            salinity: Optional[float] = None) -> Tuple[bool, str]:
        if drip_interval <= 0:
            return False, f"滴水间隔必须大于 0，当前值: {drip_interval}"
        
        try:
            self.execute(
                """INSERT INTO monitoring_data 
                   (drip_point_id, record_time, drip_interval, temperature, humidity, salinity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (point_id, record_time, drip_interval, temperature, humidity, salinity)
            )
            return True, ""
        except sqlite3.IntegrityError:
            return False, f"时间 {record_time} 已存在重复记录"
        except Exception as e:
            return False, str(e)

    def batch_add_monitoring_data(self, point_id: int, data_list: List[Dict]) -> Tuple[bool, str, int, int]:
        success_count = 0
        error_messages = []
        
        try:
            for idx, data in enumerate(data_list, 1):
                record_time = data.get("record_time", "")
                drip_interval = data.get("drip_interval", 0)
                
                if drip_interval <= 0:
                    error_messages.append(f"第 {idx} 行: 滴水间隔必须大于 0，当前值: {drip_interval}")
                    continue
                
                try:
                    self.execute(
                        """INSERT OR IGNORE INTO monitoring_data 
                           (drip_point_id, record_time, drip_interval, temperature, humidity, salinity)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (point_id, record_time, drip_interval, 
                         data.get("temperature"), data.get("humidity"), data.get("salinity"))
                    )
                    if self._cursor.rowcount > 0:
                        success_count += 1
                    else:
                        error_messages.append(f"第 {idx} 行: 时间 {record_time} 已存在，已跳过")
                except Exception as e:
                    error_messages.append(f"第 {idx} 行: {str(e)}")
            
            self.commit()
            return True, "\n".join(error_messages), success_count, len(data_list) - success_count
        except Exception as e:
            self.rollback()
            return False, f"批量导入失败: {str(e)}", success_count, len(data_list) - success_count

    def get_monitoring_data(self, point_id: int, start_time: str = "", end_time: str = "") -> List[Dict]:
        sql = "SELECT * FROM monitoring_data WHERE drip_point_id=?"
        params = [point_id]
        
        if start_time:
            sql += " AND record_time >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND record_time <= ?"
            params.append(end_time)
        
        sql += " ORDER BY record_time"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_data_by_season(self, point_id: int, season_months: List[int]) -> List[Dict]:
        sql = """SELECT * FROM monitoring_data 
                 WHERE drip_point_id=? AND CAST(strftime('%m', record_time) AS INTEGER) IN ({})
                 ORDER BY record_time""".format(','.join(['?'] * len(season_months)))
        params = [point_id] + season_months
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_data_year_range(self, point_id: int) -> Tuple[Optional[int], Optional[int]]:
        cursor = self.execute(
            """SELECT MIN(CAST(strftime('%Y', record_time) AS INTEGER)),
                      MAX(CAST(strftime('%Y', record_time) AS INTEGER))
               FROM monitoring_data WHERE drip_point_id=?""",
            (point_id,)
        )
        row = cursor.fetchone()
        return row[0], row[1]

    def add_anomaly_record(self, point_id: int, anomaly_type: str, risk_level: str,
                           start_time: str, end_time: Optional[str] = None, 
                           description: str = "") -> int:
        cursor = self.execute(
            """INSERT INTO anomaly_records 
               (drip_point_id, anomaly_type, risk_level, start_time, end_time, description)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (point_id, anomaly_type, risk_level, start_time, end_time, description)
        )
        self.commit()
        return cursor.lastrowid

    def get_anomaly_records(self, point_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT ar.*, dp.code as drip_point_code, dp.name as drip_point_name
                 FROM anomaly_records ar
                 JOIN drip_points dp ON ar.drip_point_id = dp.id"""
        params = []
        if point_id is not None:
            sql += " WHERE ar.drip_point_id=?"
            params.append(point_id)
        sql += " ORDER BY ar.created_at DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def delete_anomaly_record(self, anomaly_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM anomaly_records WHERE id=?", (anomaly_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"


def get_db() -> DatabaseManager:
    db = DatabaseManager()
    db.connect()
    return db
