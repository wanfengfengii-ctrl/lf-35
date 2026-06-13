import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from database.db_manager import get_db
from ui.cave_panel import CavePanel
from ui.drip_point_panel import DripPointPanel
from ui.device_panel import DevicePanel
from ui.data_import_panel import DataImportPanel
from ui.qc_panel import QCPanel
from ui.anomaly_panel import AnomalyPanel
from ui.dashboard_panel import DashboardPanel
from ui.handling_panel import HandlingPanel
from ui.statistics_panel import StatisticsPanel
from ui.report_panel import ReportPanel

db = get_db()

panels = []

print('1. Creating CavePanel...')
p = CavePanel()
panels.append(('cave', p))
print('   OK')

print('2. Creating DripPointPanel...')
p = DripPointPanel()
panels.append(('drip_point', p))
print('   OK')

print('3. Creating DevicePanel...')
p = DevicePanel()
panels.append(('device', p))
print('   OK')

print('4. Creating DataImportPanel...')
p = DataImportPanel()
panels.append(('data_import', p))
print('   OK')

print('5. Creating QCPanel...')
p = QCPanel()
panels.append(('qc', p))
print('   OK')

print('6. Creating AnomalyPanel...')
p = AnomalyPanel()
panels.append(('anomaly', p))
print('   OK')

print('7. Creating DashboardPanel...')
p = DashboardPanel()
panels.append(('dashboard', p))
print('   OK')

print('8. Creating HandlingPanel...')
p = HandlingPanel()
panels.append(('handling', p))
print('   OK')

print('9. Creating StatisticsPanel...')
p = StatisticsPanel()
panels.append(('statistics', p))
print('   OK')

print('10. Creating ReportPanel...')
p = ReportPanel()
panels.append(('report', p))
print('   OK')

print('\nNow calling refresh on device panel again...')
dev_panel = [p for n, p in panels if n == 'device'][0]
try:
    dev_panel.refresh()
    print('Device panel refresh after all others: OK')
except Exception as e:
    print(f'Device panel refresh after all others: ERROR - {e}')
    import traceback
    traceback.print_exc()

print('\nDone.')
