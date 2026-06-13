import sys
import traceback
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

print('=== Step 1: Import db_manager ===')
from database.db_manager import get_db

print('=== Step 2: Get db instance ===')
db = get_db()

print('=== Step 3: Test get_calibration_records ===')
import sys
sys.setrecursionlimit(200)

try:
    records = db.get_calibration_records()
    print(f'  Success: {len(records)} records')
except RecursionError as e:
    print(f'  RecursionError: {e}')
    traceback.print_exc()

print('=== Step 4: Test DevicePanel import ===')
try:
    from ui.device_panel import DevicePanel
    print('  Import OK')
except Exception as e:
    print(f'  Import failed: {e}')
    traceback.print_exc()

print('=== Step 5: Test DevicePanel creation ===')
try:
    dp = DevicePanel()
    print('  Creation OK')
    dp.refresh()
    print('  Refresh OK')
except RecursionError as e:
    print(f'  RecursionError: {e}')
    traceback.print_exc()
except Exception as e:
    print(f'  Error: {e}')
    traceback.print_exc()

print('Done.')
