import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QSplitter
from PySide6.QtCore import Qt

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

import traceback

errors = []
def handle_exception(exc_type, exc_value, exc_tb):
    errors.append(exc_type.__name__)
    print(f'[EXCEPTION] {exc_type.__name__}: {exc_value}')
    traceback.print_tb(exc_tb, limit=5)

sys.excepthook = handle_exception

from database.db_manager import get_db
from ui.device_panel import DevicePanel
from core.chart_view import ChartViewWidget

db = get_db()

print('Test 1: Just DevicePanel in QWidget...')
try:
    w = QWidget()
    layout = QVBoxLayout(w)
    dp = DevicePanel()
    layout.addWidget(dp)
    dp.refresh()
    print(f'  OK (errors so far: {len(errors)})')
except Exception as e:
    print(f'  FAILED: {e}')

print('\nTest 2: DevicePanel in QTabWidget...')
try:
    w2 = QWidget()
    layout2 = QVBoxLayout(w2)
    tabs = QTabWidget()
    dp2 = DevicePanel()
    tabs.addTab(dp2, '设备档案')
    layout2.addWidget(tabs)
    dp2.refresh()
    print(f'  OK (errors so far: {len(errors)})')
except Exception as e:
    print(f'  FAILED: {e}')

print('\nTest 3: DevicePanel + ChartViewWidget in QSplitter...')
try:
    w3 = QWidget()
    layout3 = QVBoxLayout(w3)
    splitter = QSplitter(Qt.Horizontal)
    
    left = QWidget()
    left_layout = QVBoxLayout(left)
    dp3 = DevicePanel()
    left_layout.addWidget(dp3)
    splitter.addWidget(left)
    
    chart = ChartViewWidget()
    splitter.addWidget(chart)
    
    layout3.addWidget(splitter)
    dp3.refresh()
    print(f'  OK (errors so far: {len(errors)})')
except Exception as e:
    print(f'  FAILED: {e}')
    traceback.print_exc()

print('\nTest 4: QMainWindow with device_panel + chart...')
try:
    win = QMainWindow()
    central = QWidget()
    layout4 = QVBoxLayout(central)
    splitter4 = QSplitter(Qt.Horizontal)
    
    left4 = QWidget()
    left_layout4 = QVBoxLayout(left4)
    dp4 = DevicePanel()
    left_layout4.addWidget(dp4)
    splitter4.addWidget(left4)
    
    chart4 = ChartViewWidget()
    splitter4.addWidget(chart4)
    
    layout4.addWidget(splitter4)
    win.setCentralWidget(central)
    
    dp4.refresh()
    print(f'  OK (errors so far: {len(errors)})')
except Exception as e:
    print(f'  FAILED: {e}')
    traceback.print_exc()

print(f'\nTotal exceptions: {len(errors)}')
print('Done.')
