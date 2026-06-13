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
    traceback.print_tb(exc_tb, limit=30)

sys.excepthook = handle_exception

print('=== Import panels one by one ===')

panels_to_test = [
    ('cave_panel', 'CavePanel'),
    ('drip_point_panel', 'DripPointPanel'),
    ('device_panel', 'DevicePanel'),
    ('data_import_panel', 'DataImportPanel'),
    ('qc_panel', 'QCPanel'),
    ('anomaly_panel', 'AnomalyPanel'),
    ('dashboard_panel', 'DashboardPanel'),
    ('handling_panel', 'HandlingPanel'),
    ('statistics_panel', 'StatisticsPanel'),
    ('report_panel', 'ReportPanel'),
]

created_panels = {}

for module_name, class_name in panels_to_test:
    print(f'\n--- Testing {module_name}.{class_name} ...')
    try:
        mod = __import__(f'ui.{module_name}', fromlist=[class_name])
        cls = getattr(mod, class_name)
        panel = cls()
        print(f'  Created OK')
        try:
            if hasattr(panel, 'refresh'):
                panel.refresh()
                print(f'  refresh() OK')
            elif hasattr(panel, 'refresh_points'):
                panel.refresh_points()
                print(f'  refresh_points() OK')
            elif hasattr(panel, 'refresh_areas'):
                panel.refresh_areas()
                print(f'  refresh_areas() OK')
        except Exception as e:
            print(f'  Refresh error: {e}')
            traceback.print_exc()
        created_panels[module_name] = panel
    except RecursionError as e:
        print(f'  RecursionError: {e}')
        traceback.print_exc()
    except Exception as e:
        print(f'  Error: {e}')
        traceback.print_exc()

print(f'\n=== Total panels created: {len(created_panels)}')
print(f'Total errors: {len(errors)}')
for e in errors:
    print(f'  ERROR: {e}')
print('Done.')
