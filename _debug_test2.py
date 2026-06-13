import sys, os, traceback
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

try:
    from ui.main_window import MainWindow
    window = MainWindow()
    print('MainWindow created OK')
except RecursionError:
    traceback.print_exc(limit=30)
    print('MainWindow creation FAILED with RecursionError')
except Exception as e:
    traceback.print_exc(limit=30)
    print(f'MainWindow creation FAILED with {type(e).__name__}: {e}')
