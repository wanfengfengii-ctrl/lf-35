import sys
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)

from ui.main_window import MainWindow
window = MainWindow()
print('主窗口创建成功')
print('标题:', window.windowTitle())
print('标签页数量:', window.tab_widget.count())
print('标签页:')
for i in range(window.tab_widget.count()):
    print(f'  {i}. {window.tab_widget.tabText(i)}')

print()
print('面板测试:')
panels = [
    ('dashboard_panel', window.dashboard_panel),
    ('work_order_panel', window.work_order_panel),
    ('approval_panel', window.approval_panel),
    ('route_panel', window.route_panel),
    ('user_panel', window.user_panel),
    ('statistics_panel', window.statistics_panel),
    ('anomaly_panel', window.anomaly_panel),
    ('cave_panel', window.cave_panel),
    ('drip_point_panel', window.drip_point_panel),
    ('device_panel', window.device_panel),
    ('handling_panel', window.handling_panel),
    ('report_panel', window.report_panel),
    ('qc_panel', window.qc_panel),
    ('data_import_panel', window.data_import_panel),
]
for name, panel in panels:
    try:
        print(f'  {name}: OK')
    except Exception as e:
        print(f'  {name}: ERROR - {e}')

print()
print('数据库测试:')
db = window.db
print(f'  洞区数: {len(db.get_all_cave_areas())}')
print(f'  滴水点数: {len(db.get_all_drip_points())}')
print(f'  工单总数: {len(db.get_work_orders())}')
print(f'  用户数: {len(db.get_all_users())}')
print(f'  巡检路线数: {len(db.get_all_inspection_routes())}')
print(f'  待审批数: {len(db.get_pending_approvals())}')
print(f'  超期工单数: {len(db.get_overdue_orders())}')

print()
print('测试通过!')
window.close()
app.quit()
