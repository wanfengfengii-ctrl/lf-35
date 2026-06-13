import sys, os, traceback
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget, QSplitter, QGroupBox
app = QApplication(sys.argv)

from database.db_manager import get_db
db = get_db()
print(f'db._conn is not None: {db._conn is not None}')

from ui.drip_point_panel import DripPointPanel
from ui.data_import_panel import DataImportPanel
from ui.anomaly_panel import AnomalyPanel
from core.chart_view import ChartViewWidget

# Manually replicate MainWindow init
window = QMainWindow()
central = QWidget()
window.setCentralWidget(central)
layout = QVBoxLayout(central)

splitter = QSplitter()
left = QWidget()
left_layout = QVBoxLayout(left)
left_layout.setContentsMargins(0, 0, 0, 0)

tab = QTabWidget()
print('Creating DripPointPanel...')
panel1 = DripPointPanel()
print('Creating DataImportPanel...')
panel2 = DataImportPanel()
print('Creating AnomalyPanel...')
panel3 = AnomalyPanel()

tab.addTab(panel1, "滴水点管理")
tab.addTab(panel2, "数据导入")
tab.addTab(panel3, "异常检测")
left_layout.addWidget(tab)
splitter.addWidget(left)

print('Creating ChartViewWidget...')
chart = ChartViewWidget()
print('All widgets created OK')

# Now simulate refresh_all
print('Calling panel1.refresh()...')
try:
    panel1.refresh()
    print('panel1.refresh() OK')
except RecursionError:
    traceback.print_exc(limit=30)
    print('panel1.refresh() RecursionError!')

print('Calling panel2.refresh_points()...')
try:
    panel2.refresh_points()
    print('panel2.refresh_points() OK')
except RecursionError:
    print('panel2.refresh_points() RecursionError!')

print('Calling panel3.refresh_points()...')
try:
    panel3.refresh_points()
    print('panel3.refresh_points() OK')
except RecursionError:
    print('panel3.refresh_points() RecursionError!')

print('Calling panel3.refresh()...')
try:
    panel3.refresh()
    print('panel3.refresh() OK')
except RecursionError:
    print('panel3.refresh() RecursionError!')
