import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from database.db_manager import get_db
from ui.device_panel import DevicePanel

db = get_db()

print(f'Initial recursion depth: {sys.getrecursionlimit()}')

print('\nCreating DevicePanel...')
panel = DevicePanel()
print('Created!')

print('\nCalling refresh() 1st time...')
try:
    panel.refresh()
    print('1st refresh: OK')
except Exception as e:
    print(f'1st refresh: ERROR - {e}')

print('\nCalling refresh() 2nd time...')
try:
    panel.refresh()
    print('2nd refresh: OK')
except Exception as e:
    print(f'2nd refresh: ERROR - {e}')
    import traceback
    traceback.print_exc()

print('\nCalling refresh() 3rd time...')
try:
    panel.refresh()
    print('3rd refresh: OK')
except Exception as e:
    print(f'3rd refresh: ERROR - {e}')

print('\nDone.')
