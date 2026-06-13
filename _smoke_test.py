import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from database.db_manager import DatabaseManager, get_db
db = get_db()
points = db.get_all_drip_points()
print(f'数据库连接正常，滴水点数量: {len(points)}')

from core.data_import import DataImporter
assert DataImporter.parse_float('0') == 0.0, 'parse_float(0) 应返回 0.0'
assert DataImporter.parse_float('0.0') == 0.0, 'parse_float(0.0) 应返回 0.0'
assert DataImporter.parse_float('-0') == 0.0, 'parse_float(-0) 应返回 0.0'
assert DataImporter.parse_float('') is None, 'parse_float(空) 应返回 None'
assert DataImporter.parse_float('25.5') == 25.5, 'parse_float(25.5) 应返回 25.5'
print('parse_float 0值测试全部通过')

from core.chart_view import _CHINESE_FONT
print(f'中文字体选择: {_CHINESE_FONT or "未找到"}')

from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from ui.main_window import MainWindow
window = MainWindow()
print('主窗口创建成功')
db.close()
print('冒烟测试全部通过')
