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

    def add_cave_area(self, code: str, name: str, location: str = "", 
                      geological_type: str = "", description: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO cave_areas (code, name, location, geological_type, description) 
                   VALUES (?, ?, ?, ?, ?)""",
                (code, name, location, geological_type, description)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "洞区编号已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_cave_area(self, area_id: int, code: str, name: str, location: str,
                         geological_type: str, description: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE cave_areas SET code=?, name=?, location=?, 
                   geological_type=?, description=? WHERE id=?""",
                (code, name, location, geological_type, description, area_id)
            )
            self.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "洞区编号已存在"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_cave_area(self, area_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM cave_areas WHERE id=?", (area_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_cave_area(self, area_id: int) -> Optional[Dict]:
        cursor = self.execute("SELECT * FROM cave_areas WHERE id=?", (area_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_cave_areas(self) -> List[Dict]:
        cursor = self.execute("SELECT * FROM cave_areas ORDER BY code")
        return [dict(row) for row in cursor.fetchall()]

    def get_cave_area_stats(self, area_id: int) -> Dict:
        cursor = self.execute(
            """SELECT 
                (SELECT COUNT(*) FROM cave_zones WHERE area_id=?) as zone_count,
                (SELECT COUNT(*) FROM drip_points WHERE area_id=?) as point_count,
                (SELECT COUNT(*) FROM monitoring_data md 
                 JOIN drip_points dp ON md.drip_point_id = dp.id 
                 WHERE dp.area_id=?) as data_count
            """, (area_id, area_id, area_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    def add_cave_zone(self, area_id: int, code: str, name: str, layer: str = "",
                      elevation: Optional[float] = None, description: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO cave_zones (area_id, code, name, layer, elevation, description) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (area_id, code, name, layer, elevation, description)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "子区域编号在该洞区已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_cave_zone(self, zone_id: int, area_id: int, code: str, name: str,
                         layer: str, elevation: Optional[float], description: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE cave_zones SET area_id=?, code=?, name=?, 
                   layer=?, elevation=?, description=? WHERE id=?""",
                (area_id, code, name, layer, elevation, description, zone_id)
            )
            self.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "子区域编号在该洞区已存在"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_cave_zone(self, zone_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM cave_zones WHERE id=?", (zone_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_cave_zone(self, zone_id: int) -> Optional[Dict]:
        cursor = self.execute(
            """SELECT cz.*, ca.code as area_code, ca.name as area_name 
               FROM cave_zones cz JOIN cave_areas ca ON cz.area_id = ca.id 
               WHERE cz.id=?""", (zone_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_zones_by_area(self, area_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM cave_zones WHERE area_id=? ORDER BY code", (area_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def add_device(self, code: str, name: str, model: str = "", manufacturer: str = "",
                   sensor_type: str = "", install_date: str = "", status: str = "在用",
                   drip_point_id: Optional[int] = None, description: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO devices (code, name, model, manufacturer, sensor_type, 
                   install_date, status, drip_point_id, description) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (code, name, model, manufacturer, sensor_type, install_date, 
                 status, drip_point_id, description)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "设备编号已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_device(self, device_id: int, code: str, name: str, model: str,
                      manufacturer: str, sensor_type: str, install_date: str,
                      status: str, drip_point_id: Optional[int], description: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE devices SET code=?, name=?, model=?, manufacturer=?, 
                   sensor_type=?, install_date=?, status=?, drip_point_id=?, description=? 
                   WHERE id=?""",
                (code, name, model, manufacturer, sensor_type, install_date,
                 status, drip_point_id, description, device_id)
            )
            self.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "设备编号已存在"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_device(self, device_id: int) -> Tuple[bool, str]:
        calib_count = self.get_calibration_count(device_id)
        if calib_count > 0:
            return False, f"该设备已有 {calib_count} 条校准记录，禁止删除"
        try:
            self.execute("DELETE FROM devices WHERE id=?", (device_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_device(self, device_id: int) -> Optional[Dict]:
        cursor = self.execute(
            """SELECT d.*, dp.code as drip_point_code, dp.name as drip_point_name 
               FROM devices d LEFT JOIN drip_points dp ON d.drip_point_id = dp.id 
               WHERE d.id=?""", (device_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_devices(self) -> List[Dict]:
        cursor = self.execute(
            """SELECT d.*, dp.code as drip_point_code, dp.name as drip_point_name 
               FROM devices d LEFT JOIN drip_points dp ON d.drip_point_id = dp.id 
               ORDER BY d.code"""
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_devices_by_point(self, point_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM devices WHERE drip_point_id=? ORDER BY code", (point_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_calibration_count(self, device_id: int) -> int:
        cursor = self.execute(
            "SELECT COUNT(*) FROM calibration_records WHERE device_id=?", (device_id,)
        )
        return cursor.fetchone()[0]

    def add_calibration_record(self, device_id: int, calibration_date: str,
                               operator: str = "", before_value: Optional[float] = None,
                               after_value: Optional[float] = None, error: Optional[float] = None,
                               certificate_no: str = "", notes: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO calibration_records (device_id, calibration_date, operator,
                   before_value, after_value, error, certificate_no, notes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (device_id, calibration_date, operator, before_value, 
                 after_value, error, certificate_no, notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_calibration_record(self, record_id: int, device_id: int, calibration_date: str,
                                  operator: str, before_value: Optional[float],
                                  after_value: Optional[float], error: Optional[float],
                                  certificate_no: str, notes: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE calibration_records SET device_id=?, calibration_date=?, operator=?,
                   before_value=?, after_value=?, error=?, certificate_no=?, notes=? 
                   WHERE id=?""",
                (device_id, calibration_date, operator, before_value,
                 after_value, error, certificate_no, notes, record_id)
            )
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_calibration_record(self, record_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM calibration_records WHERE id=?", (record_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_calibration_records(self, device_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT cr.*, d.code as device_code, d.name as device_name 
                 FROM calibration_records cr JOIN devices d ON cr.device_id = d.id"""
        params = ()
        if device_id is not None:
            sql += " WHERE cr.device_id=?"
            params = (device_id,)
        sql += " ORDER BY cr.calibration_date DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_drip_point(self, code: str, name: str, location: str = "", 
                       area_id: Optional[int] = None, zone_id: Optional[int] = None,
                       elevation: Optional[float] = None, description: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO drip_points (code, name, location, area_id, zone_id, elevation, description) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (code, name, location, area_id, zone_id, elevation, description)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "滴水点编号已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_drip_point(self, point_id: int, code: str, name: str, location: str,
                          area_id: Optional[int], zone_id: Optional[int],
                          elevation: Optional[float], description: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE drip_points SET code=?, name=?, location=?, 
                   area_id=?, zone_id=?, elevation=?, description=? WHERE id=?""",
                (code, name, location, area_id, zone_id, elevation, description, point_id)
            )
            self.commit()
            return True, "更新成功"
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "滴水点编号已存在"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def get_drip_points_by_area(self, area_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM drip_points WHERE area_id=? ORDER BY code", (area_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_drip_points_by_zone(self, zone_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM drip_points WHERE zone_id=? ORDER BY code", (zone_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

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

    def update_anomaly_status(self, anomaly_id: int, status: str, handler: str = "",
                          handling_time: str = "", handling_result: str = "") -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE anomaly_records SET status=?, handler=?, handling_time=?, handling_result=?
                   WHERE id=?""",
                (status, handler, handling_time, handling_result, anomaly_id)
            )
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def get_anomalies_by_status(self, status: Optional[str] = None, risk_level: Optional[str] = None,
                             area_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT ar.*, dp.code as drip_point_code, dp.name as drip_point_name,
                 dp.area_id, dp.zone_id
                 FROM anomaly_records ar
                 JOIN drip_points dp ON ar.drip_point_id = dp.id
                 WHERE 1=1"""
        params = []
        if status:
            sql += " AND ar.status=?"
            params.append(status)
        if risk_level:
            sql += " AND ar.risk_level=?"
            params.append(risk_level)
        if area_id:
            sql += " AND dp.area_id=?"
            params.append(area_id)
        sql += " ORDER BY ar.risk_level DESC, ar.created_at DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_handling_record(self, anomaly_id: int, handler: str, handle_time: str,
                            status: str, measures: str = "", result: str = "",
                            follow_up_date: str = "", notes: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO handling_records 
                   (anomaly_id, handler, handle_time, status, measures, result, follow_up_date, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (anomaly_id, handler, handle_time, status, measures, result, follow_up_date, notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_handling_records(self, anomaly_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT hr.*, ar.anomaly_type, ar.risk_level,
                 dp.code as drip_point_code, dp.name as drip_point_name
                 FROM handling_records hr
                 JOIN anomaly_records ar ON hr.anomaly_id = ar.id
                 JOIN drip_points dp ON ar.drip_point_id = dp.id"""
        params = []
        if anomaly_id is not None:
            sql += " WHERE hr.anomaly_id=?"
            params.append(anomaly_id)
        sql += " ORDER BY hr.handle_time DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_import_batch(self, drip_point_id: int, file_name: str, total_count: int = 0,
                       success_count: int = 0, error_count: int = 0,
                       quality_score: Optional[float] = None, imported_by: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO data_import_batches 
                   (drip_point_id, file_name, total_count, success_count, 
                   error_count, quality_score, imported_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (drip_point_id, file_name, total_count, success_count,
                 error_count, quality_score, imported_by)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_import_batches(self, drip_point_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT b.*, dp.code as drip_point_code, dp.name as drip_point_name
                 FROM data_import_batches b
                 JOIN drip_points dp ON b.drip_point_id = dp.id"""
        params = []
        if drip_point_id is not None:
            sql += " WHERE b.drip_point_id=?"
            params.append(drip_point_id)
        sql += " ORDER BY b.imported_at DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_qc_record(self, check_type: str, row_num: Optional[int] = None,
                      field_name: str = "", original_value: str = "",
                      issue_description: str = "", severity: str = "warning",
                      batch_id: Optional[int] = None,
                      drip_point_id: Optional[int] = None) -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO quality_control_records 
                   (batch_id, drip_point_id, check_type, row_num,
                    field_name, original_value, issue_description, severity)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (batch_id, drip_point_id, check_type, row_num,
                 field_name, original_value, issue_description, severity)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_qc_records(self, batch_id: Optional[int] = None,
                       drip_point_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT qcr.*, b.file_name, 
                 dp.code as drip_point_code, dp.name as drip_point_name
                 FROM quality_control_records qcr
                 LEFT JOIN data_import_batches b ON qcr.batch_id = b.id
                 LEFT JOIN drip_points dp ON qcr.drip_point_id = dp.id"""
        params = []
        conditions = []
        if batch_id is not None:
            conditions.append("qcr.batch_id=?")
            params.append(batch_id)
        if drip_point_id is not None:
            conditions.append("qcr.drip_point_id=?")
            params.append(drip_point_id)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY qcr.created_at DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def batch_add_monitoring_data_with_qc(self, point_id: int, data_list: List[Dict],
                                           batch_id: Optional[int] = None) -> Tuple[bool, str, int, int]:
        success_count = 0
        error_messages = []
        
        try:
            for idx, data in enumerate(data_list, 1):
                record_time = data.get("record_time", "")
                drip_interval = data.get("drip_interval", 0)
                quality_score = data.get("quality_score")
                
                if drip_interval <= 0:
                    error_messages.append(f"第 {idx} 行: 滴水间隔必须大于 0，当前值: {drip_interval}")
                    continue
                
                try:
                    self.execute(
                        """INSERT OR IGNORE INTO monitoring_data 
                           (drip_point_id, record_time, drip_interval, temperature, 
                            humidity, salinity, quality_score, batch_id)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (point_id, record_time, drip_interval,
                         data.get("temperature"), data.get("humidity"),
                         data.get("salinity"), quality_score, batch_id)
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

    def get_statistics_by_period(self, point_id: int, period: str = "day",
                                 start_time: str = "", end_time: str = "") -> List[Dict]:
        import math
        period_formats = {
            "day": "%Y-%m-%d",
            "week": "%Y-%W",
            "month": "%Y-%m",
        }
        fmt = period_formats.get(period, "%Y-%m-%d")

        sql = f"""SELECT 
                    strftime('{fmt}', record_time) as period,
                    COUNT(*) as data_count,
                    AVG(drip_interval) as avg_interval,
                    MIN(drip_interval) as min_interval,
                    MAX(drip_interval) as max_interval,
                    AVG(temperature) as avg_temperature,
                    AVG(humidity) as avg_humidity,
                    AVG(salinity) as avg_salinity,
                    MIN(record_time) as period_start,
                    MAX(record_time) as period_end
                   FROM monitoring_data 
                   WHERE drip_point_id=?"""
        params = [point_id]

        if start_time:
            sql += " AND record_time >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND record_time <= ?"
            params.append(end_time)

        sql += " GROUP BY period ORDER BY period"
        cursor = self.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]

        for r in results:
            cnt = r.get("data_count", 0)
            if cnt < 2:
                r["std_interval"] = 0.0
                continue
            period_val = r.get("period", "")
            s_sql = f"SELECT drip_interval FROM monitoring_data WHERE drip_point_id=? AND strftime('{fmt}', record_time)=?"
            s_params = [point_id, period_val]
            s_cursor = self.execute(s_sql, s_params)
            vals = [row[0] for row in s_cursor.fetchall() if row[0] is not None]
            if len(vals) < 2:
                r["std_interval"] = 0.0
                continue
            mean_val = sum(vals) / len(vals)
            variance = sum((x - mean_val) ** 2 for x in vals) / len(vals)
            r["std_interval"] = math.sqrt(variance)

        return results

    def get_multi_point_data(self, point_ids: List[int], 
                            start_time: str = "", end_time: str = "") -> Dict[int, List[Dict]]:
        result = {}
        for pid in point_ids:
            result[pid] = self.get_monitoring_data(pid, start_time, end_time)
        return result

    def delete_anomaly_record(self, anomaly_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM handling_records WHERE anomaly_id=?", (anomaly_id,))
            self.execute("DELETE FROM anomaly_records WHERE id=?", (anomaly_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_overall_statistics(self) -> Dict:
        cursor = self.execute(
            """SELECT 
                (SELECT COUNT(*) FROM cave_areas) as area_count,
                (SELECT COUNT(*) FROM cave_zones) as zone_count,
                (SELECT COUNT(*) FROM drip_points) as point_count,
                (SELECT COUNT(*) FROM monitoring_data) as data_count,
                (SELECT COUNT(*) FROM devices) as device_count,
                (SELECT COUNT(*) FROM anomaly_records WHERE status='待处理') as pending_anomalies,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='待处理') as pending_work_orders,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='处理中') as processing_work_orders
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    def _generate_order_no(self) -> str:
        from datetime import datetime
        prefix = datetime.now().strftime("%Y%m%d")
        cursor = self.execute(
            "SELECT COUNT(*) FROM maintenance_work_orders WHERE order_no LIKE ?",
            (f"WO{prefix}%",)
        )
        count = cursor.fetchone()[0]
        return f"WO{prefix}{count + 1:04d}"

    def add_work_order(self, title: str, anomaly_id: Optional[int] = None,
                        drip_point_id: Optional[int] = None, area_id: Optional[int] = None,
                        zone_id: Optional[int] = None, anomaly_type: str = "",
                        risk_level: str = "中", assignee: str = "",
                        status: str = "待处理", priority: str = "普通",
                        plan_inspect_time: str = "", description: str = "",
                        created_by: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            order_no = self._generate_order_no()
            self.execute(
                """INSERT INTO maintenance_work_orders 
                   (order_no, title, anomaly_id, drip_point_id, area_id, zone_id,
                    anomaly_type, risk_level, assignee, status, priority,
                    plan_inspect_time, description, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_no, title, anomaly_id, drip_point_id, area_id, zone_id,
                 anomaly_type, risk_level, assignee, status, priority,
                 plan_inspect_time, description, created_by)
            )
            self.commit()
            return True, "工单创建成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"创建失败: {str(e)}", None

    def update_work_order(self, order_id: int, **kwargs) -> Tuple[bool, str]:
        if not kwargs:
            return False, "没有需要更新的字段"
        try:
            fields = []
            params = []
            for key, value in kwargs.items():
                fields.append(f"{key}=?")
                params.append(value)
            params.append(order_id)
            sql = f"UPDATE maintenance_work_orders SET {', '.join(fields)}, updated_at=datetime('now', 'localtime') WHERE id=?"
            self.execute(sql, tuple(params))
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_work_order(self, order_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM maintenance_work_orders WHERE id=?", (order_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_work_order(self, order_id: int) -> Optional[Dict]:
        cursor = self.execute(
            """SELECT mwo.*, 
                   dp.code as drip_point_code, dp.name as drip_point_name,
                   ca.code as area_code, ca.name as area_name,
                   cz.code as zone_code, cz.name as zone_name,
                   ar.anomaly_type as anomaly_type_name
               FROM maintenance_work_orders mwo
               LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
               LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
               LEFT JOIN cave_zones cz ON mwo.zone_id = cz.id
               LEFT JOIN anomaly_records ar ON mwo.anomaly_id = ar.id
               WHERE mwo.id=?""",
            (order_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_work_orders(self, status: Optional[str] = None,
                        area_id: Optional[int] = None,
                        assignee: Optional[str] = None,
                        risk_level: Optional[str] = None,
                        start_date: str = "", end_date: str = "",
                        drip_point_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT mwo.*, 
                   dp.code as drip_point_code, dp.name as drip_point_name,
                   ca.code as area_code, ca.name as area_name,
                   cz.code as zone_code, cz.name as zone_name
               FROM maintenance_work_orders mwo
               LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
               LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
               LEFT JOIN cave_zones cz ON mwo.zone_id = cz.id
               WHERE 1=1"""
        params = []
        if status:
            sql += " AND mwo.status=?"
            params.append(status)
        if area_id:
            sql += " AND mwo.area_id=?"
            params.append(area_id)
        if assignee:
            sql += " AND mwo.assignee=?"
            params.append(assignee)
        if risk_level:
            sql += " AND mwo.risk_level=?"
            params.append(risk_level)
        if drip_point_id:
            sql += " AND mwo.drip_point_id=?"
            params.append(drip_point_id)
        if start_date:
            sql += " AND date(mwo.created_at) >= date(?)"
            params.append(start_date)
        if end_date:
            sql += " AND date(mwo.created_at) <= date(?)"
            params.append(end_date)
        sql += " ORDER BY mwo.created_at DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_work_order_status(self, order_id: int, status: str,
                                  assignee: str = "") -> Tuple[bool, str]:
        try:
            if status == "处理中":
                self.execute(
                    """UPDATE maintenance_work_orders 
                       SET status=?, assignee=?, actual_arrive_time=datetime('now', 'localtime'),
                           updated_at=datetime('now', 'localtime')
                       WHERE id=?""",
                    (status, assignee, order_id)
                )
            elif status in ("已完成", "已关闭"):
                close_time_expr = "datetime('now', 'localtime')" if status == "已关闭" else "NULL"
                self.execute(
                    f"""UPDATE maintenance_work_orders 
                       SET status=?, assignee=?, 
                           handle_duration=CASE 
                               WHEN actual_arrive_time IS NOT NULL AND actual_arrive_time != '' 
                               THEN CAST((julianday(datetime('now', 'localtime')) - julianday(actual_arrive_time)) * 24 * 60 AS INTEGER)
                               ELSE NULL END,
                           updated_at=datetime('now', 'localtime'),
                           closed_at={close_time_expr}
                       WHERE id=?""",
                    (status, assignee, order_id)
                )
            else:
                self.execute(
                    """UPDATE maintenance_work_orders 
                       SET status=?, assignee=?, updated_at=datetime('now', 'localtime')
                       WHERE id=?""",
                    (status, assignee, order_id)
                )
            self.commit()
            return True, "状态更新成功"
        except Exception as e:
            self.rollback()
            return False, f"状态更新失败: {str(e)}"

    def add_inspection_record(self, work_order_id: int, inspector: str,
                               inspect_time: str, inspection_content: str = "",
                               measures: str = "", result: str = "",
                               recheck_conclusion: str = "",
                               notes: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO inspection_records 
                   (work_order_id, inspector, inspect_time, inspection_content,
                    measures, result, recheck_conclusion, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (work_order_id, inspector, inspect_time, inspection_content,
                 measures, result, recheck_conclusion, notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_inspection_records(self, work_order_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT ir.*, mwo.order_no, mwo.title as order_title
               FROM inspection_records ir
               JOIN maintenance_work_orders mwo ON ir.work_order_id = mwo.id"""
        params = []
        if work_order_id:
            sql += " WHERE ir.work_order_id=?"
            params.append(work_order_id)
        sql += " ORDER BY ir.inspect_time DESC"
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_attachment(self, work_order_id: int, file_name: str,
                         file_path: str, file_size: Optional[int] = None,
                         file_type: str = "", uploaded_by: str = ""
                         ) -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO work_order_attachments 
                   (work_order_id, file_name, file_path, file_size, file_type, uploaded_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (work_order_id, file_name, file_path, file_size, file_type, uploaded_by)
            )
            self.commit()
            return True, "上传成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"上传失败: {str(e)}", None

    def get_attachments(self, work_order_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM work_order_attachments WHERE work_order_id=? ORDER BY uploaded_at DESC",
            (work_order_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_attachment(self, attachment_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM work_order_attachments WHERE id=?", (attachment_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_overdue_orders(self) -> List[Dict]:
        cursor = self.execute(
            """SELECT mwo.*, 
                   dp.code as drip_point_code, dp.name as drip_point_name,
                   ca.code as area_code, ca.name as area_name
               FROM maintenance_work_orders mwo
               LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
               LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
               WHERE mwo.status IN ('待处理', '处理中')
               AND mwo.plan_inspect_time IS NOT NULL
               AND mwo.plan_inspect_time != ''
               AND datetime(mwo.plan_inspect_time) < datetime('now', 'localtime')
               ORDER BY mwo.plan_inspect_time ASC"""
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_work_order_stats(self) -> Dict:
        cursor = self.execute(
            """SELECT 
                (SELECT COUNT(*) FROM maintenance_work_orders) as total,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='待处理') as pending,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='处理中') as processing,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='待复检') as recheck_pending,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='已完成') as completed,
                (SELECT COUNT(*) FROM maintenance_work_orders WHERE status='已关闭') as closed,
                (SELECT COUNT(*) FROM maintenance_work_orders 
                 WHERE status IN ('待处理', '处理中')
                 AND plan_inspect_time IS NOT NULL
                 AND plan_inspect_time != ''
                 AND datetime(plan_inspect_time) < datetime('now', 'localtime')) as overdue
            """
        )
        row = cursor.fetchone()
        return dict(row) if row else {}

    def get_efficiency_stats(self, start_date: str = "", end_date: str = "") -> Dict:
        base_where = "1=1"
        params = []
        if start_date:
            base_where += " AND date(created_at) >= date(?)"
            params.append(start_date)
        if end_date:
            base_where += " AND date(created_at) <= date(?)"
            params.append(end_date)

        cursor = self.execute(
            f"""SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN status IN ('已完成', '已关闭') THEN 1 ELSE 0 END) as total_completed,
                AVG(
                    CASE WHEN handle_duration IS NOT NULL THEN handle_duration ELSE NULL END
                ) as avg_handle_minutes,
                AVG(
                    CASE WHEN actual_arrive_time IS NOT NULL AND actual_arrive_time != ''
                         THEN CAST((julianday(actual_arrive_time) - julianday(created_at)) * 24 * 60 AS INTEGER)
                         ELSE NULL END
                ) as avg_response_minutes,
                SUM(CASE WHEN status IN ('待处理', '处理中')
                    AND plan_inspect_time IS NOT NULL AND plan_inspect_time != ''
                    AND datetime(plan_inspect_time) < datetime('now', 'localtime') THEN 1 ELSE 0 END
                ) as overdue_count,
                SUM(CASE WHEN actual_arrive_time IS NOT NULL AND actual_arrive_time != ''
                    AND plan_inspect_time IS NOT NULL AND plan_inspect_time != ''
                    AND datetime(actual_arrive_time) <= datetime(plan_inspect_time) THEN 1 ELSE 0 END
                ) as on_time_count,
                SUM(CASE WHEN actual_arrive_time IS NOT NULL AND actual_arrive_time != ''
                    AND plan_inspect_time IS NOT NULL AND plan_inspect_time != '' THEN 1 ELSE 0 END
                ) as arrived_with_plan_count
             FROM maintenance_work_orders WHERE {base_where}""",
            tuple(params)
        )
        row = cursor.fetchone()
        result = dict(row) if row else {}
        return result

    def get_repeat_anomaly_points(self, start_date: str = "",
                                   end_date: str = "",
                                   min_count: int = 2) -> List[Dict]:
        sql = """SELECT 
                    mwo.drip_point_id,
                    dp.code as drip_point_code,
                    dp.name as drip_point_name,
                    ca.code as area_code,
                    ca.name as area_name,
                    COUNT(*) as order_count,
                    GROUP_CONCAT(DISTINCT mwo.anomaly_type) as anomaly_types
                 FROM maintenance_work_orders mwo
                 LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
                 LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
                 WHERE mwo.drip_point_id IS NOT NULL"""
        params = []
        if start_date:
            sql += " AND date(mwo.created_at) >= date(?)"
            params.append(start_date)
        if end_date:
            sql += " AND date(mwo.created_at) <= date(?)"
            params.append(end_date)
        sql += """
                 GROUP BY mwo.drip_point_id
                 HAVING order_count >= ?
                 ORDER BY order_count DESC"""
        params.append(min_count)
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_maintenance_history(self, drip_point_id: int) -> List[Dict]:
        cursor = self.execute(
            """SELECT mwo.*, 
                   dp.code as drip_point_code, dp.name as drip_point_name
               FROM maintenance_work_orders mwo
               LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
               WHERE mwo.drip_point_id=?
               ORDER BY mwo.created_at DESC""",
            (drip_point_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def create_work_order_from_anomaly(self, anomaly_id: int,
                                        assignee: str = "",
                                        plan_inspect_time: str = "",
                                        created_by: str = "") -> Tuple[bool, str, Optional[int]]:
        cursor = self.execute(
            "SELECT id FROM maintenance_work_orders WHERE anomaly_id=?",
            (anomaly_id,)
        )
        if cursor.fetchone():
            return False, "该异常已有对应工单", None
        anomaly = None
        records = self.get_anomaly_records()
        for r in records:
            if r["id"] == anomaly_id:
                anomaly = r
                break
        if not anomaly:
            return False, "异常记录不存在", None
        title = f"[{anomaly.get('anomaly_type', '异常')}] {anomaly.get('drip_point_code', '')} 巡检工单"
        point = self.get_drip_point(anomaly["drip_point_id"]) if anomaly.get("drip_point_id") else None
        return self.add_work_order(
            title=title,
            anomaly_id=anomaly_id,
            drip_point_id=anomaly["drip_point_id"],
            area_id=point.get("area_id") if point else None,
            zone_id=point.get("zone_id") if point else None,
            anomaly_type=anomaly.get("anomaly_type", ""),
            risk_level=anomaly.get("risk_level", "中"),
            assignee=assignee,
            status="待处理",
            plan_inspect_time=plan_inspect_time,
            description=anomaly.get("description", ""),
            created_by=created_by
        )

    def batch_create_work_orders_from_anomalies(self, anomaly_ids: List[int],
                                                  assignee: str = "",
                                                  created_by: str = "") -> Tuple[int, int, List[str]]:
        created = 0
        skipped = 0
        messages = []
        for aid in anomaly_ids:
            from datetime import datetime, timedelta
            plan_time = (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            success, msg, _ = self.create_work_order_from_anomaly(
                anomaly_id=aid,
                assignee=assignee,
                plan_inspect_time=plan_time,
                created_by=created_by
            )
            if success:
                created += 1
            else:
                skipped += 1
                messages.append(msg)
        return created, skipped, messages


    def add_user(self, username: str, real_name: str, password: str,
                 role: str, phone: str = "", email: str = "",
                 department: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO users (username, real_name, password, role, phone, email, department)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (username, real_name, password, role, phone, email, department)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "用户名已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_user(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        if not kwargs:
            return False, "没有需要更新的字段"
        try:
            fields = []
            params = []
            for key, value in kwargs.items():
                fields.append(f"{key}=?")
                params.append(value)
            params.append(user_id)
            sql = f"UPDATE users SET {', '.join(fields)} WHERE id=?"
            self.execute(sql, tuple(params))
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM users WHERE id=?", (user_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_user(self, user_id: int) -> Optional[Dict]:
        cursor = self.execute("SELECT * FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        cursor = self.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_users(self, role: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        sql = "SELECT * FROM users WHERE 1=1"
        params = []
        if role:
            sql += " AND role=?"
            params.append(role)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY username"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def verify_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        user = self.get_user_by_username(username)
        if not user:
            return False, None, "用户不存在"
        if user.get("status") != "active":
            return False, None, "用户已被禁用"
        if user.get("password") == password:
            self.execute(
                "UPDATE users SET last_login=datetime('now', 'localtime') WHERE id=?",
                (user["id"],)
            )
            self.commit()
            return True, user, "登录成功"
        return False, None, "密码错误"

    def add_user_permission(self, user_id: int, permission: str) -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                "INSERT INTO user_permissions (user_id, permission) VALUES (?, ?)",
                (user_id, permission)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "权限已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_user_permissions(self, user_id: int) -> List[str]:
        cursor = self.execute(
            "SELECT permission FROM user_permissions WHERE user_id=?",
            (user_id,)
        )
        return [row["permission"] for row in cursor.fetchall()]

    def delete_user_permission(self, user_id: int, permission: str) -> Tuple[bool, str]:
        try:
            self.execute(
                "DELETE FROM user_permissions WHERE user_id=? AND permission=?",
                (user_id, permission)
            )
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def add_approval_record(self, work_order_id: int, approval_step: int = 1,
                            approver_id: Optional[int] = None, approver_name: str = "",
                            approval_status: str = "pending",
                            approval_opinion: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO approval_records 
                   (work_order_id, approver_id, approver_name, approval_step, 
                    approval_status, approval_opinion)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (work_order_id, approver_id, approver_name, approval_step,
                 approval_status, approval_opinion)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_approval_record(self, record_id: int, approval_status: str,
                               approval_opinion: str = "",
                               approver_name: str = "") -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE approval_records 
                   SET approval_status=?, approval_opinion=?, approver_name=?,
                       approval_time=datetime('now', 'localtime')
                   WHERE id=?""",
                (approval_status, approval_opinion, approver_name, record_id)
            )
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def get_approval_records(self, work_order_id: Optional[int] = None,
                              approval_status: Optional[str] = None) -> List[Dict]:
        sql = """SELECT ar.*, mwo.order_no, mwo.title as order_title,
                        mwo.assignee, mwo.risk_level
                 FROM approval_records ar
                 JOIN maintenance_work_orders mwo ON ar.work_order_id = mwo.id
                 WHERE 1=1"""
        params = []
        if work_order_id:
            sql += " AND ar.work_order_id=?"
            params.append(work_order_id)
        if approval_status:
            sql += " AND ar.approval_status=?"
            params.append(approval_status)
        sql += " ORDER BY ar.created_at DESC"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def get_pending_approvals(self, approver_role: Optional[str] = None) -> List[Dict]:
        sql = """SELECT ar.*, mwo.order_no, mwo.title as order_title,
                        mwo.assignee, mwo.risk_level, mwo.anomaly_type,
                        dp.code as drip_point_code, dp.name as drip_point_name
                 FROM approval_records ar
                 JOIN maintenance_work_orders mwo ON ar.work_order_id = mwo.id
                 LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
                 WHERE ar.approval_status='pending'"""
        params = []
        sql += " ORDER BY ar.created_at DESC"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def add_inspection_route(self, route_name: str, route_code: str,
                              area_id: Optional[int] = None, description: str = "",
                              created_by: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO inspection_routes 
                   (route_name, route_code, area_id, description, created_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (route_name, route_code, area_id, description, created_by)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "路线编号已存在", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_inspection_route(self, route_id: int, **kwargs) -> Tuple[bool, str]:
        if not kwargs:
            return False, "没有需要更新的字段"
        try:
            fields = []
            params = []
            for key, value in kwargs.items():
                fields.append(f"{key}=?")
                params.append(value)
            params.append(route_id)
            sql = f"UPDATE inspection_routes SET {', '.join(fields)}, updated_at=datetime('now', 'localtime') WHERE id=?"
            self.execute(sql, tuple(params))
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def delete_inspection_route(self, route_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM inspection_routes WHERE id=?", (route_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def get_inspection_route(self, route_id: int) -> Optional[Dict]:
        cursor = self.execute(
            """SELECT ir.*, ca.code as area_code, ca.name as area_name
               FROM inspection_routes ir
               LEFT JOIN cave_areas ca ON ir.area_id = ca.id
               WHERE ir.id=?""",
            (route_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_inspection_routes(self, area_id: Optional[int] = None) -> List[Dict]:
        sql = """SELECT ir.*, ca.code as area_code, ca.name as area_name
                 FROM inspection_routes ir
                 LEFT JOIN cave_areas ca ON ir.area_id = ca.id
                 WHERE 1=1"""
        params = []
        if area_id:
            sql += " AND ir.area_id=?"
            params.append(area_id)
        sql += " ORDER BY ir.route_code"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def add_route_point(self, route_id: int, drip_point_id: int,
                        sequence: int = 0, estimated_duration: Optional[int] = None,
                        notes: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO route_points 
                   (route_id, drip_point_id, sequence, estimated_duration, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (route_id, drip_point_id, sequence, estimated_duration, notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except sqlite3.IntegrityError:
            self.rollback()
            return False, "该点位已在路线中", None
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_route_points(self, route_id: int) -> List[Dict]:
        cursor = self.execute(
            """SELECT rp.*, dp.code as drip_point_code, dp.name as drip_point_name,
                        dp.location, dp.elevation
               FROM route_points rp
               JOIN drip_points dp ON rp.drip_point_id = dp.id
               WHERE rp.route_id=?
               ORDER BY rp.sequence, rp.id""",
            (route_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_route_point(self, route_point_id: int) -> Tuple[bool, str]:
        try:
            self.execute("DELETE FROM route_points WHERE id=?", (route_point_id,))
            self.commit()
            return True, "删除成功"
        except Exception as e:
            self.rollback()
            return False, f"删除失败: {str(e)}"

    def update_route_point_sequence(self, route_point_id: int, sequence: int) -> Tuple[bool, str]:
        try:
            self.execute(
                "UPDATE route_points SET sequence=? WHERE id=?",
                (sequence, route_point_id)
            )
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def add_route_assignment(self, route_id: int, assignee: str,
                              plan_date: str, notes: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            points = self.get_route_points(route_id)
            self.execute(
                """INSERT INTO route_assignments 
                   (route_id, assignee, plan_date, total_count, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (route_id, assignee, plan_date, len(points), notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def update_route_assignment(self, assignment_id: int, **kwargs) -> Tuple[bool, str]:
        if not kwargs:
            return False, "没有需要更新的字段"
        try:
            fields = []
            params = []
            for key, value in kwargs.items():
                fields.append(f"{key}=?")
                params.append(value)
            params.append(assignment_id)
            sql = f"UPDATE route_assignments SET {', '.join(fields)} WHERE id=?"
            self.execute(sql, tuple(params))
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def get_route_assignments(self, assignee: Optional[str] = None,
                              plan_date: Optional[str] = None,
                              status: Optional[str] = None) -> List[Dict]:
        sql = """SELECT ra.*, ir.route_name, ir.route_code, ir.description
                 FROM route_assignments ra
                 JOIN inspection_routes ir ON ra.route_id = ir.id
                 WHERE 1=1"""
        params = []
        if assignee:
            sql += " AND ra.assignee=?"
            params.append(assignee)
        if plan_date:
            sql += " AND ra.plan_date=?"
            params.append(plan_date)
        if status:
            sql += " AND ra.status=?"
            params.append(status)
        sql += " ORDER BY ra.plan_date DESC, ra.id DESC"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def add_reminder(self, work_order_id: int, reminder_type: str,
                     recipient: str = "", content: str = "",
                     due_date: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO reminder_records 
                   (work_order_id, reminder_type, reminder_content, recipient, reminder_time)
                   VALUES (?, ?, ?, ?, datetime('now', 'localtime'))""",
                (work_order_id, reminder_type, content or due_date, recipient)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_reminders(self, work_order_id: Optional[int] = None,
                      is_read: Optional[int] = None,
                      recipient: Optional[str] = None) -> List[Dict]:
        sql = """SELECT r.*, mwo.order_no, mwo.title as order_title,
                        mwo.assignee, mwo.status as order_status
                 FROM reminder_records r
                 JOIN maintenance_work_orders mwo ON r.work_order_id = mwo.id
                 WHERE 1=1"""
        params = []
        if work_order_id:
            sql += " AND r.work_order_id=?"
            params.append(work_order_id)
        if is_read is not None:
            sql += " AND r.is_read=?"
            params.append(is_read)
        if recipient:
            sql += " AND r.recipient=?"
            params.append(recipient)
        sql += " ORDER BY r.reminder_time DESC"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def mark_reminder_read(self, reminder_id: int) -> Tuple[bool, str]:
        try:
            self.execute(
                "UPDATE reminder_records SET is_read=1 WHERE id=?",
                (reminder_id,)
            )
            self.commit()
            return True, "标记成功"
        except Exception as e:
            self.rollback()
            return False, f"标记失败: {str(e)}"

    def add_escalation(self, work_order_id: int, escalation_level: int,
                       escalation_reason: str = "", escalated_to: str = "",
                       escalated_by: str = "") -> Tuple[bool, str, Optional[int]]:
        try:
            self.execute(
                """INSERT INTO work_order_escalations 
                   (work_order_id, escalation_level, escalation_reason,
                    escalated_to, escalated_by, escalation_time)
                   VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
                (work_order_id, escalation_level, escalation_reason,
                 escalated_to, escalated_by)
            )
            self.commit()
            return True, "升级成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"升级失败: {str(e)}", None

    def update_escalation_response(self, escalation_id: int,
                                    response: str) -> Tuple[bool, str]:
        try:
            self.execute(
                """UPDATE work_order_escalations 
                   SET response=?, response_time=datetime('now', 'localtime')
                   WHERE id=?""",
                (response, escalation_id)
            )
            self.commit()
            return True, "更新成功"
        except Exception as e:
            self.rollback()
            return False, f"更新失败: {str(e)}"

    def get_escalations(self, work_order_id: Optional[int] = None,
                         escalation_level: Optional[int] = None) -> List[Dict]:
        sql = """SELECT e.*, mwo.order_no, mwo.title as order_title,
                        mwo.assignee, mwo.status as order_status
                 FROM work_order_escalations e
                 JOIN maintenance_work_orders mwo ON e.work_order_id = mwo.id
                 WHERE 1=1"""
        params = []
        if work_order_id:
            sql += " AND e.work_order_id=?"
            params.append(work_order_id)
        if escalation_level:
            sql += " AND e.escalation_level=?"
            params.append(escalation_level)
        sql += " ORDER BY e.escalation_time DESC"
        cursor = self.execute(sql, tuple(params))
        return [dict(row) for row in cursor.fetchall()]

    def get_work_order_escalations(self, work_order_id: int) -> List[Dict]:
        return self.get_escalations(work_order_id=work_order_id)

    def add_work_order_history(self, work_order_id: int, action: str,
                               old_value: str = "", new_value: str = "",
                               operator: str = "", remarks: str = "",
                               action_type: str = "", details: str = "",
                               notes: str = "") -> Tuple[bool, str, Optional[int]]:
        final_action = action_type if action_type else action
        final_details = details if details else (new_value if new_value else "")
        final_notes = notes if notes else remarks
        final_details_and_notes = f"{final_details} {final_notes}".strip()
        try:
            self.execute(
                """INSERT INTO work_order_history 
                   (work_order_id, action, old_value, new_value, operator, remarks)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (work_order_id, final_action, old_value, new_value, 
                 operator, final_details_and_notes)
            )
            self.commit()
            return True, "添加成功", self._cursor.lastrowid
        except Exception as e:
            self.rollback()
            return False, f"添加失败: {str(e)}", None

    def get_work_order_history(self, work_order_id: int) -> List[Dict]:
        cursor = self.execute(
            "SELECT * FROM work_order_history WHERE work_order_id=? ORDER BY operation_time DESC",
            (work_order_id,)
        )
        raw = [dict(row) for row in cursor.fetchall()]
        for item in raw:
            item["action_type"] = item.get("action", "")
            item["details"] = item.get("remarks", "")
        return raw

    def batch_assign_work_orders(self, work_order_ids: List[int], assignee: str,
                                  plan_inspect_time: str = "", priority: str = "",
                                  notes: str = "", operator: str = ""
                                  ) -> Tuple[bool, str, int]:
        updated = 0
        skipped = 0
        messages = []
        update_data = {"assignee": assignee, "status": "待处理"}
        if plan_inspect_time:
            update_data["plan_inspect_time"] = plan_inspect_time
        if priority:
            update_data["priority"] = priority
        for oid in work_order_ids:
            success, msg = self.update_work_order(oid, **update_data)
            if success:
                self.add_work_order_history(
                    oid, action="batch_assign", old_value="", new_value=assignee,
                    operator=operator if operator else assignee, remarks=f"批量派单给 {assignee}{f'，备注：{notes}' if notes else ''}"
                )
                updated += 1
            else:
                skipped += 1
                messages.append(f"工单 {oid}: {msg}")
        return True, "批量派单完成" + (f"（跳过 {skipped} 个：" + "; ".join(messages) + "）" if skipped else ""), updated

    def get_recheck_reminders(self) -> List[Dict]:
        cursor = self.execute(
            """SELECT mwo.*, 
                       dp.code as drip_point_code, dp.name as drip_point_name,
                       ca.code as area_code, ca.name as area_name
               FROM maintenance_work_orders mwo
               LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
               LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
               WHERE mwo.status='待复检'
               AND datetime(mwo.updated_at, '+7 days') < datetime('now', 'localtime')
               ORDER BY mwo.updated_at ASC"""
        )
        return [dict(row) for row in cursor.fetchall()]

    def auto_escalate_overdue(self) -> Tuple[int, List[str]]:
        escalated = 0
        messages = []
        overdue_orders = self.get_overdue_orders()
        for order in overdue_orders:
            order_id = order["id"]
            escalations = self.get_escalations(work_order_id=order_id)
            current_level = max([e["escalation_level"] for e in escalations], default=0)
            
            plan_dt_str = order.get("plan_inspect_time", "")
            if not plan_dt_str:
                continue
                
            try:
                from datetime import datetime
                plan_dt = datetime.strptime(plan_dt_str, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                days_overdue = (now - plan_dt).days
                
                if days_overdue >= 3 and current_level < 1:
                    self.add_escalation(
                        order_id, 1,
                        f"工单已超期 {days_overdue} 天未处理",
                        "", "系统自动升级"
                    )
                    escalated += 1
                    messages.append(f"工单 {order['order_no']} 已自动升级到 Level 1")
                elif days_overdue >= 7 and current_level < 2:
                    self.add_escalation(
                        order_id, 2,
                        f"工单已超期 {days_overdue} 天未处理",
                        "", "系统自动升级"
                    )
                    escalated += 1
                    messages.append(f"工单 {order['order_no']} 已自动升级到 Level 2")
                elif days_overdue >= 14 and current_level < 3:
                    self.add_escalation(
                        order_id, 3,
                        f"工单已超期 {days_overdue} 天未处理",
                        "", "系统自动升级"
                    )
                    escalated += 1
                    messages.append(f"工单 {order['order_no']} 已自动升级到 Level 3")
            except Exception:
                continue
        return escalated, messages

    def auto_send_overdue_reminders(self) -> Tuple[int, List[str]]:
        reminded = 0
        messages = []
        overdue_orders = self.get_overdue_orders()
        for order in overdue_orders:
            order_id = order["id"]
            assignee = order.get("assignee", "")
            order_no = order.get("order_no", "")
            
            recent_reminders = self.get_reminders(
                work_order_id=order_id,
                reminder_type="overdue"
            )
            
            if len(recent_reminders) < 3:
                self.add_reminder(
                    order_id, "overdue",
                    f"工单 [{order_no}] 已超期，请尽快处理",
                    assignee
                )
                reminded += 1
                messages.append(f"已为工单 {order_no} 发送超期提醒")
        return reminded, messages

    def get_advanced_statistics(self, start_date: str = "", end_date: str = "",
                                 area_id: Optional[int] = None,
                                 assignee: Optional[str] = None,
                                 anomaly_type: Optional[str] = None,
                                 drip_point_id: Optional[int] = None) -> Dict:
        base_where = "1=1"
        params = []
        
        if start_date:
            base_where += " AND date(mwo.created_at) >= date(?)"
            params.append(start_date)
        if end_date:
            base_where += " AND date(mwo.created_at) <= date(?)"
            params.append(end_date)
        if area_id:
            base_where += " AND mwo.area_id=?"
            params.append(area_id)
        if assignee:
            base_where += " AND mwo.assignee=?"
            params.append(assignee)
        if anomaly_type:
            base_where += " AND mwo.anomaly_type=?"
            params.append(anomaly_type)
        if drip_point_id:
            base_where += " AND mwo.drip_point_id=?"
            params.append(drip_point_id)

        result: Dict = {}

        summary_sql = f"""
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN mwo.status IN ('已完成', '已关闭') THEN 1 ELSE 0 END) as closed_count,
                SUM(CASE WHEN mwo.status IN ('待处理', '处理中', '待复检') THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN mwo.status IN ('待处理', '处理中')
                    AND mwo.plan_inspect_time IS NOT NULL AND mwo.plan_inspect_time != ''
                    AND datetime(mwo.plan_inspect_time) < datetime('now', 'localtime') THEN 1 ELSE 0 END
                ) as overdue_count,
                AVG(CASE WHEN mwo.handle_duration IS NOT NULL THEN mwo.handle_duration / 60.0 ELSE NULL END) as avg_duration_hours
             FROM maintenance_work_orders mwo WHERE {base_where}
        """
        cur = self.execute(summary_sql, tuple(params))
        row = cur.fetchone()
        s = dict(row) if row else {}
        result["summary"] = {
            "total_count": s.get("total_count") or 0,
            "closed_count": s.get("closed_count") or 0,
            "pending_count": s.get("pending_count") or 0,
            "overdue_count": s.get("overdue_count") or 0,
            "avg_duration_hours": round(float(s.get("avg_duration_hours") or 0), 2),
        }

        repeat_sql = f"""
            SELECT COUNT(DISTINCT mwo.drip_point_id) as repeated_point_count
            FROM maintenance_work_orders mwo
            WHERE {base_where} AND mwo.drip_point_id IS NOT NULL
            GROUP BY mwo.drip_point_id HAVING COUNT(*) >= 3
        """
        try:
            cur2 = self.execute(repeat_sql, tuple(params))
            repeated_rows = cur2.fetchall()
            result["summary"]["repeated_point_count"] = len(repeated_rows)
        except Exception:
            result["summary"]["repeated_point_count"] = 0

        status_sql = f"""
            SELECT mwo.status, COUNT(*) as cnt
            FROM maintenance_work_orders mwo
            WHERE {base_where}
            GROUP BY mwo.status
        """
        by_status = {}
        for r in self.execute(status_sql, tuple(params)).fetchall():
            by_status[r["status"]] = r["cnt"]
        result["by_status"] = by_status

        trend_sql = f"""
            SELECT date(mwo.created_at) as date, COUNT(*) as count
            FROM maintenance_work_orders mwo
            WHERE {base_where}
            GROUP BY date(mwo.created_at)
            ORDER BY date(mwo.created_at)
            LIMIT 90
        """
        trend = []
        for r in self.execute(trend_sql, tuple(params)).fetchall():
            trend.append({"date": r["date"], "count": r["count"]})
        result["trend"] = trend

        assignee_agg_sql = f"""
            SELECT mwo.assignee,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN mwo.status IN ('已完成', '已关闭') THEN 1 ELSE 0 END) as completed_count,
                   AVG(CASE WHEN mwo.handle_duration IS NOT NULL THEN mwo.handle_duration / 60.0 ELSE NULL END) as avg_duration,
                   SUM(CASE WHEN mwo.actual_arrive_time IS NOT NULL AND mwo.actual_arrive_time != ''
                        AND mwo.plan_inspect_time IS NOT NULL AND mwo.plan_inspect_time != ''
                        AND datetime(mwo.actual_arrive_time) <= datetime(mwo.plan_inspect_time) THEN 1 ELSE 0 END
                   ) as on_time_count
            FROM maintenance_work_orders mwo
            WHERE {base_where} AND mwo.assignee IS NOT NULL AND mwo.assignee != ''
            GROUP BY mwo.assignee
            ORDER BY completed_count DESC
        """
        assignee_list = []
        for r in self.execute(assignee_agg_sql, tuple(params)).fetchall():
            assignee_list.append({
                "assignee": r["assignee"],
                "total_count": r["total_count"],
                "completed_count": r["completed_count"],
                "avg_duration": round(float(r["avg_duration"] or 0), 2),
                "on_time_count": r["on_time_count"] or 0,
            })
        result["by_assignee"] = assignee_list

        repeat_detail_sql = f"""
            SELECT mwo.drip_point_id,
                   dp.code as code,
                   dp.name as name,
                   COUNT(*) as count,
                   MAX(mwo.created_at) as last_time,
                   ca.code as area_code,
                   ca.name as area_name,
                   (SELECT mwo2.anomaly_type FROM maintenance_work_orders mwo2
                    WHERE mwo2.drip_point_id = mwo.drip_point_id
                    GROUP BY mwo2.anomaly_type ORDER BY COUNT(*) DESC LIMIT 1) as top_anomaly_type
            FROM maintenance_work_orders mwo
            LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
            LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
            WHERE {base_where} AND mwo.drip_point_id IS NOT NULL
            GROUP BY mwo.drip_point_id
            HAVING count >= 2
            ORDER BY count DESC
        """
        repeated_points = []
        for r in self.execute(repeat_detail_sql, tuple(params)).fetchall():
            repeated_points.append({
                "drip_point_id": r["drip_point_id"],
                "code": r["code"],
                "name": r["name"],
                "count": r["count"],
                "last_time": r["last_time"],
                "area_code": r["area_code"],
                "area_name": r["area_name"],
                "top_anomaly_type": r["top_anomaly_type"],
            })
        result["repeated_points"] = repeated_points

        area_sql = f"""
            SELECT ca.code, ca.name, COUNT(*) as count
            FROM maintenance_work_orders mwo
            LEFT JOIN cave_areas ca ON mwo.area_id = ca.id
            WHERE {base_where} AND mwo.area_id IS NOT NULL
            GROUP BY mwo.area_id
            ORDER BY count DESC
        """
        areas = []
        for r in self.execute(area_sql, tuple(params)).fetchall():
            areas.append({
                "code": r["code"],
                "name": r["name"],
                "count": r["count"],
            })
        result["by_area"] = areas

        history_sql = f"""
            SELECT mwo.order_no as work_order_code,
                   mwo.anomaly_type,
                   dp.code as drip_point_code,
                   dp.name as drip_point_name,
                   mwo.assignee,
                   mwo.created_at,
                   mwo.closed_at,
                   mwo.status,
                   CASE WHEN mwo.handle_duration IS NOT NULL THEN mwo.handle_duration / 60.0 ELSE NULL END as duration_hours
            FROM maintenance_work_orders mwo
            LEFT JOIN drip_points dp ON mwo.drip_point_id = dp.id
            WHERE {base_where}
            ORDER BY mwo.created_at DESC
            LIMIT 500
        """
        history = []
        for r in self.execute(history_sql, tuple(params)).fetchall():
            history.append({
                "work_order_code": r["work_order_code"],
                "anomaly_type": r["anomaly_type"],
                "drip_point_code": r["drip_point_code"],
                "drip_point_name": r["drip_point_name"],
                "assignee": r["assignee"],
                "created_at": r["created_at"],
                "closed_at": r["closed_at"],
                "status": r["status"],
                "duration_hours": round(float(r["duration_hours"] or 0), 2) if r["duration_hours"] is not None else -1,
            })
        result["history"] = history

        anomaly_agg_sql = f"""
            SELECT mwo.anomaly_type,
                   COUNT(*) as total_count,
                   SUM(CASE WHEN mwo.status IN ('已完成', '已关闭') THEN 1 ELSE 0 END) as closed_count,
                   SUM(CASE WHEN mwo.status IN ('待处理', '处理中', '待复检') THEN 1 ELSE 0 END) as pending_count,
                   SUM(CASE WHEN mwo.status IN ('待处理', '处理中')
                        AND mwo.plan_inspect_time IS NOT NULL AND mwo.plan_inspect_time != ''
                        AND datetime(mwo.plan_inspect_time) < datetime('now', 'localtime') THEN 1 ELSE 0 END
                   ) as overdue_count
            FROM maintenance_work_orders mwo
            WHERE {base_where}
            GROUP BY mwo.anomaly_type
            ORDER BY total_count DESC
        """
        anomaly_types = []
        for r in self.execute(anomaly_agg_sql, tuple(params)).fetchall():
            anomaly_types.append({
                "anomaly_type": r["anomaly_type"] or "未分类",
                "total_count": r["total_count"],
                "closed_count": r["closed_count"] or 0,
                "pending_count": r["pending_count"] or 0,
                "overdue_count": r["overdue_count"] or 0,
            })
        result["by_anomaly_type"] = anomaly_types

        return result

    def check_and_init_default_users(self):
        users = self.get_all_users()
        if not users:
            default_users = [
                ("admin", "系统管理员", "admin123", "manager", "", "admin@example.com", "技术部"),
                ("manager1", "张经理", "123456", "manager", "13800138001", "zhang@example.com", "运维部"),
                ("researcher1", "李研究员", "123456", "researcher", "13800138002", "li@example.com", "研究部"),
                ("researcher2", "王研究员", "123456", "researcher", "13800138003", "wang@example.com", "研究部"),
                ("inspector1", "赵巡检", "123456", "inspector", "13800138004", "zhao@example.com", "巡检组"),
                ("inspector2", "钱巡检", "123456", "inspector", "13800138005", "qian@example.com", "巡检组"),
            ]
            for u in default_users:
                self.add_user(*u)


def get_db() -> DatabaseManager:
    db = DatabaseManager()
    db.connect()
    db.check_and_init_default_users()
    return db
