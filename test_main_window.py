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
    traceback.print_tb(exc_tb, limit=50)

sys.excepthook = handle_exception

print('=== Testing MainWindow ===')
from ui.main_window import MainWindow

print('Creating MainWindow...')
try:
    win = MainWindow()
    print('Created OK')
    win.show()

    def check():
        print(f'Total errors: {len(errors)}')
        for e in errors:
            print(f'  ERROR: {e}')
        app.quit()

    QTimer.singleShot(200, check)
    app.exec()
except RecursionError as e:
    print(f'RecursionError: {e}')
    traceback.print_exc(limit=100)
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()

print('Done.')
