import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field


SEASONS = {
    "春季": [3, 4, 5],
    "夏季": [6, 7, 8],
    "秋季": [9, 10, 11],
    "冬季": [12, 1, 2],
}


RISK_LEVELS = ["低", "中", "高", "极高"]
ANOMALY_TYPES = {
    "blockage": "疑似堵塞",
    "increased_seepage": "疑似渗流增强",
    "sudden_change": "突变异常",
    "abnormal_fluctuation": "异常波动",
    "data_gap": "数据断档",
}


@dataclass
class AnomalySegment:
    start_idx: int
    end_idx: int
    start_time: str
    end_time: str
    anomaly_type: str
    risk_level: str
    avg_value: float
    baseline_avg: float
    change_percent: float
    description: str = ""


@dataclass
class DetectionResult:
    segments: List[AnomalySegment] = field(default_factory=list)
    baseline_mean: float = 0.0
    baseline_std: float = 0.0
    data_count: int = 0
    gaps: List[Dict] = field(default_factory=list)


class AnomalyDetector:
    def __init__(self, 
                 fluctuation_threshold: float = 2.0,
                 consecutive_count: int = 5,
                 blockage_threshold: float = 1.5,
                 seepage_threshold: float = 0.6,
                 sudden_change_threshold: float = 2.5):
        self.fluctuation_threshold = fluctuation_threshold
        self.consecutive_count = consecutive_count
        self.blockage_threshold = blockage_threshold
        self.seepage_threshold = seepage_threshold
        self.sudden_change_threshold = sudden_change_threshold

    def _calculate_baseline(self, values: np.ndarray) -> Tuple[float, float]:
        if len(values) == 0:
            return 0.0, 0.0
        
        sorted_values = np.sort(values)
        n = len(sorted_values)
        mid_start = int(n * 0.2)
        mid_end = int(n * 0.8)
        if mid_end - mid_start < 5:
            mid_start = 0
            mid_end = n
        
        core_data = sorted_values[mid_start:mid_end]
        
        median = np.median(core_data)
        mad = np.median(np.abs(core_data - median))
        if mad == 0:
            mad = np.std(core_data) * 0.6745
        
        std_estimate = 1.4826 * mad
        
        lower_bound = median - 3.0 * std_estimate
        upper_bound = median + 3.0 * std_estimate
        
        filtered = values[(values >= lower_bound) & (values <= upper_bound)]
        if len(filtered) < 5:
            filtered = core_data
        
        baseline_mean = float(np.mean(filtered))
        baseline_std = float(np.std(filtered))
        
        if baseline_std == 0:
            baseline_std = baseline_mean * 0.05
        
        return baseline_mean, baseline_std

    def _detect_data_gaps(self, data: List[Dict], expected_interval_minutes: int = 60) -> List[Dict]:
        gaps = []
        if len(data) < 2:
            return gaps
        
        for i in range(1, len(data)):
            t1 = datetime.strptime(data[i-1]["record_time"], "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(data[i]["record_time"], "%Y-%m-%d %H:%M:%S")
            diff = (t2 - t1).total_seconds() / 60
            
            if diff > expected_interval_minutes * 3:
                gaps.append({
                    "start_time": data[i-1]["record_time"],
                    "end_time": data[i]["record_time"],
                    "gap_minutes": diff,
                    "start_idx": i - 1,
                    "end_idx": i,
                })
        
        return gaps

    def _determine_risk_level(self, consecutive_count: int, change_percent: float) -> str:
        if consecutive_count >= self.consecutive_count * 3 or abs(change_percent) > 200:
            return "极高"
        elif consecutive_count >= self.consecutive_count * 2 or abs(change_percent) > 100:
            return "高"
        elif consecutive_count >= self.consecutive_count or abs(change_percent) > 50:
            return "中"
        else:
            return "低"

    def detect_anomalies(self, data: List[Dict]) -> DetectionResult:
        result = DetectionResult()
        result.data_count = len(data)
        
        if len(data) < self.consecutive_count * 2:
            return result
        
        intervals = np.array([d["drip_interval"] for d in data], dtype=float)
        times = [d["record_time"] for d in data]
        
        baseline_mean, baseline_std = self._calculate_baseline(intervals)
        result.baseline_mean = baseline_mean
        result.baseline_std = baseline_std
        
        if baseline_std == 0:
            baseline_std = baseline_mean * 0.1
        
        z_scores = np.abs((intervals - baseline_mean) / baseline_std)
        fluctuation_mask = z_scores > self.fluctuation_threshold
        
        result.gaps = self._detect_data_gaps(data)
        for gap in result.gaps:
            segment = AnomalySegment(
                start_idx=gap["start_idx"],
                end_idx=gap["end_idx"],
                start_time=gap["start_time"],
                end_time=gap["end_time"],
                anomaly_type="data_gap",
                risk_level="低",
                avg_value=0,
                baseline_avg=baseline_mean,
                change_percent=0,
                description=f"数据断档约 {gap['gap_minutes']:.0f} 分钟"
            )
            result.segments.append(segment)
        
        current_segment = None
        for i in range(len(intervals)):
            if i == 0:
                continue
            
            prev_interval = intervals[i-1]
            curr_interval = intervals[i]
            
            if fluctuation_mask[i]:
                change_ratio = curr_interval / baseline_mean if baseline_mean > 0 else 1
                change_percent = (change_ratio - 1) * 100
                
                is_sudden_change = abs(curr_interval - prev_interval) / max(prev_interval, 0.001) > self.sudden_change_threshold - 1
                
                anomaly_type = "abnormal_fluctuation"
                if change_ratio >= self.blockage_threshold:
                    anomaly_type = "blockage"
                elif change_ratio <= self.seepage_threshold:
                    anomaly_type = "increased_seepage"
                elif is_sudden_change:
                    anomaly_type = "sudden_change"
                
                if current_segment is None:
                    current_segment = {
                        "start_idx": i,
                        "start_time": times[i],
                        "values": [curr_interval],
                        "anomaly_type": anomaly_type,
                        "consecutive_count": 1,
                    }
                else:
                    current_segment["values"].append(curr_interval)
                    current_segment["consecutive_count"] += 1
                    if anomaly_type in ["blockage", "increased_seepage"]:
                        current_segment["anomaly_type"] = anomaly_type
                    elif anomaly_type == "sudden_change" and current_segment["anomaly_type"] == "abnormal_fluctuation":
                        current_segment["anomaly_type"] = anomaly_type
            else:
                if current_segment is not None:
                    if current_segment["consecutive_count"] >= self.consecutive_count:
                        segment_avg = float(np.mean(current_segment["values"]))
                        change_percent = (segment_avg / baseline_mean - 1) * 100 if baseline_mean > 0 else 0
                        risk_level = self._determine_risk_level(
                            current_segment["consecutive_count"],
                            change_percent
                        )
                        
                        type_name = ANOMALY_TYPES.get(current_segment["anomaly_type"], "异常波动")
                        desc = f"{type_name}：连续 {current_segment['consecutive_count']} 个点"
                        if change_percent > 0:
                            desc += f"，平均升高 {change_percent:.1f}%"
                        else:
                            desc += f"，平均降低 {abs(change_percent):.1f}%"
                        
                        segment = AnomalySegment(
                            start_idx=current_segment["start_idx"],
                            end_idx=i - 1,
                            start_time=current_segment["start_time"],
                            end_time=times[i - 1],
                            anomaly_type=current_segment["anomaly_type"],
                            risk_level=risk_level,
                            avg_value=segment_avg,
                            baseline_avg=baseline_mean,
                            change_percent=change_percent,
                            description=desc
                        )
                        result.segments.append(segment)
                    
                    current_segment = None
        
        if current_segment is not None and current_segment["consecutive_count"] >= self.consecutive_count:
            segment_avg = float(np.mean(current_segment["values"]))
            change_percent = (segment_avg / baseline_mean - 1) * 100 if baseline_mean > 0 else 0
            risk_level = self._determine_risk_level(
                current_segment["consecutive_count"],
                change_percent
            )
            
            type_name = ANOMALY_TYPES.get(current_segment["anomaly_type"], "异常波动")
            desc = f"{type_name}：连续 {current_segment['consecutive_count']} 个点"
            if change_percent > 0:
                desc += f"，平均升高 {change_percent:.1f}%"
            else:
                desc += f"，平均降低 {abs(change_percent):.1f}%"
            
            segment = AnomalySegment(
                start_idx=current_segment["start_idx"],
                end_idx=len(intervals) - 1,
                start_time=current_segment["start_time"],
                end_time=times[-1],
                anomaly_type=current_segment["anomaly_type"],
                risk_level=risk_level,
                avg_value=segment_avg,
                baseline_avg=baseline_mean,
                change_percent=change_percent,
                description=desc
            )
            result.segments.append(segment)
        
        return result

    def save_anomalies_to_db(self, db, point_id: int, 
                             result: DetectionResult) -> Tuple[int, str]:
        if not result.segments:
            return 0, "未检测到异常"
        
        saved_count = 0
        errors = []
        
        for seg in result.segments:
            try:
                db.add_anomaly_record(
                    point_id=point_id,
                    anomaly_type=ANOMALY_TYPES.get(seg.anomaly_type, "异常波动"),
                    risk_level=seg.risk_level,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                    description=seg.description
                )
                saved_count += 1
            except Exception as e:
                errors.append(str(e))
        
        if errors:
            return saved_count, "部分保存失败: " + "; ".join(errors)
        
        return saved_count, f"成功保存 {saved_count} 条异常记录"

    @staticmethod
    def get_season_data(data: List[Dict], season_name: str) -> List[Dict]:
        months = SEASONS.get(season_name, [])
        if not months:
            return []
        
        result = []
        for d in data:
            try:
                dt = datetime.strptime(d["record_time"], "%Y-%m-%d %H:%M:%S")
                if dt.month in months:
                    result.append(d)
            except (ValueError, KeyError):
                continue
        
        return result

    @staticmethod
    def compare_seasons(data: List[Dict]) -> Dict[str, Dict]:
        comparison = {}
        
        for season_name in SEASONS:
            season_data = AnomalyDetector.get_season_data(data, season_name)
            if season_data:
                intervals = [d["drip_interval"] for d in season_data]
                temps = [d["temperature"] for d in season_data if d["temperature"] is not None]
                hums = [d["humidity"] for d in season_data if d["humidity"] is not None]
                sals = [d["salinity"] for d in season_data if d["salinity"] is not None]
                
                comparison[season_name] = {
                    "count": len(season_data),
                    "interval_mean": float(np.mean(intervals)),
                    "interval_std": float(np.std(intervals)),
                    "interval_min": float(np.min(intervals)),
                    "interval_max": float(np.max(intervals)),
                    "temp_mean": float(np.mean(temps)) if temps else None,
                    "hum_mean": float(np.mean(hums)) if hums else None,
                    "sal_mean": float(np.mean(sals)) if sals else None,
                }
        
        return comparison
