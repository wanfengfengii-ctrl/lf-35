import csv
import os
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import re


TIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
]


class DataImportError(Exception):
    pass


class DataImporter:
    @staticmethod
    def parse_time(time_str: str) -> Optional[str]:
        time_str = time_str.strip()
        if not time_str:
            return None
        
        for fmt in TIME_FORMATS:
            try:
                dt = datetime.strptime(time_str, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        
        match = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?$", time_str)
        if match:
            year, month, day, hour, minute = match.groups()[:5]
            second = match.groups()[5] or "00"
            try:
                dt = datetime(int(year), int(month), int(day), 
                              int(hour), int(minute), int(second))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
        
        return None

    @staticmethod
    def parse_float(value_str: str) -> Optional[float]:
        if value_str is None or value_str.strip() == "":
            return None
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def parse_float_required(value_str: str) -> Tuple[bool, float, str]:
        if value_str is None or value_str.strip() == "":
            return False, 0.0, "值不能为空"
        try:
            value = float(value_str)
            if value <= 0:
                return False, value, "值必须大于 0"
            return True, value, ""
        except (ValueError, TypeError):
            return False, 0.0, "格式错误，无法解析为数字"

    @staticmethod
    def detect_columns(header: List[str]) -> Dict[str, Optional[int]]:
        header_lower = [h.strip().lower() for h in header]
        
        mapping = {
            "record_time": ["time", "datetime", "timestamp", "时间", "记录时间", "日期时间"],
            "drip_interval": ["interval", "drip_interval", "dripinterval", "间隔", "滴水间隔", "滴间隔"],
            "temperature": ["temp", "temperature", "温度", "气温", "水温"],
            "humidity": ["humidity", "hum", "湿度", "相对湿度"],
            "salinity": ["salinity", "salt", "盐度", "含盐量"],
        }
        
        result = {}
        for field, candidates in mapping.items():
            result[field] = None
            for idx, col in enumerate(header_lower):
                for candidate in candidates:
                    if candidate.lower() in col:
                        result[field] = idx
                        break
                if result[field] is not None:
                    break
        
        return result

    @staticmethod
    def validate_csv_file(file_path: str) -> Tuple[bool, str, List[str], List[Dict]]:
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}", [], []
        
        if not file_path.lower().endswith(".csv"):
            return False, "仅支持 CSV 格式文件", [], []
        
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                if header is None:
                    return False, "CSV 文件为空", [], []
                
                header = [h.strip() for h in header]
                columns = DataImporter.detect_columns(header)
                
                if columns["record_time"] is None:
                    return False, "未找到时间列，请确保包含 time/datetime/时间 等列名", [], []
                
                if columns["drip_interval"] is None:
                    return False, "未找到滴水间隔列，请确保包含 interval/drip_interval/滴水间隔 等列名", [], []
                
                preview_data = []
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    preview_data.append({
                        "row_num": i + 2,
                        "record_time": row[columns["record_time"]].strip() if columns["record_time"] is not None and columns["record_time"] < len(row) else "",
                        "drip_interval": row[columns["drip_interval"]].strip() if columns["drip_interval"] is not None and columns["drip_interval"] < len(row) else "",
                        "temperature": row[columns["temperature"]].strip() if columns["temperature"] is not None and columns["temperature"] < len(row) else "",
                        "humidity": row[columns["humidity"]].strip() if columns["humidity"] is not None and columns["humidity"] < len(row) else "",
                        "salinity": row[columns["salinity"]].strip() if columns["salinity"] is not None and columns["salinity"] < len(row) else "",
                    })
                
                return True, "", header, preview_data
                
        except UnicodeDecodeError:
            return False, "文件编码错误，请使用 UTF-8 编码", [], []
        except Exception as e:
            return False, f"读取文件失败: {str(e)}", [], []

    @staticmethod
    def import_csv(file_path: str) -> Tuple[bool, str, List[Dict], List[str]]:
        success, error, header, _ = DataImporter.validate_csv_file(file_path)
        if not success:
            return False, error, [], []
        
        columns = DataImporter.detect_columns(header)
        parsed_data = []
        errors = []
        
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader)
                
                for row_num, row in enumerate(reader, 2):
                    if not any(cell.strip() for cell in row):
                        continue
                    
                    row_errors = []
                    record_time_str = row[columns["record_time"]].strip() if columns["record_time"] < len(row) else ""
                    record_time = DataImporter.parse_time(record_time_str)
                    
                    if not record_time:
                        row_errors.append(f"时间格式错误: {record_time_str}")
                    
                    interval_str = row[columns["drip_interval"]].strip() if columns["drip_interval"] < len(row) else ""
                    interval_ok, drip_interval, interval_err = DataImporter.parse_float_required(interval_str)
                    
                    if not interval_ok:
                        row_errors.append(f"滴水间隔{interval_err}: {interval_str}")
                    
                    temperature = None
                    if columns["temperature"] is not None and columns["temperature"] < len(row):
                        temperature = DataImporter.parse_float(row[columns["temperature"]])
                    
                    humidity = None
                    if columns["humidity"] is not None and columns["humidity"] < len(row):
                        humidity = DataImporter.parse_float(row[columns["humidity"]])
                    
                    salinity = None
                    if columns["salinity"] is not None and columns["salinity"] < len(row):
                        salinity = DataImporter.parse_float(row[columns["salinity"]])
                    
                    if row_errors:
                        errors.append(f"第 {row_num} 行: " + "; ".join(row_errors))
                        continue
                    
                    parsed_data.append({
                        "record_time": record_time,
                        "drip_interval": drip_interval,
                        "temperature": temperature,
                        "humidity": humidity,
                        "salinity": salinity,
                        "row_num": row_num,
                    })
            
            if parsed_data:
                parsed_data.sort(key=lambda x: x["record_time"])
            
            return True, "", parsed_data, errors
            
        except Exception as e:
            return False, f"解析文件失败: {str(e)}", [], errors

    @staticmethod
    def generate_sample_csv(file_path: str, num_rows: int = 100):
        import random
        from datetime import timedelta
        
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        
        with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["时间", "滴水间隔(秒)", "温度(℃)", "湿度(%)", "盐度(‰)"])
            
            for i in range(num_rows):
                record_time = start_time + timedelta(minutes=i * 10)
                base_interval = 30.0 + random.uniform(-5, 5)
                
                if 20 <= i < 30:
                    base_interval = 60.0 + random.uniform(-10, 10)
                elif 50 <= i < 60:
                    base_interval = 15.0 + random.uniform(-3, 3)
                
                writer.writerow([
                    record_time.strftime("%Y-%m-%d %H:%M:%S"),
                    round(base_interval, 2),
                    round(15.0 + random.uniform(-2, 2), 1),
                    round(85.0 + random.uniform(-5, 5), 1),
                    round(32.0 + random.uniform(-1, 1), 1),
                ])


@dataclass
class QualityCheckResult:
    passed: bool
    total_rows: int
    issues: List[Dict]
    error_count: int
    warning_count: int
    info_count: int
    quality_score: float
    suggestions: List[str]


class DataQualityChecker:
    RANGES = {
        "drip_interval": (0.1, 3600.0),
        "temperature": (-20.0, 60.0),
        "humidity": (0.0, 100.0),
        "salinity": (0.0, 100.0),
    }

    def __init__(self):
        self.expected_interval_minutes = 60
        self.issues: List[Dict] = []

    def _add_issue(self, check_type: str, row_num: int, field_name: str,
                   original_value: str, description: str, severity: str = "warning"):
        self.issues.append({
            "check_type": check_type,
            "row_num": row_num,
            "field_name": field_name,
            "original_value": original_value,
            "issue_description": description,
            "severity": severity,
        })

    def check_range(self, data_list: List[Dict]):
        for idx, data in enumerate(data_list):
            row_num = idx + 2
            for field, (min_val, max_val) in self.RANGES.items():
                value = data.get(field)
                if value is not None:
                    if value < min_val or value > max_val:
                        self._add_issue(
                            "range_check", row_num, field, str(value),
                            f"{field}值 {value} 超出合理范围 [{min_val}, {max_val}]",
                            "error" if field == "drip_interval" else "warning"
                        )

    def check_duplicates(self, data_list: List[Dict]):
        time_map: Dict[str, List[int]] = {}
        for idx, data in enumerate(data_list):
            row_num = idx + 2
            record_time = data.get("record_time", "")
            if record_time in time_map:
                time_map[record_time].append(row_num)
            else:
                time_map[record_time] = [row_num]
        
        for record_time, rows in time_map.items():
            if len(rows) > 1:
                self._add_issue(
                    "duplicate_check", rows[0], "record_time", record_time,
                    f"时间戳重复，涉及行号: {', '.join(map(str, rows))}",
                    "warning"
                )

    def check_time_order(self, data_list: List[Dict]):
        for i in range(1, len(data_list)):
            prev_time = data_list[i-1].get("record_time", "")
            curr_time = data_list[i].get("record_time", "")
            if prev_time > curr_time:
                self._add_issue(
                    "time_order_check", i + 2, "record_time", curr_time,
                    f"时间顺序错误，前一行为 {prev_time}",
                    "error"
                )

    def check_time_gaps(self, data_list: List[Dict]):
        expected_gap = self.expected_interval_minutes * 60
        for i in range(1, len(data_list)):
            try:
                t1 = datetime.strptime(data_list[i-1]["record_time"], "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(data_list[i]["record_time"], "%Y-%m-%d %H:%M:%S")
                gap = (t2 - t1).total_seconds()
                
                if gap > expected_gap * 3:
                    self._add_issue(
                        "time_gap_check", i + 2, "record_time", data_list[i]["record_time"],
                        f"数据间隔过大，约 {gap/60:.0f} 分钟，预期约 {self.expected_interval_minutes} 分钟",
                        "warning"
                    )
            except (KeyError, ValueError):
                continue

    def check_outliers_iqr(self, data_list: List[Dict], field: str, threshold: float = 3.0):
        values = [d[field] for d in data_list if d.get(field) is not None]
        if len(values) < 10:
            return
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        if iqr == 0:
            return
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        for idx, data in enumerate(data_list):
            value = data.get(field)
            if value is not None and (value < lower_bound or value > upper_bound):
                self._add_issue(
                    "outlier_check", idx + 2, field, str(value),
                    f"{field}值 {value} 疑似异常（IQR方法，范围 [{lower_bound:.2f}, {upper_bound:.2f}]）",
                    "warning"
                )

    def check_missing_values(self, data_list: List[Dict]):
        required_fields = ["record_time", "drip_interval"]
        for idx, data in enumerate(data_list):
            row_num = idx + 2
            for field in required_fields:
                if data.get(field) is None or data.get(field) == "":
                    self._add_issue(
                        "missing_check", row_num, field, "",
                        f"{field} 缺失必填值",
                        "critical"
                    )

    def run_quality_check(self, data_list: List[Dict]) -> QualityCheckResult:
        self.issues = []
        
        self.check_missing_values(data_list)
        self.check_range(data_list)
        self.check_duplicates(data_list)
        self.check_time_order(data_list)
        self.check_time_gaps(data_list)
        
        if data_list:
            self.check_outliers_iqr(data_list, "drip_interval")
            self.check_outliers_iqr(data_list, "temperature")
            self.check_outliers_iqr(data_list, "humidity")
            self.check_outliers_iqr(data_list, "salinity")
        
        error_count = sum(1 for i in self.issues if i["severity"] in ["error", "critical"])
        warning_count = sum(1 for i in self.issues if i["severity"] == "warning")
        info_count = sum(1 for i in self.issues if i["severity"] == "info")
        
        total_rows = len(data_list)
        max_possible_score = total_rows * 10
        penalty = error_count * 10 + warning_count * 3
        quality_score = max(0, min(100, (max_possible_score - penalty) / max_possible_score * 100))
        
        suggestions = []
        if error_count > 0:
            suggestions.append(f"存在 {error_count} 个严重问题，建议修复后再导入")
        if warning_count > 5:
            suggestions.append("警告较多，建议核查数据质量")
        if quality_score < 60:
            suggestions.append("数据质量较低，建议检查数据源")
        
        passed = error_count == 0 and quality_score >= 60
        
        return QualityCheckResult(
            passed=passed,
            total_rows=total_rows,
            issues=self.issues.copy(),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            quality_score=round(quality_score, 2),
            suggestions=suggestions
        )

    def save_qc_records_to_db(self, db, qc_result: QualityCheckResult,
                              batch_id: Optional[int] = None,
                              drip_point_id: Optional[int] = None):
        for issue in qc_result.issues:
            db.add_qc_record(
                check_type=issue["check_type"],
                row_num=issue["row_num"],
                field_name=issue["field_name"],
                original_value=issue["original_value"],
                issue_description=issue["issue_description"],
                severity=issue["severity"],
                batch_id=batch_id,
                drip_point_id=drip_point_id
            )
