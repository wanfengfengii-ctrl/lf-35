from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QSplitter, QGroupBox, QComboBox, QMessageBox, QStatusBar,
    QToolBar, QFileDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon

from database.db_manager import get_db
from core.anomaly_detector import AnomalyDetector, SEASONS, ANOMALY_TYPES
from core.chart_view import ChartViewWidget

from ui.drip_point_panel import DripPointPanel
from ui.data_import_panel import DataImportPanel
from ui.anomaly_panel import AnomalyPanel


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
        self.setWindowTitle("海蚀洞滴水监测数据管理系统")
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.drip_point_panel = DripPointPanel()
        self.data_import_panel = DataImportPanel()
        self.anomaly_panel = AnomalyPanel()

        self.tab_widget.addTab(self.drip_point_panel, "滴水点管理")
        self.tab_widget.addTab(self.data_import_panel, "数据导入")
        self.tab_widget.addTab(self.anomaly_panel, "异常检测")

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

        self.chart_view = ChartViewWidget()
        chart_control_layout.addWidget(self.chart_view, stretch=1)

        right_layout.addWidget(chart_control_group)
        self.splitter.addWidget(right_widget)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        self.splitter.setSizes([450, 950])

        main_layout.addWidget(self.splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status()

    def _init_toolbar(self):
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

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
        self.data_import_panel.data_imported.connect(self.refresh_all)
        self.anomaly_panel.anomalies_updated.connect(self._on_anomalies_updated)

    def _on_point_selected(self, point_id: int):
        self.current_point_id = point_id
        self.anomaly_panel.set_selected_point(point_id)
        self._on_refresh_chart()
        self._update_status()

    def _on_anomalies_updated(self):
        self.detector = self.anomaly_panel.get_detector()
        self._on_refresh_chart()

    def _on_chart_type_changed(self):
        self._on_refresh_chart()

    def _on_refresh_chart(self):
        if self.current_point_id is None:
            self.chart_view.clear()
            return

        chart_type = self.chart_type_combo.currentData()
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
            "<h3>海蚀洞滴水监测数据管理系统</h3>"
            "<p>版本: 1.0</p>"
            "<p>用于地质和洞穴研究团队整理海蚀洞内的滴水监测数据。</p>"
            "<p><b>主要功能:</b></p>"
            "<ul>"
            "<li>滴水点建档与管理</li>"
            "<li>滴水间隔、温度、湿度、盐度数据导入</li>"
            "<li>节律曲线可视化</li>"
            "<li>季节数据对比分析</li>"
            "<li>异常波动检测与风险等级判定</li>"
            "</ul>"
            "<p><b>技术栈:</b> Python + PySide6 + SQLite + Matplotlib</p>"
        )

    def refresh_all(self):
        self.drip_point_panel.refresh()
        self.data_import_panel.refresh_points()
        self.anomaly_panel.refresh_points()
        self.anomaly_panel.refresh()

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
        points = self.db.get_all_drip_points()
        total_data = sum(self.db.get_monitoring_data_count(p["id"]) for p in points)
        total_anomalies = len(self.db.get_anomaly_records())

        status_text = f"滴水点: {len(points)} | 监测数据: {total_data} 条 | 异常记录: {total_anomalies} 条"
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
