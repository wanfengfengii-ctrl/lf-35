import sys
import traceback
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

errors = []

def handle_exception(exc_type, exc_value, exc_tb):
    msg = f'[{exc_type.__name__}] {exc_value}'
    errors.append(msg)
    print(msg)
    traceback.print_tb(exc_tb)

sys.excepthook = handle_exception

print('=== Testing launch (MainWindow) ===')
try:
    from ui.main_window import MainWindow
    win = MainWindow()
    win.show()
    print('MainWindow created successfully')

    def check_and_exit():
        print(f'Total errors: {len(errors)}')
        if errors:
            for e in errors:
                print(f'  ERROR: {e}')
        app.quit()

    QTimer.singleShot(100, check_and_exit)
    app.exec()
except Exception as e:
    print(f'FAILED to launch: {e}')
    traceback.print_exc()

print('Done.')
