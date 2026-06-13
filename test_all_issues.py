import sys
import traceback
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

errors = []
def handle_exception(exc_type, exc_value, exc_tb):
    msg = f'[{exc_type.__name__}] {exc_value}'
    errors.append(msg)
    print(msg)
    traceback.print_tb(exc_tb, limit=20)

sys.excepthook = handle_exception

print('=== Test 1: MainWindow launch ===')
from ui.main_window import MainWindow
try:
    win = MainWindow()
    win.show()
    print('Launch: OK')
except Exception as e:
    print(f'Launch FAILED: {e}')
    traceback.print_exc()
    sys.exit(1)

print('\n=== Test 2: Switch to report panel ===')
try:
    from ui.report_panel import ReportPanel
    # Find the report tab index
    for i in range(win.tab_widget.count()):
        if '报告' in win.tab_widget.tabText(i):
            win.tab_widget.setCurrentIndex(i)
            print(f'Switched to tab {i}: {win.tab_widget.tabText(i)}')
            break
    print('Report panel switch: OK')
except Exception as e:
    print(f'Report panel switch FAILED: {e}')
    traceback.print_exc()

print('\n=== Test 3: Statistics panel - run analysis ===')
try:
    for i in range(win.tab_widget.count()):
        if '统计' in win.tab_widget.tabText(i):
            win.tab_widget.setCurrentIndex(i)
            print(f'Switched to tab {i}: {win.tab_widget.tabText(i)}')
            break

    stats_panel = win.statistics_panel
    # Check if there are any points
    if stats_panel.point_combo.count() > 0:
        # Simulate clicking the analyze button
        stats_panel._on_analyze()
        print('Statistics analyze: OK')
    else:
        print('No drip points to analyze - skipped')
except Exception as e:
    print(f'Statistics analyze FAILED: {e}')
    traceback.print_exc()

print('\n=== Test 4: Generate monthly report ===')
try:
    for i in range(win.tab_widget.count()):
        if '报告' in win.tab_widget.tabText(i):
            win.tab_widget.setCurrentIndex(i)
            break

    report_panel = win.report_panel
    if report_panel.point_combo.count() > 0:
        # Make sure monthly is selected
        report_panel.type_combo.setCurrentIndex(0)
        # Click generate
        report_panel._on_generate()
        print('Monthly report generation: OK')
    else:
        print('No drip points for report - skipped')
except Exception as e:
    print(f'Monthly report FAILED: {e}')
    traceback.print_exc()

print(f'\n=== Total errors: {len(errors)} ===')
for i, e in enumerate(errors):
    print(f'  {i+1}. {e}')

def close_app():
    app.quit()

QTimer.singleShot(100, close_app)
app.exec()

print('Done.')
