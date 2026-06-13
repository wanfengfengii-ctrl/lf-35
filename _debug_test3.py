import sys, os, traceback
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

print(f'Default recursion limit: {sys.getrecursionlimit()}')

from database.db_manager import DatabaseManager, get_db
db = get_db()
print(f'db._conn is not None: {db._conn is not None}')

from ui.drip_point_panel import DripPointPanel
panel = DripPointPanel()
print('Panel created OK (refresh done in __init__)')

# Now try what MainWindow does
from ui.data_import_panel import DataImportPanel
from ui.anomaly_panel import AnomalyPanel
print('All panels imported OK')

# What refresh_all does:
try:
    panel.refresh()
    print('panel.refresh() OK')
except RecursionError:
    traceback.print_exc(limit=50)
    print('panel.refresh() RecursionError!')

# Test direct db call
try:
    points = db.get_all_drip_points()
    print(f'direct db.get_all_drip_points() OK: {len(points)}')
except RecursionError:
    print('direct db.get_all_drip_points() RecursionError!')
