import sys
import traceback
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QDate

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

errors = []
def handle_exception(exc_type, exc_value, exc_tb):
    msg = f'[{exc_type.__name__}] {exc_value}'
    errors.append(msg)
    print(msg)
    traceback.print_tb(exc_tb, limit=30)

sys.excepthook = handle_exception

from database.db_manager import get_db
from core.data_import import DataImporter

db = get_db()

print('=== Step 1: Add test data ===')
# Add a test cave area
try:
    ok, msg, area_id = db.add_cave_area(
        code="TEST-001",
        name="测试洞区",
        location="测试地点",
        geological_type="海蚀洞"
    )
    print(f'  Add area: {ok}, id={area_id}')
except Exception as e:
    print(f'  Add area FAILED: {e}')
    area_id = None
    areas = db.get_all_cave_areas()
    if areas:
        area_id = areas[0]["id"]

# Add a test drip point
try:
    ok, msg, point_id = db.add_drip_point(
        code="TEST-DP-01",
        name="测试滴水点",
        location="测试位置",
        area_id=area_id,
        elevation=10.5,
        description="用于测试"
    )
    print(f'  Add point: {ok}, id={point_id}')
except Exception as e:
    print(f'  Add point FAILED: {e}')
    points = db.get_all_drip_points()
    if points:
        point_id = points[0]["id"]

# Generate sample data and import
if point_id:
    import tempfile, os
    sample_path = os.path.join(tempfile.gettempdir(), "test_sample.csv")
    DataImporter.generate_sample_csv(sample_path)
    print(f'  Generated sample: {sample_path}')

    success, error, data, parse_errors = DataImporter.import_csv(sample_path)
    if success:
        ok, error_msg, sc, sk = db.batch_add_monitoring_data_with_qc(point_id, data, None)
        print(f'  Imported: {sc} records')
    else:
        print(f'  Import failed: {error}')

print('\n=== Step 2: Test MainWindow ===')
from ui.main_window import MainWindow
win = MainWindow()
win.show()
print('  MainWindow: OK')

print('\n=== Step 3: Test statistics panel ===')
for i in range(win.tab_widget.count()):
    if '统计' in win.tab_widget.tabText(i):
        win.tab_widget.setCurrentIndex(i)
        print(f'  Switched to tab: {win.tab_widget.tabText(i)}')
        break

stats_panel = win.statistics_panel
try:
    # Select a point
    if stats_panel.point_combo.count() > 0:
        stats_panel.point_combo.setCurrentIndex(0)
        print(f'  Selected point: {stats_panel.point_combo.currentText()}')

    # Run statistics
    stats_panel._on_run_statistics()
    print('  Run statistics: OK')

    # Check different tabs
    stats_panel.tab_widget.setCurrentIndex(1)  # Summary
    print('  Summary tab: OK')

    stats_panel.tab_widget.setCurrentIndex(2)  # Multi-point
    print('  Multi-point tab: OK')

    stats_panel.tab_widget.setCurrentIndex(0)  # Period
    print('  Period tab: OK')
except Exception as e:
    print(f'  Statistics FAILED: {e}')
    traceback.print_exc()

print('\n=== Step 4: Test report panel (monthly) ===')
for i in range(win.tab_widget.count()):
    if '报告' in win.tab_widget.tabText(i):
        win.tab_widget.setCurrentIndex(i)
        print(f'  Switched to tab: {win.tab_widget.tabText(i)}')
        break

report_panel = win.report_panel
try:
    # Select monthly report
    report_panel.type_combo.setCurrentIndex(0)
    print(f'  Report type: {report_panel.type_combo.currentText()}')

    if report_panel.point_combo.count() > 0:
        report_panel.point_combo.setCurrentIndex(0)

    # Generate
    report_panel._on_generate()
    print('  Monthly report: OK')
    preview = report_panel.preview_text.toPlainText()
    print(f'  Preview length: {len(preview)} chars')
except Exception as e:
    print(f'  Monthly report FAILED: {e}')
    traceback.print_exc()

print('\n=== Step 5: Test report panel (anomaly) ===')
try:
    # Set anomaly type - need to find its index
    for i in range(report_panel.type_combo.count()):
        if '异常' in report_panel.type_combo.itemText(i):
            report_panel.type_combo.setCurrentIndex(i)
            print(f'  Report type: {report_panel.type_combo.currentText()}')
            break
    report_panel._on_generate()
    print('  Anomaly report: OK')
except Exception as e:
    print(f'  Anomaly report FAILED: {e}')
    traceback.print_exc()

print('\n=== Step 6: Test report panel (joint) ===')
try:
    for i in range(report_panel.type_combo.count()):
        if '联合' in report_panel.type_combo.itemText(i):
            report_panel.type_combo.setCurrentIndex(i)
            print(f'  Report type: {report_panel.type_combo.currentText()}')
            break
    report_panel._on_generate()
    print('  Joint report: OK')
except Exception as e:
    print(f'  Joint report FAILED: {e}')
    traceback.print_exc()

print(f'\n=== Total errors: {len(errors)} ===')
for i, e in enumerate(errors):
    print(f'  {i+1}. {e}')

def close_app():
    app.quit()

QTimer.singleShot(100, close_app)
app.exec()

print('Done.')
