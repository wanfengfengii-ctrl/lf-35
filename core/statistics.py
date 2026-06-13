import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class PeriodStatistics:
    period: str
    period_start: str
    period_end: str
    data_count: int
    avg_interval: float
    min_interval: float
    max_interval: float
    std_interval: float
    cv_interval: float
    avg_temperature: Optional[float]
    avg_humidity: Optional[float]
    avg_salinity: Optional[float]
    anomaly_count: int


@dataclass
class MultiPointComparison:
    point_ids: List[int]
    point_codes: Dict[int, str]
    common_period: Tuple[Optional[str], Optional[str]]
    overall_stats: Dict[int, PeriodStatistics]
    correlation_matrix: Dict[Tuple[int, int], float]
    trends: Dict[int, str]


class StatisticsAnalyzer:
    @staticmethod
    def analyze_period(db, point_id: int, period: str = "day",
                       start_time: str = "", end_time: str = "") -> List[PeriodStatistics]:
        raw_stats = db.get_statistics_by_period(point_id, period, start_time, end_time)
        results = []
        
        for stat in raw_stats:
            avg = stat.get("avg_interval", 0)
            std = stat.get("std_interval", 0)
            cv = (std / avg * 100) if avg > 0 else 0
            
            results.append(PeriodStatistics(
                period=stat.get("period", ""),
                period_start=stat.get("period_start", ""),
                period_end=stat.get("period_end", ""),
                data_count=stat.get("data_count", 0),
                avg_interval=round(avg, 2) if avg else 0,
                min_interval=round(stat.get("min_interval", 0), 2),
                max_interval=round(stat.get("max_interval", 0), 2),
                std_interval=round(std, 2) if std else 0,
                cv_interval=round(cv, 2),
                avg_temperature=round(stat.get("avg_temperature"), 2) if stat.get("avg_temperature") else None,
                avg_humidity=round(stat.get("avg_humidity"), 2) if stat.get("avg_humidity") else None,
                avg_salinity=round(stat.get("avg_salinity"), 2) if stat.get("avg_salinity") else None,
                anomaly_count=0
            ))
        
        return results

    @staticmethod
    def calculate_trend(data: List[Dict], field: str = "drip_interval") -> str:
        if len(data) < 10:
            return "数据不足"
        
        values = [d[field] for d in data if d.get(field) is not None]
        if len(values) < 10:
            return "数据不足"
        
        n = len(values)
        x = np.arange(n)
        y = np.array(values)
        
        slope, _ = np.polyfit(x, y, 1)
        mean_val = np.mean(y)
        change_pct = (slope * n / mean_val * 100) if mean_val > 0 else 0
        
        if abs(change_pct) < 3:
            return "稳定"
        elif change_pct > 20:
            return "显著上升"
        elif change_pct > 5:
            return "上升"
        elif change_pct < -20:
            return "显著下降"
        else:
            return "下降"

    @staticmethod
    def compare_multiple_points(db, point_ids: List[int],
                                start_time: str = "", end_time: str = "") -> MultiPointComparison:
        from core.anomaly_detector import AdvancedAnomalyDetector
        
        point_codes = {}
        overall_stats = {}
        all_data = {}
        trends = {}
        
        for pid in point_ids:
            point = db.get_drip_point(pid)
            if point:
                point_codes[pid] = f"{point['code']} - {point['name']}"
            
            data = db.get_monitoring_data(pid, start_time, end_time)
            all_data[pid] = data
            
            if data:
                intervals = [d["drip_interval"] for d in data]
                overall_stats[pid] = PeriodStatistics(
                    period="综合",
                    period_start=data[0]["record_time"],
                    period_end=data[-1]["record_time"],
                    data_count=len(data),
                    avg_interval=round(float(np.mean(intervals)), 2),
                    min_interval=round(float(np.min(intervals)), 2),
                    max_interval=round(float(np.max(intervals)), 2),
                    std_interval=round(float(np.std(intervals)), 2),
                    cv_interval=round(float(np.std(intervals) / np.mean(intervals) * 100), 2),
                    avg_temperature=round(np.mean([d["temperature"] for d in data if d["temperature"] is not None]), 2) if any(d["temperature"] is not None for d in data) else None,
                    avg_humidity=round(np.mean([d["humidity"] for d in data if d["humidity"] is not None]), 2) if any(d["humidity"] is not None for d in data) else None,
                    avg_salinity=round(np.mean([d["salinity"] for d in data if d["salinity"] is not None]), 2) if any(d["salinity"] is not None for d in data) else None,
                    anomaly_count=0
                )
                trends[pid] = StatisticsAnalyzer.calculate_trend(data)
        
        correlation_matrix = {}
        for i in range(len(point_ids)):
            for j in range(i + 1, len(point_ids)):
                pid1, pid2 = point_ids[i], point_ids[j]
                corr = AdvancedAnomalyDetector.calculate_correlation(
                    all_data[pid1], all_data[pid2]
                )
                correlation_matrix[(pid1, pid2)] = corr
        
        all_starts = [d[0]["record_time"] for d in all_data.values() if d]
        all_ends = [d[-1]["record_time"] for d in all_data.values() if d]
        common_period = (min(all_starts) if all_starts else None, max(all_ends) if all_ends else None)
        
        return MultiPointComparison(
            point_ids=point_ids,
            point_codes=point_codes,
            common_period=common_period,
            overall_stats=overall_stats,
            correlation_matrix=correlation_matrix,
            trends=trends
        )

    @staticmethod
    def get_summary_statistics(db, point_id: int) -> Dict:
        data = db.get_monitoring_data(point_id)
        if not data:
            return {}
        
        intervals = [d["drip_interval"] for d in data]
        
        return {
            "total_records": len(data),
            "date_range": f"{data[0]['record_time']} 至 {data[-1]['record_time']}",
            "interval_mean": round(float(np.mean(intervals)), 2),
            "interval_median": round(float(np.median(intervals)), 2),
            "interval_std": round(float(np.std(intervals)), 2),
            "interval_cv": round(float(np.std(intervals) / np.mean(intervals) * 100), 2),
            "interval_min": round(float(np.min(intervals)), 2),
            "interval_max": round(float(np.max(intervals)), 2),
            "trend": StatisticsAnalyzer.calculate_trend(data),
            "data_quality": StatisticsAnalyzer.assess_data_quality(data)
        }

    @staticmethod
    def assess_data_quality(data: List[Dict]) -> str:
        if not data:
            return "无数据"
        
        expected_interval = 60
        gaps = 0
        for i in range(1, len(data)):
            try:
                t1 = datetime.strptime(data[i-1]["record_time"], "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(data[i]["record_time"], "%Y-%m-%d %H:%M:%S")
                diff = (t2 - t1).total_seconds() / 60
                if diff > expected_interval * 3:
                    gaps += 1
            except (ValueError, KeyError):
                continue
        
        gap_rate = gaps / max(len(data) - 1, 1) * 100
        completeness = 100 - gap_rate
        
        if completeness >= 95:
            return "优秀"
        elif completeness >= 85:
            return "良好"
        elif completeness >= 70:
            return "一般"
        else:
            return "较差"

    @staticmethod
    def calculate_seasonal_index(db, point_id: int) -> Dict[str, Dict]:
        from core.anomaly_detector import SEASONS
        
        data = db.get_monitoring_data(point_id)
        if not data:
            return {}
        
        overall_mean = np.mean([d["drip_interval"] for d in data])
        
        seasonal_index = {}
        for season, months in SEASONS.items():
            season_data = [d for d in data 
                          if int(datetime.strptime(d["record_time"], "%Y-%m-%d %H:%M:%S").month) in months]
            if season_data:
                season_mean = np.mean([d["drip_interval"] for d in season_data])
                seasonal_index[season] = {
                    "count": len(season_data),
                    "mean": round(float(season_mean), 2),
                    "index": round(float(season_mean / overall_mean * 100), 2),
                    "std": round(float(np.std([d["drip_interval"] for d in season_data])), 2)
                }
        
        return seasonal_index
