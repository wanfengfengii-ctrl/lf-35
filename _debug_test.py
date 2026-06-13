import sys, os, traceback
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from database.db_manager import DatabaseManager, get_db
db = get_db()
print(f'db id={id(db)}, conn={db._conn is not None}')

from ui.drip_point_panel import DripPointPanel
panel1 = DripPointPanel()
print('Step 1: DripPointPanel OK')

from ui.data_import_panel import DataImportPanel
panel2 = DataImportPanel()
print('Step 2: DataImportPanel OK')

from ui.anomaly_panel import AnomalyPanel
panel3 = AnomalyPanel()
print('Step 3: AnomalyPanel OK')

sys.setrecursionlimit(50)
try:
    panel1.refresh()
    print('Step 4: panel1.refresh() OK')
except RecursionError:
    traceback.print_exc(limit=30)
    print('Step 4: panel1.refresh() FAILED')
sys.setrecursionlimit(1000)

try:
    panel2.refresh_points()
    print('Step 5: panel2.refresh_points() OK')
except RecursionError:
    traceback.print_exc(limit=10)
    print('Step 5: panel2.refresh_points() FAILED')

try:
    panel3.refresh_points()
    panel3.refresh()
    print('Step 6: panel3 refresh OK')
except RecursionError:
    traceback.print_exc(limit=10)
    print('Step 6: panel3 refresh FAILED')
