import csv
import os
from datetime import datetime
from typing import List, Dict, Tuple, Optional
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
