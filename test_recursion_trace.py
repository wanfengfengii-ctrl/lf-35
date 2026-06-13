import sys
import traceback
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

call_count = 0
from ui.main_window import MainWindow

original_refresh_all = MainWindow.refresh_all
def traced_refresh_all(self):
    global call_count
    call_count += 1
    print(f'  [refresh_all] call #{call_count}')
    if call_count > 10:
        print('  [refresh_all] TOO MANY CALLS - dumping stack')
        traceback.print_stack(limit=30)
        return
    original_refresh_all(self)

MainWindow.refresh_all = traced_refresh_all

print('Creating MainWindow...')
try:
    win = MainWindow()
    print(f'Created OK, refresh_all called {call_count} times')
except RecursionError as e:
    print(f'RecursionError after {call_count} calls: {e}')
    traceback.print_exc(limit=50)
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()

print(f'Total refresh_all calls: {call_count}')
print('Done.')
