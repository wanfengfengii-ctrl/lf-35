import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
import traceback

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

errors = []

def handle_exception(exc_type, exc_value, exc_tb):
    errors.append((exc_type.__name__, str(exc_value)))
    print(f"\n[EXCEPTION] {exc_type.__name__}: {exc_value}")
    traceback.print_tb(exc_tb, limit=10)

sys.excepthook = handle_exception

print('=== Testing Full App Start ===')

from ui.main_window import MainWindow

try:
    window = MainWindow()
    print('MainWindow created successfully!')
except Exception as e:
    print(f'MainWindow creation FAILED: {e}')
    traceback.print_exc()
    sys.exit(1)

print(f'\nTotal exceptions during startup: {len(errors)}')
for i, (name, msg) in enumerate(errors):
    print(f'  {i+1}. {name}: {msg[:100]}')

print('\n=== Testing Tab Switches ===')
tab_errors = []
for i in range(window.tab_widget.count()):
    tab_name = window.tab_widget.tabText(i)
    try:
        window.tab_widget.setCurrentIndex(i)
        print(f'  Tab {i} [{tab_name}]: OK')
    except Exception as e:
        tab_errors.append((tab_name, str(e)))
        print(f'  Tab {i} [{tab_name}]: ERROR - {e}')

if tab_errors:
    print(f'\nTab errors: {len(tab_errors)}')
    for name, msg in tab_errors:
        print(f'  - {name}: {msg[:100]}')

print('\n=== Test Result ===')
if errors or tab_errors:
    print(f'FAILED: {len(errors)} startup errors, {len(tab_errors)} tab errors')
else:
    print('PASSED: All tests passed!')
