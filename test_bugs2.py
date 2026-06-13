import sys
sys.path.insert(0, '.')

print('=== Test 1: All Imports ===')
from database.db_manager import get_db
from core.anomaly_detector import AnomalyDetector, AdvancedAnomalyDetector, ANOMALY_TYPES, RISK_LEVELS
from core.data_import import DataImporter, DataQualityChecker
from core.statistics import StatisticsAnalyzer
from core.report_generator import ReportGenerator
from ui.qc_panel import QCPanel
from ui.statistics_panel import StatisticsPanel
from ui.report_panel import ReportPanel
from ui.dashboard_panel import DashboardPanel
from ui.handling_panel import HandlingPanel
from ui.main_window import MainWindow
print('All imports OK')

print('\n=== Test 2: DB Operations ===')
db = get_db()

areas = db.get_all_cave_areas()
print(f'Existing areas: {len(areas)}')
if areas:
    area_id = areas[0]['id']
else:
    ok, msg, area_id = db.add_cave_area('TEST001', '测试洞区', '测试位置', '花岗岩', '测试用')
    print(f'Add area: ok={ok}, id={area_id}, msg={msg}')

points = db.get_all_drip_points()
print(f'Existing points: {len(points)}')
if points:
    point_id = points[0]['id']
else:
    ok, msg, point_id = db.add_drip_point('DP001', '测试滴水点', '测试位置', area_id=area_id)
    print(f'Add point: ok={ok}, id={point_id}, msg={msg}')

yr = db.get_data_year_range(point_id)
print(f'get_data_year_range: {yr} (type: {type(yr).__name__})')

print('\n=== Test 3: StatisticsAnalyzer ===')
try:
    stats = StatisticsAnalyzer.analyze_period(db, point_id, "day", "2024-01-01", "2024-12-31")
    print(f'analyze_period: {len(stats)} periods returned')
    if stats:
        print(f'  first: period={stats[0].period}, avg={stats[0].avg_interval}, std={stats[0].std_interval}, cv={stats[0].cv_interval}')
except Exception as e:
    import traceback
    print(f'analyze_period ERROR: {e}')
    traceback.print_exc()

try:
    summary = StatisticsAnalyzer.get_summary_statistics(db, point_id)
    print(f'get_summary_statistics: {type(summary).__name__}, keys={list(summary.keys())}')
except Exception as e:
    import traceback
    print(f'get_summary_statistics ERROR: {e}')
    traceback.print_exc()

try:
    seasonal = StatisticsAnalyzer.calculate_seasonal_index(db, point_id)
    print(f'calculate_seasonal_index: {type(seasonal).__name__}, keys={list(seasonal.keys())}')
except Exception as e:
    import traceback
    print(f'calculate_seasonal_index ERROR: {e}')
    traceback.print_exc()

print('\n=== Test 4: Report Generator ===')
try:
    rep = ReportGenerator.generate_monthly_report(db, point_id, 2024, 1)
    print(f'Monthly report generated: keys={list(rep.keys())}, title={rep.get("title")}')
except Exception as e:
    import traceback
    print(f'Monthly report ERROR: {e}')
    traceback.print_exc()

try:
    rep = ReportGenerator.generate_anomaly_report(db, area_id=None)
    print(f'Anomaly report generated: keys={list(rep.keys())}, title={rep.get("title")}')
except Exception as e:
    import traceback
    print(f'Anomaly report ERROR: {e}')
    traceback.print_exc()

print('\n=== Test 5: Dashboard assess_overall_risk ===')
try:
    risk = AdvancedAnomalyDetector.assess_overall_risk(db)
    print(f'assess_overall_risk: overall_risk={risk.overall_risk}, score={risk.risk_score}')
except Exception as e:
    import traceback
    print(f'assess_overall_risk ERROR: {e}')
    traceback.print_exc()

print('\nAll tests done!')
