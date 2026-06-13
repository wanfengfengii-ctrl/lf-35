import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import csv


class ReportGenerator:
    @staticmethod
    def generate_monthly_report(db, point_id: int, year: int, month: int) -> Dict:
        from core.statistics import StatisticsAnalyzer
        
        point = db.get_drip_point(point_id)
        if not point:
            return {}
        
        start_date = f"{year:04d}-{month:02d}-01 00:00:00"
        if month == 12:
            end_date = f"{year+1:04d}-01-01 00:00:00"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01 00:00:00"
        
        data = db.get_monitoring_data(point_id, start_date, end_date)
        day_stats = StatisticsAnalyzer.analyze_period(db, point_id, "day", start_date, end_date)
        anomalies = [a for a in db.get_anomaly_records(point_id) 
                    if a["start_time"] >= start_date and a["start_time"] < end_date]
        
        if data:
            intervals = [d["drip_interval"] for d in data]
            import numpy as np
            summary = {
                "total_records": len(data),
                "interval_mean": round(float(np.mean(intervals)), 2),
                "interval_std": round(float(np.std(intervals)), 2),
                "interval_min": round(float(np.min(intervals)), 2),
                "interval_max": round(float(np.max(intervals)), 2),
            }
        else:
            summary = {
                "total_records": 0,
                "interval_mean": 0,
                "interval_std": 0,
                "interval_min": 0,
                "interval_max": 0,
            }
        
        data_rows = []
        for s in day_stats:
            data_rows.append({
                "时段": s.period,
                "数据量": s.data_count,
                "平均间隔(s)": round(s.avg_interval, 2),
                "最小间隔(s)": round(s.min_interval, 2),
                "最大间隔(s)": round(s.max_interval, 2),
                "变异系数(%)": round(s.cv_interval, 2),
            })

        anomaly_rows = []
        for a in anomalies:
            anomaly_rows.append({
                "异常类型": a["anomaly_type"],
                "风险等级": a["risk_level"],
                "起始时间": a["start_time"],
                "结束时间": a.get("end_time", "-"),
                "状态": a.get("status", "-"),
            })

        combined_data = data_rows
        combined_data.append({})
        combined_data.append({"时段": f"=== 异常记录 ({len(anomaly_rows)} 条) ==="})
        combined_data.extend(anomaly_rows)

        statistics_info = {
            "滴水点编号": point.get("code", "-"),
            "滴水点名称": point.get("name", "-"),
            "位置": point.get("location", "-"),
            "异常总数": len(anomalies),
            "最高风险等级": max([a["risk_level"] for a in anomalies], default="低"),
            "总监测天数": len(day_stats),
        }

        return {
            "title": f"{point.get('code', '-')} - {point.get('name', '-')} 月度监测报告",
            "report_type": "月度监测报告",
            "report_period": f"{year}年{month}月",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "point_info": point,
            "summary": summary,
            "data": combined_data,
            "daily_statistics": day_stats,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "risk_level": max([a["risk_level"] for a in anomalies], default="低"),
            "statistics": statistics_info,
            "notes": "请重点关注异常记录和变异系数大于30%的日期。",
        }

    @staticmethod
    def generate_anomaly_report(db, area_id: Optional[int] = None) -> Dict:
        from core.anomaly_detector import AdvancedAnomalyDetector
        
        pending = db.get_anomalies_by_status(status="待处理", area_id=area_id)
        processing = db.get_anomalies_by_status(status="处理中", area_id=area_id)
        completed = db.get_anomalies_by_status(status="已处理", area_id=area_id)
        
        risk_assessment = AdvancedAnomalyDetector.assess_overall_risk(db)
        
        area_name = "全部洞区"
        if area_id:
            area = db.get_cave_area(area_id)
            if area:
                area_name = f"{area['code']} - {area['name']}"
        
        data_rows = []
        for a in pending:
            data_rows.append({
                "状态": "待处理",
                "滴水点": f"{a.get('drip_point_code', '-')} - {a.get('drip_point_name', '-')}",
                "异常类型": a.get("anomaly_type", "-"),
                "风险等级": a.get("risk_level", "-"),
                "起始时间": a.get("start_time", "-"),
                "描述": a.get("description", "")[:40],
            })
        for a in processing:
            data_rows.append({
                "状态": "处理中",
                "滴水点": f"{a.get('drip_point_code', '-')} - {a.get('drip_point_name', '-')}",
                "异常类型": a.get("anomaly_type", "-"),
                "风险等级": a.get("risk_level", "-"),
                "起始时间": a.get("start_time", "-"),
                "描述": a.get("description", "")[:40],
            })
        for a in completed:
            data_rows.append({
                "状态": "已处理",
                "滴水点": f"{a.get('drip_point_code', '-')} - {a.get('drip_point_name', '-')}",
                "异常类型": a.get("anomaly_type", "-"),
                "风险等级": a.get("risk_level", "-"),
                "起始时间": a.get("start_time", "-"),
                "描述": a.get("description", "")[:40],
            })

        statistics_info = {
            "洞区范围": area_name,
            "待处理": len(pending),
            "处理中": len(processing),
            "已处理": len(completed),
            "综合风险等级": risk_assessment.overall_risk,
            "风险评分": risk_assessment.risk_score,
            "高风险点位": len(risk_assessment.high_risk_points),
            "趋势": risk_assessment.trend_analysis,
        }

        recommendations_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(risk_assessment.recommendations)]) if risk_assessment.recommendations else "暂无建议"

        return {
            "title": f"{area_name} 异常专项报告",
            "report_type": "异常专项报告",
            "report_period": "截至 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "area_name": area_name,
            "summary": statistics_info,
            "data": data_rows,
            "pending_count": len(pending),
            "processing_count": len(processing),
            "completed_count": len(completed),
            "pending_anomalies": pending,
            "processing_anomalies": processing,
            "statistics": statistics_info,
            "risk_assessment": {
                "overall_risk": risk_assessment.overall_risk,
                "risk_score": risk_assessment.risk_score,
                "anomaly_counts": risk_assessment.anomaly_counts,
                "high_risk_count": len(risk_assessment.high_risk_points),
                "trend_analysis": risk_assessment.trend_analysis,
                "recommendations": risk_assessment.recommendations
            },
            "notes": recommendations_text
        }

    @staticmethod
    def generate_joint_analysis_report(db, area_id: int) -> Dict:
        from core.anomaly_detector import AdvancedAnomalyDetector
        
        area = db.get_cave_area(area_id)
        if not area:
            return {}
        
        points = db.get_drip_points_by_area(area_id)
        points_data = {}
        
        for p in points:
            data = db.get_monitoring_data(p["id"])
            points_data[p["id"]] = {
                "code": p["code"],
                "name": p["name"],
                "data": data
            }
        
        joint_result = AdvancedAnomalyDetector.joint_analysis(
            area_id, f"{area['code']} - {area['name']}", points_data
        )
        
        point_results_list = [
            {
                "point_id": pr.point_id,
                "point_code": pr.point_code,
                "point_name": pr.point_name,
                "baseline_mean": pr.baseline_mean,
                "baseline_std": pr.baseline_std,
                "data_count": pr.data_count,
                "anomaly_count": pr.anomaly_count,
                "avg_interval": pr.avg_interval,
                "trend": pr.trend
            }
            for pr in joint_result.point_results
        ]

        data_rows = []
        for pr in point_results_list:
            data_rows.append({
                "点位编号": pr["point_code"],
                "点位名称": pr["point_name"],
                "数据量": pr["data_count"],
                "平均间隔(s)": round(pr["avg_interval"], 2) if pr["avg_interval"] else "-",
                "异常段数": pr["anomaly_count"],
                "趋势": pr["trend"],
            })

        correlation_rows = []
        if joint_result.correlation_matrix:
            correlation_rows.append({})
            correlation_rows.append({"点位编号": "=== 相关系数矩阵 ==="})
            points_order = list(joint_result.correlation_matrix.keys())
            header_row = {"点位编号": "点位编号"}
            for c in points_order:
                header_row[c] = c
            correlation_rows.append(header_row)
            for p1 in points_order:
                row_dict = {"点位编号": p1}
                for p2 in points_order:
                    val = joint_result.correlation_matrix[p1][p2]
                    row_dict[p2] = round(val, 3)
                correlation_rows.append(row_dict)

        all_starts = []
        all_ends = []
        for pr in joint_result.point_results:
            pd = points_data.get(pr.point_id, {}).get("data", [])
            if pd:
                all_starts.append(pd[0]["record_time"])
                all_ends.append(pd[-1]["record_time"])
        common_period_text = "-"
        if all_starts and all_ends:
            common_period_text = f"{min(all_starts)} 至 {max(all_ends)}"

        statistics_info = {
            "洞区": f"{area['code']} - {area['name']}",
            "点位数量": len(points),
            "综合风险等级": joint_result.combined_risk_level,
            "共同时段": common_period_text,
        }

        recommendations_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(joint_result.recommendations)]) if joint_result.recommendations else "暂无建议"

        return {
            "title": f"{area['code']} - {area['name']} 联合分析报告",
            "report_type": "多滴水点联合分析报告",
            "report_period": "截至 " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "area_info": area,
            "point_count": len(points),
            "summary": statistics_info,
            "data": data_rows + correlation_rows,
            "statistics": statistics_info,
            "combined_risk_level": joint_result.combined_risk_level,
            "point_results": point_results_list,
            "correlation_matrix": joint_result.correlation_matrix,
            "anomaly_summary": joint_result.anomaly_summary,
            "recommendations": joint_result.recommendations,
            "notes": recommendations_text
        }

    @staticmethod
    def export_to_csv(report_data: Dict, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                
                writer.writerow(["报告类型", report_data.get("report_type", "")])
                writer.writerow(["报告周期", report_data.get("report_period", "")])
                writer.writerow(["生成时间", report_data.get("generated_at", "")])
                writer.writerow([])
                
                if "point_info" in report_data:
                    writer.writerow(["监测点信息"])
                    pi = report_data["point_info"]
                    writer.writerow(["编号", pi.get("code", "")])
                    writer.writerow(["名称", pi.get("name", "")])
                    writer.writerow(["位置", pi.get("location", "")])
                    writer.writerow([])
                
                if "summary" in report_data:
                    writer.writerow(["数据摘要"])
                    s = report_data["summary"]
                    writer.writerow(["总记录数", s.get("total_records", 0)])
                    writer.writerow(["平均滴水间隔(s)", s.get("interval_mean", 0)])
                    writer.writerow(["标准差", s.get("interval_std", 0)])
                    writer.writerow(["最小值", s.get("interval_min", 0)])
                    writer.writerow(["最大值", s.get("interval_max", 0)])
                    writer.writerow([])
                
                if "daily_statistics" in report_data:
                    writer.writerow(["日统计数据"])
                    writer.writerow(["日期", "记录数", "平均间隔(s)", "标准差", "CV(%)", "最小(s)", "最大(s)", "平均温度(℃)", "平均湿度(%)", "平均盐度(‰)"])
                    for ds in report_data["daily_statistics"]:
                        writer.writerow([
                            ds.period, ds.data_count, ds.avg_interval, ds.std_interval,
                            ds.cv_interval, ds.min_interval, ds.max_interval,
                            ds.avg_temperature or "", ds.avg_humidity or "", ds.avg_salinity or ""
                        ])
                    writer.writerow([])
                
                if "anomalies" in report_data:
                    writer.writerow(["异常记录"])
                    writer.writerow(["类型", "风险等级", "开始时间", "结束时间", "描述"])
                    for a in report_data["anomalies"]:
                        writer.writerow([
                            a.get("anomaly_type", ""), a.get("risk_level", ""),
                            a.get("start_time", ""), a.get("end_time", ""),
                            a.get("description", "")
                        ])
                    writer.writerow([])
                
                if "recommendations" in report_data:
                    writer.writerow(["建议"])
                    for i, rec in enumerate(report_data["recommendations"], 1):
                        writer.writerow([f"{i}. {rec}"])
                
                return True, f"报告已导出: {file_path}"
        except Exception as e:
            return False, f"导出失败: {str(e)}"

    @staticmethod
    def export_to_text(report_data: Dict, file_path: str) -> Tuple[bool, str]:
        try:
            lines = []
            
            lines.append("=" * 60)
            lines.append(f"报告类型: {report_data.get('report_type', '')}")
            lines.append(f"报告周期: {report_data.get('report_period', '')}")
            lines.append(f"生成时间: {report_data.get('generated_at', '')}")
            lines.append("=" * 60)
            lines.append("")
            
            if "point_info" in report_data:
                pi = report_data["point_info"]
                lines.append("【监测点信息】")
                lines.append(f"  编号: {pi.get('code', '')}")
                lines.append(f"  名称: {pi.get('name', '')}")
                lines.append(f"  位置: {pi.get('location', '')}")
                lines.append("")
            
            if "summary" in report_data:
                s = report_data["summary"]
                lines.append("【数据摘要】")
                lines.append(f"  总记录数: {s.get('total_records', 0)}")
                lines.append(f"  平均滴水间隔: {s.get('interval_mean', 0):.2f} s")
                lines.append(f"  标准差: {s.get('interval_std', 0):.2f}")
                lines.append(f"  范围: {s.get('interval_min', 0):.2f} - {s.get('interval_max', 0):.2f} s")
                lines.append("")
            
            if "pending_count" in report_data:
                lines.append("【异常统计】")
                lines.append(f"  待处理: {report_data.get('pending_count', 0)}")
                lines.append(f"  处理中: {report_data.get('processing_count', 0)}")
                lines.append(f"  已处理: {report_data.get('completed_count', 0)}")
                lines.append("")
            
            if "risk_assessment" in report_data:
                ra = report_data["risk_assessment"]
                lines.append("【风险评估】")
                lines.append(f"  综合风险等级: {ra.get('overall_risk', '')}")
                lines.append(f"  风险评分: {ra.get('risk_score', 0)}/10")
                lines.append(f"  高风险异常数: {ra.get('high_risk_count', 0)}")
                lines.append(f"  趋势分析: {ra.get('trend_analysis', '')}")
                lines.append("")
            
            if "point_results" in report_data:
                lines.append("【各监测点分析结果】")
                for pr in report_data["point_results"]:
                    lines.append(f"  {pr.get('point_code', '')} - {pr.get('point_name', '')}:")
                    lines.append(f"    数据量: {pr.get('data_count', 0)} | 异常数: {pr.get('anomaly_count', 0)}")
                    lines.append(f"    平均间隔: {pr.get('avg_interval', 0):.2f}s | 趋势: {pr.get('trend', '')}")
                lines.append("")
            
            if "recommendations" in report_data:
                lines.append("【建议】")
                for i, rec in enumerate(report_data["recommendations"], 1):
                    lines.append(f"  {i}. {rec}")
                lines.append("")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            return True, f"报告已导出: {file_path}"
        except Exception as e:
            return False, f"导出失败: {str(e)}"

    @staticmethod
    def get_available_report_types() -> List[Dict]:
        return [
            {"key": "monthly", "name": "月度监测报告", "description": "按月份导出单滴水点统计报告"},
            {"key": "anomaly", "name": "异常专项报告", "description": "导出异常处理进度与风险评估"},
            {"key": "joint", "name": "联合分析报告", "description": "导出洞区多滴水点联合分析结果"},
        ]
