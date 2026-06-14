from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QSplitter, QGroupBox, QComboBox, QMessageBox, QStatusBar,
    QToolBar, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from database.db_manager import get_db
from core.anomaly_detector import AnomalyDetector, AdvancedAnomalyDetector, SEASONS, ANOMALY_TYPES
from core.chart_view import ChartViewWidget

from ui.cave_panel import CavePanel
from ui.drip_point_panel import DripPointPanel
from ui.device_panel import DevicePanel
from ui.data_import_panel import DataImportPanel
from ui.qc_panel import QCPanel
from ui.anomaly_panel import AnomalyPanel
from ui.dashboard_panel import DashboardPanel
from ui.handling_panel import HandlingPanel
from ui.statistics_panel import AdvancedStatisticsPanel
from ui.report_panel import ReportPanel
from ui.work_order_panel import WorkOrderPanel
from ui.user_panel import UserPanel
from ui.approval_panel import ApprovalPanel
from ui.route_panel import RoutePanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.current_point_id: Optional[int] = None
        self.detector = AnomalyDetector()
        self._init_ui()
        self._init_toolbar()
        self._connect_signals()
        self.refresh_all()

    def _init_ui(self):
        self.setWindowTitle("海蚀洞滴水监测智能运维闭环平台 v3.0")
        self.resize(1600, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()

        self.cave_panel = CavePanel()
        self.drip_point_panel = DripPointPanel()
        self.device_panel = DevicePanel()
        self.data_import_panel = DataImportPanel()
        self.qc_panel = QCPanel()
        self.anomaly_panel = AnomalyPanel()
        self.dashboard_panel = DashboardPanel()
        self.handling_panel = HandlingPanel()
        self.work_order_panel = WorkOrderPanel()
        self.statistics_panel = AdvancedStatisticsPanel()
        self.report_panel = ReportPanel()
        self.user_panel = UserPanel()
        self.approval_panel = ApprovalPanel()
        self.route_panel = RoutePanel()

        self.tab_widget.addTab(self.dashboard_panel, "🏠 预警看板")
        self.tab_widget.addTab(self.cave_panel, "📍 洞区管理")
        self.tab_widget.addTab(self.drip_point_panel, "💧 滴水点管理")
        self.tab_widget.addTab(self.device_panel, "📱 设备档案")
        self.tab_widget.addTab(self.data_import_panel, "📥 数据导入")
        self.tab_widget.addTab(self.qc_panel, "✅ 数据质控")
        self.tab_widget.addTab(self.anomaly_panel, "⚠️ 异常检测")
        self.tab_widget.addTab(self.work_order_panel, "📋 维护巡检")
        self.tab_widget.addTab(self.approval_panel, "🔍 工单审批")
        self.tab_widget.addTab(self.route_panel, "🗺️ 巡检路线")
        self.tab_widget.addTab(self.user_panel, "👥 用户管理")
        self.tab_widget.addTab(self.statistics_panel, "📊 统计分析")
        self.tab_widget.addTab(self.report_panel, "📄 报告导出")
        self.tab_widget.addTab(self.handling_panel, "📝 处理追踪")

        left_layout.addWidget(self.tab_widget)
        self.splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        chart_control_group = QGroupBox("图表视图")
        chart_control_layout = QVBoxLayout(chart_control_group)

        chart_btn_layout = QHBoxLayout()
        chart_btn_layout.addWidget(QLabel("图表类型:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItem("节律曲线", "rhythm")
        self.chart_type_combo.addItem("季节对比", "season")
        self.chart_type_combo.addItem("异常统计", "anomaly")
        self.chart_type_combo.addItem("多点位联合分析", "joint")
        self.chart_type_combo.addItem("时段统计图", "period_stats")
        self.chart_type_combo.currentIndexChanged.connect(self._on_chart_type_changed)
        chart_btn_layout.addWidget(self.chart_type_combo)

        self.refresh_chart_btn = QPushButton("刷新图表")
        self.refresh_chart_btn.clicked.connect(self._on_refresh_chart)
        chart_btn_layout.addWidget(self.refresh_chart_btn)

        self.export_btn = QPushButton("导出图片")
        self.export_btn.clicked.connect(self._on_export_chart)
        chart_btn_layout.addWidget(self.export_btn)

        chart_btn_layout.addStretch()
        chart_control_layout.addLayout(chart_btn_layout)

        self.joint_area_layout = QHBoxLayout()
        self.joint_area_layout.addWidget(QLabel("选择洞区:"))
        self.joint_area_combo = QComboBox()
        self.joint_area_combo.setMinimumWidth(200)
        self.joint_area_combo.currentIndexChanged.connect(self._on_refresh_chart)
        self.joint_area_layout.addWidget(self.joint_area_combo)
        self.joint_area_layout.addStretch()
        chart_control_layout.addLayout(self.joint_area_layout)

        self.chart_view = ChartViewWidget()
        chart_control_layout.addWidget(self.chart_view, stretch=1)

        right_layout.addWidget(chart_control_group)
        self.splitter.addWidget(right_widget)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([500, 1000])

        main_layout.addWidget(self.splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status()

        for i in range(self.joint_area_layout.count()):
            w = self.joint_area_layout.itemAt(i).widget()
            if w:
                w.hide()

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        refresh_action = QAction("全部刷新", self)
        refresh_action.triggered.connect(self.refresh_all)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        toolbar.addAction(exit_action)

        toolbar.addSeparator()

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        toolbar.addAction(about_action)

    def _connect_signals(self):
        self.drip_point_panel.point_selected.connect(self._on_point_selected)
        self.drip_point_panel.data_changed.connect(self.refresh_all)
        self.cave_panel.data_changed.connect(self.refresh_all)
        self.cave_panel.area_selected.connect(self._on_area_selected)
        self.device_panel.data_changed.connect(self.refresh_all)
        self.data_import_panel.data_imported.connect(self.refresh_all)
        self.qc_panel.data_changed.connect(self.refresh_all)
        self.anomaly_panel.anomalies_updated.connect(self._on_anomalies_updated)
        self.anomaly_panel.work_order_created.connect(self._on_work_order_created)
        self.dashboard_panel.data_changed.connect(self.refresh_all)
        self.handling_panel.data_changed.connect(self.refresh_all)
        self.work_order_panel.data_changed.connect(self.refresh_all)
        self.statistics_panel.data_changed.connect(self.refresh_all)
        self.report_panel.data_changed.connect(self.refresh_all)
        self.user_panel.data_changed.connect(self.refresh_all)
        self.approval_panel.data_changed.connect(self.refresh_all)
        self.route_panel.data_changed.connect(self.refresh_all)

    def _on_point_selected(self, point_id: int):
        self.current_point_id = point_id
        self.anomaly_panel.set_selected_point(point_id)
        self.qc_panel.set_selected_point(point_id)
        self._on_refresh_chart()
        self._update_status()

    def _on_area_selected(self, area_id: int):
        self._on_refresh_chart()

    def _on_anomalies_updated(self):
        self.detector = self.anomaly_panel.get_detector()
        self._on_refresh_chart()

    def _on_work_order_created(self, order_id: int):
        self.work_order_panel.refresh()
        wo_index = self.tab_widget.indexOf(self.work_order_panel)
        if wo_index >= 0:
            self.tab_widget.setCurrentIndex(wo_index)

    def _on_chart_type_changed(self):
        chart_type = self.chart_type_combo.currentData()
        if chart_type == "joint":
            for i in range(self.joint_area_layout.count()):
                w = self.joint_area_layout.itemAt(i).widget()
                if w:
                    w.show()
        else:
            for i in range(self.joint_area_layout.count()):
                w = self.joint_area_layout.itemAt(i).widget()
                if w:
                    w.hide()
        self._on_refresh_chart()

    def _on_refresh_chart(self):
        chart_type = self.chart_type_combo.currentData()

        if chart_type == "joint":
            self._plot_joint_analysis()
            return

        if chart_type == "period_stats":
            self._plot_period_stats()
            return

        if self.current_point_id is None:
            self.chart_view.clear()
            return

        data = self.db.get_monitoring_data(self.current_point_id)

        if chart_type == "rhythm":
            result = self.detector.detect_anomalies(data)
            self.chart_view.plot_rhythm(data, result)
        elif chart_type == "season":
            comparison = AnomalyDetector.compare_seasons(data)
            self.chart_view.plot_season(data, comparison)
        elif chart_type == "anomaly":
            result = self.detector.detect_anomalies(data)
            self.chart_view.plot_anomaly(result)

    def _plot_joint_analysis(self):
        area_id = self.joint_area_combo.currentData()
        if not area_id:
            self.chart_view.clear()
            return

        area = None
        for a in self.db.get_all_cave_areas():
            if a["id"] == area_id:
                area = a
                break

        if not area:
            self.chart_view.clear()
            return

        points = self.db.get_drip_points_by_area(area_id)
        if len(points) < 2:
            self.chart_view.clear()
            QMessageBox.information(self, "提示", f"洞区 [{area['code']} - {area['name']}] 下的滴水点数量不足2个，无法进行联合分析")
            return

        points_data = {}
        for p in points:
            data = self.db.get_monitoring_data(p["id"])
            if data:
                points_data[p["id"]] = {
                    "code": p["code"],
                    "name": p["name"],
                    "data": data
                }

        if len(points_data) < 2:
            self.chart_view.clear()
            return

        result = AdvancedAnomalyDetector.joint_analysis(
            area["id"], f"{area['code']} - {area['name']}", points_data
        )
        self.chart_view.plot_joint_analysis(result, points_data)

    def _plot_period_stats(self):
        if self.current_point_id is None:
            self.chart_view.clear()
            return
        from core.statistics import StatisticsAnalyzer
        day_stats = StatisticsAnalyzer.analyze_period(self.db, self.current_point_id, "day")
        self.chart_view.plot_period_statistics(day_stats)

    def _on_export_chart(self):
        if self.current_point_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个滴水点")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出图片", "chart.png",
            "PNG 图片 (*.png);;JPEG 图片 (*.jpg);;PDF 文件 (*.pdf)"
        )
        if file_path:
            try:
                self.chart_view.chart_canvas.fig.savefig(
                    file_path, dpi=300, bbox_inches="tight"
                )
                QMessageBox.information(self, "成功", f"图片已导出: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"导出失败: {str(e)}")

    def _show_about(self):
        QMessageBox.about(
            self, "关于",
            "<h3>海蚀洞滴水监测智能运维闭环平台</h3>"
            "<p>版本: 3.0</p>"
            "<p>用于地质和洞穴研究团队建立从异常识别到闭环归档的高效运维体系。</p>"
            "<p><b>核心功能:</b></p>"
            "<ul>"
            "<li>🔐 <b>多角色权限管理</b>：管理人员、研究人员、现场巡检人员三级权限</li>"
            "<li>📍 <b>洞区分层管理</b>：洞区 → 子区域 → 滴水点三级架构</li>"
            "<li>📱 <b>设备档案</b>：设备管理与校准记录追踪</li>"
            "<li>📥 <b>数据导入</b>：CSV 数据导入与导入前数据质控</li>"
            "<li>⚠️ <b>智能异常检测</b>：断档/持续偏高/偏低/突变/堵塞/渗流增强</li>"
            "<li>🏠 <b>预警看板</b>：实时异常与工单状态总览</li>"
            "<li>📋 <b>维护巡检工单</b>：工单创建、分配、状态流转</li>"
            "<li>🔍 <b>工单审批流程</b>：高优先级工单多级审批机制</li>"
            "<li>🗺️ <b>巡检路线安排</b>：自定义巡检路线与分配计划</li>"
            "<li>👥 <b>批量派单</b>：多选工单批量分配给巡检人员</li>"
            "<li>⏰ <b>复检提醒</b>：待复检工单自动提醒机制</li>"
            "<li>🔔 <b>超期自动催办</b>：超期工单自动发送提醒</li>"
            "<li>🚨 <b>工单升级机制</b>：超期未处理自动升级上报</li>"
            "<li>📊 <b>多维度统计分析</b>：按洞区、滴水点、责任人、异常类型、时间筛选</li>"
            "<li>📈 <b>处置效率分析</b>：响应时间、处理时长、完成率统计</li>"
            "<li>🔄 <b>重复异常点位</b>：高频异常点识别与历史追溯</li>"
            "<li>📄 <b>报告导出</b>：月度/异常/联合分析报告生成</li>"
            "</ul>"
            "<p><b>技术栈:</b> Python + PySide6 + SQLite + Matplotlib</p>"
        )

    def refresh_all(self):
        self.cave_panel.refresh_areas()
        self.drip_point_panel.refresh()
        self.device_panel.refresh()
        self.data_import_panel.refresh_points()
        self.qc_panel.refresh_points()
        self.qc_panel.refresh()
        self.anomaly_panel.refresh_points()
        self.anomaly_panel.refresh()
        self.dashboard_panel.refresh()
        self.handling_panel.refresh()
        self.work_order_panel.refresh()
        self.statistics_panel.refresh()
        self.report_panel.refresh()
        self.user_panel.refresh()
        self.approval_panel.refresh()
        self.route_panel.refresh()

        current_area_id = self.joint_area_combo.currentData()
        self.joint_area_combo.blockSignals(True)
        self.joint_area_combo.clear()
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.joint_area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        if current_area_id:
            idx = self.joint_area_combo.findData(current_area_id)
            if idx >= 0:
                self.joint_area_combo.setCurrentIndex(idx)
        self.joint_area_combo.blockSignals(False)

        if self.current_point_id:
            point = self.db.get_drip_point(self.current_point_id)
            if not point:
                self.current_point_id = None

        if self.current_point_id:
            self._on_refresh_chart()
        else:
            self.chart_view.clear()

        self._update_status()

    def _update_status(self):
        stats = self.db.get_overall_statistics()
        total_data = stats.get("data_count", 0)
        total_points = stats.get("point_count", 0)
        pending = stats.get("pending_anomalies", 0)

        wo_stats = self.db.get_work_order_stats()
        pending_wo = wo_stats.get("pending", 0)
        overdue_wo = wo_stats.get("overdue", 0)

        status_text = (
            f"洞区: {stats.get('area_count', 0)} | "
            f"子区域: {stats.get('zone_count', 0)} | "
            f"滴水点: {total_points} | "
            f"监测数据: {total_data} 条 | "
            f"设备: {stats.get('device_count', 0)} | "
            f"待处理异常: {pending} | "
            f"待处理工单: {pending_wo}"
        )

        if overdue_wo > 0:
            status_text += f" | ⚠超期工单: {overdue_wo}"

        if self.current_point_id:
            point = self.db.get_drip_point(self.current_point_id)
            if point:
                status_text += f" | 当前选中: {point['code']} - {point['name']}"

        self.status_bar.showMessage(status_text)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.close()
            event.accept()
        else:
            event.ignore()
