import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

print('=== Testing UI Panels ===')

from database.db_manager import get_db
db = get_db()

panels = []

try:
    from ui.cave_panel import CavePanel
    p = CavePanel()
    panels.append(('CavePanel', p))
    print('CavePanel: OK')
except Exception as e:
    import traceback
    print(f'CavePanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.drip_point_panel import DripPointPanel
    p = DripPointPanel()
    panels.append(('DripPointPanel', p))
    print('DripPointPanel: OK')
except Exception as e:
    import traceback
    print(f'DripPointPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.device_panel import DevicePanel
    p = DevicePanel()
    panels.append(('DevicePanel', p))
    print('DevicePanel: OK')
except Exception as e:
    import traceback
    print(f'DevicePanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.data_import_panel import DataImportPanel
    p = DataImportPanel()
    panels.append(('DataImportPanel', p))
    print('DataImportPanel: OK')
except Exception as e:
    import traceback
    print(f'DataImportPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.qc_panel import QCPanel
    p = QCPanel()
    panels.append(('QCPanel', p))
    print('QCPanel: OK')
except Exception as e:
    import traceback
    print(f'QCPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.anomaly_panel import AnomalyPanel
    p = AnomalyPanel()
    panels.append(('AnomalyPanel', p))
    print('AnomalyPanel: OK')
except Exception as e:
    import traceback
    print(f'AnomalyPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.dashboard_panel import DashboardPanel
    p = DashboardPanel()
    panels.append(('DashboardPanel', p))
    print('DashboardPanel: OK')
except Exception as e:
    import traceback
    print(f'DashboardPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.handling_panel import HandlingPanel
    p = HandlingPanel()
    panels.append(('HandlingPanel', p))
    print('HandlingPanel: OK')
except Exception as e:
    import traceback
    print(f'HandlingPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.statistics_panel import StatisticsPanel
    p = StatisticsPanel()
    panels.append(('StatisticsPanel', p))
    print('StatisticsPanel: OK')
except Exception as e:
    import traceback
    print(f'StatisticsPanel: ERROR - {e}')
    traceback.print_exc()

try:
    from ui.report_panel import ReportPanel
    p = ReportPanel()
    panels.append(('ReportPanel', p))
    print('ReportPanel: OK')
except Exception as e:
    import traceback
    print(f'ReportPanel: ERROR - {e}')
    traceback.print_exc()

print(f'\nTotal panels created: {len(panels)}')
print('All UI panel tests done!')
