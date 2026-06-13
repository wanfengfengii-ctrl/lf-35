import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
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
    "continuous_high": "持续偏高",
    "continuous_low": "持续偏低",
}

DEVICE_STATUSES = ["在用", "停用", "维修中", "待校准"]
HANDLING_STATUSES = ["待处理", "处理中", "已处理", "已忽略"]
QC_SEVERITY = ["info", "warning", "error", "critical"]

ANOMALY_STATUS_COLORS = {
    "待处理": "#d62728",
    "处理中": "#ff7f0e",
    "已处理": "#2ca02c",
    "已忽略": "#7f7f7f",
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


@dataclass
class PointAnalysisResult:
    point_id: int
    point_code: str
    point_name: str
    baseline_mean: float
    baseline_std: float
    data_count: int
    anomaly_count: int
    avg_interval: float
    trend: str


@dataclass
class JointAnalysisResult:
    area_id: Optional[int]
    area_name: str
    point_results: List[PointAnalysisResult]
    correlation_matrix: Dict[Tuple[int, int], float]
    combined_risk_level: str
    anomaly_summary: Dict[str, int]
    recommendations: List[str]


@dataclass
class RiskAssessmentResult:
    overall_risk: str
    risk_score: float
    anomaly_counts: Dict[str, int]
    high_risk_points: List[Dict]
    trend_analysis: str
    recommendations: List[str]


class AdvancedAnomalyDetector(AnomalyDetector):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.continuous_threshold = 10
        self.high_threshold_factor = 1.3
        self.low_threshold_factor = 0.7

    def _detect_continuous_patterns(self, data: List[Dict], 
                                   baseline_mean: float, 
                                   times: List[str]) -> List[AnomalySegment]:
        segments = []
        if len(data) < self.continuous_threshold:
            return segments

        intervals = np.array([d["drip_interval"] for d in data], dtype=float)
        
        high_mask = intervals > baseline_mean * self.high_threshold_factor
        low_mask = intervals < baseline_mean * self.low_threshold_factor
        
        def find_continuous_segments(mask: np.ndarray, anomaly_type: str, 
                                    factor: float) -> List[AnomalySegment]:
            segs = []
            current_start = None
            count = 0
            
            for i, is_match in enumerate(mask):
                if is_match:
                    if current_start is None:
                        current_start = i
                    count += 1
                else:
                    if current_start is not None and count >= self.continuous_threshold:
                        avg_val = float(np.mean(intervals[current_start:i]))
                        change_pct = (avg_val / baseline_mean - 1) * 100 if baseline_mean > 0 else 0
                        risk = self._determine_risk_level(count, change_pct)
                        type_name = ANOMALY_TYPES.get(anomaly_type, anomaly_type)
                        desc = f"{type_name}：连续 {count} 个点，平均{change_pct:+.1f}%"
                        
                        segs.append(AnomalySegment(
                            start_idx=current_start,
                            end_idx=i - 1,
                            start_time=times[current_start],
                            end_time=times[i - 1],
                            anomaly_type=anomaly_type,
                            risk_level=risk,
                            avg_value=avg_val,
                            baseline_avg=baseline_mean,
                            change_percent=change_pct,
                            description=desc
                        ))
                    current_start = None
                    count = 0
            
            if current_start is not None and count >= self.continuous_threshold:
                avg_val = float(np.mean(intervals[current_start:]))
                change_pct = (avg_val / baseline_mean - 1) * 100 if baseline_mean > 0 else 0
                risk = self._determine_risk_level(count, change_pct)
                type_name = ANOMALY_TYPES.get(anomaly_type, anomaly_type)
                desc = f"{type_name}：连续 {count} 个点，平均{change_pct:+.1f}%"
                
                segs.append(AnomalySegment(
                    start_idx=current_start,
                    end_idx=len(intervals) - 1,
                    start_time=times[current_start],
                    end_time=times[-1],
                    anomaly_type=anomaly_type,
                    risk_level=risk,
                    avg_value=avg_val,
                    baseline_avg=baseline_mean,
                    change_percent=change_pct,
                    description=desc
                ))
            
            return segs
        
        segments.extend(find_continuous_segments(high_mask, "continuous_high", self.high_threshold_factor))
        segments.extend(find_continuous_segments(low_mask, "continuous_low", self.low_threshold_factor))
        
        return segments

    def detect_anomalies_v2(self, data: List[Dict]) -> DetectionResult:
        result = super().detect_anomalies(data)
        
        if len(data) >= self.consecutive_count * 2:
            times = [d["record_time"] for d in data]
            continuous_segs = self._detect_continuous_patterns(
                data, result.baseline_mean, times
            )
            result.segments.extend(continuous_segs)
        
        return result

    @staticmethod
    def analyze_point(point_id: int, point_code: str, point_name: str, 
                      data: List[Dict]) -> PointAnalysisResult:
        if not data:
            return PointAnalysisResult(
                point_id=point_id,
                point_code=point_code,
                point_name=point_name,
                baseline_mean=0,
                baseline_std=0,
                data_count=0,
                anomaly_count=0,
                avg_interval=0,
                trend="数据不足"
            )
        
        intervals = [d["drip_interval"] for d in data]
        detector = AdvancedAnomalyDetector()
        det_result = detector.detect_anomalies_v2(data)
        
        if len(intervals) >= 2:
            first_half = np.mean(intervals[:len(intervals)//2])
            second_half = np.mean(intervals[len(intervals)//2:])
            change_pct = (second_half - first_half) / max(first_half, 0.001) * 100
            if abs(change_pct) < 5:
                trend = "稳定"
            elif change_pct > 20:
                trend = "显著上升"
            elif change_pct > 5:
                trend = "上升"
            elif change_pct < -20:
                trend = "显著下降"
            else:
                trend = "下降"
        else:
            trend = "数据不足"
        
        return PointAnalysisResult(
            point_id=point_id,
            point_code=point_code,
            point_name=point_name,
            baseline_mean=det_result.baseline_mean,
            baseline_std=det_result.baseline_std,
            data_count=len(data),
            anomaly_count=len(det_result.segments),
            avg_interval=float(np.mean(intervals)),
            trend=trend
        )

    @staticmethod
    def calculate_correlation(data1: List[Dict], data2: List[Dict]) -> float:
        if len(data1) < 10 or len(data2) < 10:
            return 0.0
        
        time_map1 = {d["record_time"]: d["drip_interval"] for d in data1}
        time_map2 = {d["record_time"]: d["drip_interval"] for d in data2}
        
        common_times = sorted(set(time_map1.keys()) & set(time_map2.keys()))
        if len(common_times) < 10:
            return 0.0
        
        values1 = [time_map1[t] for t in common_times]
        values2 = [time_map2[t] for t in common_times]
        
        try:
            corr = np.corrcoef(values1, values2)[0, 1]
            return float(corr) if not np.isnan(corr) else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def joint_analysis(area_id: Optional[int], area_name: str,
                       points_data: Dict[int, Dict[str, Any]]) -> JointAnalysisResult:
        point_results = []
        all_data = {}
        
        for pid, info in points_data.items():
            data = info.get("data", [])
            result = AdvancedAnomalyDetector.analyze_point(
                pid, info.get("code", ""), info.get("name", ""), data
            )
            point_results.append(result)
            all_data[pid] = data
        
        correlation_matrix = {}
        point_ids = list(all_data.keys())
        for i in range(len(point_ids)):
            for j in range(i + 1, len(point_ids)):
                pid1, pid2 = point_ids[i], point_ids[j]
                corr = AdvancedAnomalyDetector.calculate_correlation(
                    all_data[pid1], all_data[pid2]
                )
                correlation_matrix[(pid1, pid2)] = corr
        
        anomaly_summary = {}
        total_anomalies = 0
        high_risk_count = 0
        
        for pr in point_results:
            total_anomalies += pr.anomaly_count
            if pr.anomaly_count > 5:
                high_risk_count += 1
        
        anomaly_summary["total_points"] = len(point_results)
        anomaly_summary["total_anomalies"] = total_anomalies
        anomaly_summary["high_risk_points"] = high_risk_count
        anomaly_summary["avg_anomalies_per_point"] = total_anomalies / max(len(point_results), 1)
        
        high_correlation_count = sum(1 for c in correlation_matrix.values() if abs(c) > 0.7)
        anomaly_summary["high_correlation_pairs"] = high_correlation_count
        
        if high_risk_count > len(point_results) * 0.5 or total_anomalies > 20:
            combined_risk = "极高"
        elif high_risk_count > 0 or total_anomalies > 10:
            combined_risk = "高"
        elif total_anomalies > 3:
            combined_risk = "中"
        else:
            combined_risk = "低"
        
        recommendations = []
        if combined_risk in ["高", "极高"]:
            recommendations.append("建议尽快安排现场检查，核实异常原因")
        if high_correlation_count > 0:
            recommendations.append("发现多点位高度相关，建议开展区域水文分析")
        if any(pr.trend in ["显著上升", "显著下降"] for pr in point_results):
            recommendations.append("部分点位趋势变化显著，建议加强监测频率")
        
        return JointAnalysisResult(
            area_id=area_id,
            area_name=area_name,
            point_results=point_results,
            correlation_matrix=correlation_matrix,
            combined_risk_level=combined_risk,
            anomaly_summary=anomaly_summary,
            recommendations=recommendations
        )

    @staticmethod
    def assess_overall_risk(db) -> RiskAssessmentResult:
        pending_anomalies = db.get_anomalies_by_status(status="待处理")
        
        anomaly_counts: Dict[str, int] = {}
        for a in pending_anomalies:
            atype = a["anomaly_type"]
            anomaly_counts[atype] = anomaly_counts.get(atype, 0) + 1
        
        risk_score = 0.0
        high_risk_points = []
        
        for a in pending_anomalies:
            level = a.get("risk_level", "低")
            if level == "极高":
                risk_score += 10
                high_risk_points.append(a)
            elif level == "高":
                risk_score += 5
            elif level == "中":
                risk_score += 2
            else:
                risk_score += 1
        
        total_pending = len(pending_anomalies)
        if total_pending > 0:
            risk_score = risk_score / total_pending
        
        if risk_score >= 8:
            overall_risk = "极高"
        elif risk_score >= 5:
            overall_risk = "高"
        elif risk_score >= 2:
            overall_risk = "中"
        else:
            overall_risk = "低"
        
        if total_pending > 10:
            trend_analysis = "待处理异常较多，整体呈上升趋势"
        elif total_pending > 5:
            trend_analysis = "有一定数量待处理异常，需关注"
        else:
            trend_analysis = "异常数量处于正常水平"
        
        recommendations = []
        if overall_risk in ["高", "极高"]:
            recommendations.append("建议优先处理高风险和极高风险异常")
            recommendations.append("考虑增加设备巡检频率")
        if anomaly_counts.get("数据断档", 0) > 3:
            recommendations.append("多个点位存在数据断档，建议检查设备通讯")
        if anomaly_counts.get("疑似堵塞", 0) > 0:
            recommendations.append("存在疑似堵塞情况，建议现场清理维护")
        
        return RiskAssessmentResult(
            overall_risk=overall_risk,
            risk_score=round(risk_score, 2),
            anomaly_counts=anomaly_counts,
            high_risk_points=high_risk_points,
            trend_analysis=trend_analysis,
            recommendations=recommendations
        )
