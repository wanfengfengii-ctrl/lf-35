import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from database.db_manager import get_db
from core.data_import import DataImporter
import os
import tempfile
import random
from datetime import datetime, timedelta

print('=== Setup Test Data ===')
db = get_db()

areas = db.get_all_cave_areas()
if not areas:
    ok, msg, area_id = db.add_cave_area('TEST001', '测试洞区', '测试位置', '花岗岩', '测试用')
    print(f'Add area: ok={ok}, id={area_id}')
else:
    area_id = areas[0]['id']

points = db.get_all_drip_points()
if not points:
    ok, msg, point_id = db.add_drip_point('DP001', '测试滴水点', '测试位置', area_id=area_id)
    print(f'Add point: ok={ok}, id={point_id}')
else:
    point_id = points[0]['id']

count = db.get_monitoring_data_count(point_id)
print(f'Current data count: {count}')

if count < 100:
    print('Generating test data...')
    start = datetime(2024, 1, 1, 0, 0, 0)
    data = []
    for i in range(500):
        t = start + timedelta(minutes=i * 15)
        interval = 60.0 + random.gauss(0, 10)
        if 100 < i < 120:
            interval = 120.0
        temp = 15.0 + random.gauss(0, 2)
        humidity = 75.0 + random.gauss(0, 5)
        salinity = 30.0 + random.gauss(0, 3)
        data.append({
            'record_time': t.strftime('%Y-%m-%d %H:%M:%S'),
            'drip_interval': round(interval, 2),
            'temperature': round(temp, 2),
            'humidity': round(humidity, 2),
            'salinity': round(salinity, 2),
        })

    ok, msg, sc, ec = db.batch_add_monitoring_data(point_id, data)
    print(f'Added data: ok={ok}, success={sc}, error={ec}')

count = db.get_monitoring_data_count(point_id)
print(f'Final data count: {count}')

print('\n=== Test StatisticsAnalyzer with data ===')
from core.statistics import StatisticsAnalyzer

try:
    stats = StatisticsAnalyzer.analyze_period(db, point_id, "day", "2024-01-01", "2024-12-31")
    print(f'analyze_period (day): {len(stats)} periods')
    if stats:
        print(f'  first: period={stats[0].period}, count={stats[0].data_count}, avg={stats[0].avg_interval:.2f}, std={stats[0].std_interval:.2f}, cv={stats[0].cv_interval:.2f}%')
except Exception as e:
    import traceback
    print(f'analyze_period ERROR: {e}')
    traceback.print_exc()

try:
    stats = StatisticsAnalyzer.analyze_period(db, point_id, "week")
    print(f'analyze_period (week): {len(stats)} periods')
except Exception as e:
    import traceback
    print(f'analyze_period (week) ERROR: {e}')
    traceback.print_exc()

try:
    stats = StatisticsAnalyzer.analyze_period(db, point_id, "month")
    print(f'analyze_period (month): {len(stats)} periods')
except Exception as e:
    import traceback
    print(f'analyze_period (month) ERROR: {e}')
    traceback.print_exc()

try:
    summary = StatisticsAnalyzer.get_summary_statistics(db, point_id)
    print(f'get_summary_statistics: {list(summary.keys())}')
    print(f'  total_records: {summary.get("total_records")}')
    print(f'  interval_mean: {summary.get("interval_mean")}')
    print(f'  trend: {summary.get("trend")}')
    print(f'  data_quality: {summary.get("data_quality")}')
except Exception as e:
    import traceback
    print(f'get_summary_statistics ERROR: {e}')
    traceback.print_exc()

try:
    seasonal = StatisticsAnalyzer.calculate_seasonal_index(db, point_id)
    print(f'calculate_seasonal_index: {list(seasonal.keys())}')
    for k, v in seasonal.items():
        print(f'  {k}: count={v.get("count")}, index={v.get("index")}')
except Exception as e:
    import traceback
    print(f'calculate_seasonal_index ERROR: {e}')
    traceback.print_exc()

print('\n=== Test Report Generator with data ===')
from core.report_generator import ReportGenerator

try:
    rep = ReportGenerator.generate_monthly_report(db, point_id, 2024, 1)
    print(f'Monthly report: title={rep.get("title")}')
    print(f'  summary keys: {list(rep.get("summary", {}).keys())}')
    print(f'  data rows: {len(rep.get("data", []))}')
    print(f'  daily_statistics: {len(rep.get("daily_statistics", []))} days')
except Exception as e:
    import traceback
    print(f'Monthly report ERROR: {e}')
    traceback.print_exc()

try:
    rep = ReportGenerator.generate_anomaly_report(db, area_id=area_id)
    print(f'Anomaly report: title={rep.get("title")}')
    print(f'  pending_count: {rep.get("pending_count")}')
except Exception as e:
    import traceback
    print(f'Anomaly report ERROR: {e}')
    traceback.print_exc()

try:
    rep = ReportGenerator.generate_joint_analysis_report(db, area_id)
    print(f'Joint analysis report: title={rep.get("title")}')
except Exception as e:
    import traceback
    print(f'Joint analysis report ERROR: {e}')
    traceback.print_exc()

print('\n=== Test Anomaly Detection ===')
from core.anomaly_detector import AdvancedAnomalyDetector

data = db.get_monitoring_data(point_id)
try:
    det = AdvancedAnomalyDetector()
    result = det.detect_anomalies(data)
    print(f'Anomaly detection: {len(result.segments)} segments found')
    for seg in result.segments[:5]:
        print(f'  {seg.anomaly_type} ({seg.risk_level}): {seg.start_time} ~ {seg.end_time}')
except Exception as e:
    import traceback
    print(f'Anomaly detection ERROR: {e}')
    traceback.print_exc()

try:
    risk = AdvancedAnomalyDetector.assess_overall_risk(db)
    print(f'Overall risk: {risk.overall_risk}, score={risk.risk_score}')
    print(f'  anomaly_counts: {risk.anomaly_counts}')
    print(f'  high_risk_points: {risk.high_risk_points}')
except Exception as e:
    import traceback
    print(f'assess_overall_risk ERROR: {e}')
    traceback.print_exc()

print('\n=== Test Main Window with data ===')
try:
    from ui.main_window import MainWindow
    window = MainWindow()
    print('MainWindow created successfully!')

    print('\nSwitching to statistics tab and running stats...')
    window.tab_widget.setCurrentIndex(8)
    window.statistics_panel._on_run_statistics()
    print('Statistics execution: OK')

    print('\nSwitching to report tab and generating monthly report...')
    window.tab_widget.setCurrentIndex(9)
    window.report_panel._on_generate()
    print('Monthly report generation: OK')

    print('\nSwitching to dashboard tab...')
    window.tab_widget.setCurrentIndex(6)
    print('Dashboard tab: OK')

    print('\nAll tests passed!')
except Exception as e:
    import traceback
    print(f'Main window test ERROR: {e}')
    traceback.print_exc()
