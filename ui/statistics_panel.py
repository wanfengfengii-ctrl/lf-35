from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QGroupBox, QComboBox, QDateEdit, QAbstractItemView, QSplitter,
    QTabWidget, QFrame, QScrollArea, QGridLayout, QProgressBar, QGraphicsDropShadowEffect,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QFont, QBrush, QPalette, QPainter
from PySide6.QtCharts import (
    QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis,
    QPieSeries, QPieSlice, QLineSeries, QDateTimeAxis
)
from PySide6.QtCore import QDateTime

from database.db_manager import get_db
from core.anomaly_detector import (
    WORK_ORDER_STATUS_COLORS, WORK_ORDER_STATUS_NAMES,
    ANOMALY_TYPE_NAMES, ANOMALY_TYPE_COLORS,
    ESCALATION_LEVEL_NAMES, ESCALATION_LEVEL_COLORS
)


class StatCard(QFrame):
    def __init__(self, title: str, value: str, subtitle: str = "", color: str = "#409EFF", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: white;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
            QLabel#title {{
                color: #606266;
                font-size: 13px;
                font-weight: 500;
            }}
            QLabel#value {{
                color: #303133;
                font-size: 28px;
                font-weight: bold;
            }}
            QLabel#subtitle {{
                color: #909399;
                font-size: 12px;
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("title")
        layout.addWidget(self.title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setObjectName("value")
        layout.addWidget(self.value_label)
        
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("subtitle")
            layout.addWidget(self.subtitle_label)


class AdvancedStatisticsPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        filter_group = QGroupBox("筛选条件")
        filter_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #EBEEF5;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 12px;
                font-weight: 600;
                color: #303133;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """)
        filter_layout = QGridLayout(filter_group)

        self.area_filter = QComboBox()
        self.area_filter.addItem("全部洞区", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_filter.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_filter.setMinimumWidth(180)
        filter_layout.addWidget(QLabel("洞区:"), 0, 0)
        filter_layout.addWidget(self.area_filter, 0, 1)

        self.point_filter = QComboBox()
        self.point_filter.addItem("全部滴水点", None)
        points = self.db.get_all_drip_points()
        for p in points:
            self.point_filter.addItem(f"{p['code']} - {p['name']}", p["id"])
        self.point_filter.setMinimumWidth(180)
        filter_layout.addWidget(QLabel("滴水点:"), 0, 2)
        filter_layout.addWidget(self.point_filter, 0, 3)

        self.assignee_filter = QComboBox()
        self.assignee_filter.addItem("全部责任人", None)
        users = self.db.get_all_users()
        for u in users:
            self.assignee_filter.addItem(u["real_name"], u["real_name"])
        self.assignee_filter.setMinimumWidth(150)
        filter_layout.addWidget(QLabel("责任人:"), 0, 4)
        filter_layout.addWidget(self.assignee_filter, 0, 5)

        self.type_filter = QComboBox()
        self.type_filter.addItem("全部异常类型", None)
        for t, name in ANOMALY_TYPE_NAMES.items():
            self.type_filter.addItem(name, t)
        self.type_filter.setMinimumWidth(150)
        filter_layout.addWidget(QLabel("异常类型:"), 1, 0)
        filter_layout.addWidget(self.type_filter, 1, 1)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(QLabel("开始日期:"), 1, 2)
        filter_layout.addWidget(self.start_date, 1, 3)

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("结束日期:"), 1, 4)
        filter_layout.addWidget(self.end_date, 1, 5)

        btn_layout = QHBoxLayout()
        self.query_btn = QPushButton("查询")
        self.query_btn.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        self.query_btn.clicked.connect(self.refresh)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #f5f7fa;
                color: #606266;
                border: 1px solid #dcdfe6;
                padding: 8px 24px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ecf5ff;
                color: #409EFF;
                border-color: #c6e2ff;
            }
        """)
        self.reset_btn.clicked.connect(self._on_reset)

        self.export_btn = QPushButton("导出")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #67C23A;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #85ce61;
            }
        """)
        self.export_btn.clicked.connect(self._on_export)

        btn_layout.addStretch()
        btn_layout.addWidget(self.query_btn)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addWidget(self.export_btn)
        filter_layout.addLayout(btn_layout, 2, 0, 1, 6)

        main_layout.addWidget(filter_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.stat_cards: Dict[str, StatCard] = {}
        
        self.stat_cards["total"] = StatCard("工单总数", "0", "选定时间段内", "#409EFF")
        self.stat_cards["closed"] = StatCard("已闭环", "0", "已完成且复检通过", "#67C23A")
        self.stat_cards["pending"] = StatCard("待处理", "0", "进行中工单", "#E6A23C")
        self.stat_cards["overdue"] = StatCard("超期工单", "0", "未按时完成", "#F56C6C")
        self.stat_cards["avg_duration"] = StatCard("平均处置时长", "0 小时", "从派单到闭环", "#909399")
        self.stat_cards["repeated"] = StatCard("重复异常点位", "0", "出现3次以上", "#F56C6C")
        
        for card in self.stat_cards.values():
            cards_row.addWidget(card)
        content_layout.addLayout(cards_row)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #EBEEF5;
                border-radius: 6px;
                top: -1px;
            }
            QTabBar::tab {
                background: #f5f7fa;
                border: 1px solid #EBEEF5;
                border-bottom: none;
                padding: 8px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: #606266;
            }
            QTabBar::tab:selected {
                background: white;
                color: #409EFF;
                font-weight: 600;
            }
        """)

        self.tabs.addTab(self._create_efficiency_tab(), "处置效率分析")
        self.tabs.addTab(self._create_repeated_tab(), "重复异常点位")
        self.tabs.addTab(self._create_history_tab(), "历史维护记录")
        self.tabs.addTab(self._create_anomaly_tab(), "异常类型分布")
        
        content_layout.addWidget(self.tabs)

        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)

    def _create_efficiency_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        chart_splitter = QSplitter(Qt.Horizontal)
        
        chart1_widget = QWidget()
        chart1_layout = QVBoxLayout(chart1_widget)
        chart1_layout.addWidget(QLabel("按状态分布"))
        self.status_chart_view = QChartView()
        self.status_chart_view.setRenderHint(QPainter.Antialiasing, True)
        self.status_chart_view.setMinimumHeight(300)
        chart1_layout.addWidget(self.status_chart_view)
        chart_splitter.addWidget(chart1_widget)
        
        chart2_widget = QWidget()
        chart2_layout = QVBoxLayout(chart2_widget)
        chart2_layout.addWidget(QLabel("处置时长趋势（天）"))
        self.trend_chart_view = QChartView()
        self.trend_chart_view.setRenderHint(QPainter.Antialiasing, True)
        self.trend_chart_view.setMinimumHeight(300)
        chart2_layout.addWidget(self.trend_chart_view)
        chart_splitter.addWidget(chart2_widget)
        
        chart_splitter.setStretchFactor(0, 1)
        chart_splitter.setStretchFactor(1, 1)
        layout.addWidget(chart_splitter)
        
        table_group = QGroupBox("人员处置效率排行")
        table_layout = QVBoxLayout(table_group)
        self.efficiency_table = QTableWidget()
        self.efficiency_table.setColumnCount(5)
        self.efficiency_table.setHorizontalHeaderLabels([
            "排名", "责任人", "完成工单", "平均耗时(小时)", "按期完成率"
        ])
        self.efficiency_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.efficiency_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.efficiency_table.setAlternatingRowColors(True)
        self.efficiency_table.setStyleSheet("alternate-background-color: #f5f7fa;")
        table_layout.addWidget(self.efficiency_table)
        layout.addWidget(table_group)
        
        return widget

    def _create_repeated_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        chart_splitter = QSplitter(Qt.Horizontal)
        
        chart1_widget = QWidget()
        chart1_layout = QVBoxLayout(chart1_widget)
        chart1_layout.addWidget(QLabel("异常点位频次 Top 10"))
        self.repeated_chart_view = QChartView()
        self.repeated_chart_view.setRenderHint(QPainter.Antialiasing, True)
        self.repeated_chart_view.setMinimumHeight(300)
        chart1_layout.addWidget(self.repeated_chart_view)
        chart_splitter.addWidget(chart1_widget)
        
        chart2_widget = QWidget()
        chart2_layout = QVBoxLayout(chart2_widget)
        chart2_layout.addWidget(QLabel("按洞区分布"))
        self.area_chart_view = QChartView()
        self.area_chart_view.setRenderHint(QPainter.Antialiasing, True)
        self.area_chart_view.setMinimumHeight(300)
        chart2_layout.addWidget(self.area_chart_view)
        chart_splitter.addWidget(chart2_widget)
        
        chart_splitter.setStretchFactor(0, 1)
        chart_splitter.setStretchFactor(1, 1)
        layout.addWidget(chart_splitter)
        
        table_group = QGroupBox("重复异常点位明细")
        table_layout = QVBoxLayout(table_group)
        self.repeated_table = QTableWidget()
        self.repeated_table.setColumnCount(6)
        self.repeated_table.setHorizontalHeaderLabels([
            "滴水点", "点位名称", "异常次数", "最近异常", "主要异常类型", "所属洞区"
        ])
        self.repeated_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.repeated_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.repeated_table.setAlternatingRowColors(True)
        self.repeated_table.setStyleSheet("alternate-background-color: #f5f7fa;")
        table_layout.addWidget(self.repeated_table)
        layout.addWidget(table_group)
        
        return widget

    def _create_history_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "工单编号", "异常类型", "滴水点", "责任人", "创建时间",
            "完成时间", "处理耗时", "状态"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("alternate-background-color: #f5f7fa;")
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.history_table)
        
        return widget

    def _create_anomaly_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        
        chart_splitter = QSplitter(Qt.Horizontal)
        
        chart1_widget = QWidget()
        chart1_layout = QVBoxLayout(chart1_widget)
        chart1_layout.addWidget(QLabel("异常类型占比"))
        self.anomaly_pie_view = QChartView()
        self.anomaly_pie_view.setRenderHint(QPainter.Antialiasing, True)
        self.anomaly_pie_view.setMinimumHeight(300)
        chart1_layout.addWidget(self.anomaly_pie_view)
        chart_splitter.addWidget(chart1_widget)
        
        chart2_widget = QWidget()
        chart2_layout = QVBoxLayout(chart2_widget)
        chart2_layout.addWidget(QLabel("各类型工单数量对比"))
        self.anomaly_bar_view = QChartView()
        self.anomaly_bar_view.setRenderHint(QPainter.Antialiasing, True)
        self.anomaly_bar_view.setMinimumHeight(300)
        chart2_layout.addWidget(self.anomaly_bar_view)
        chart_splitter.addWidget(chart2_widget)
        
        chart_splitter.setStretchFactor(0, 1)
        chart_splitter.setStretchFactor(1, 1)
        layout.addWidget(chart_splitter)
        
        table_group = QGroupBox("各类型详细统计")
        table_layout = QVBoxLayout(table_group)
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(6)
        self.anomaly_table.setHorizontalHeaderLabels([
            "异常类型", "工单总数", "已闭环", "进行中", "超期", "闭环率"
        ])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.anomaly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.anomaly_table.setAlternatingRowColors(True)
        self.anomaly_table.setStyleSheet("alternate-background-color: #f5f7fa;")
        table_layout.addWidget(self.anomaly_table)
        layout.addWidget(table_group)
        
        return widget

    def _on_reset(self):
        self.area_filter.setCurrentIndex(0)
        self.point_filter.setCurrentIndex(0)
        self.assignee_filter.setCurrentIndex(0)
        self.type_filter.setCurrentIndex(0)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.end_date.setDate(QDate.currentDate())
        self.refresh()

    def _on_export(self):
        QMessageBox.information(self, "提示", "数据导出功能开发中...")

    def refresh(self):
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")
        area_id = self.area_filter.currentData()
        assignee = self.assignee_filter.currentData()
        anomaly_type = self.type_filter.currentData()
        drip_point_id = self.point_filter.currentData()

        stats = self.db.get_advanced_statistics(
            start_date=start_date,
            end_date=end_date,
            area_id=area_id,
            assignee=assignee,
            anomaly_type=anomaly_type,
            drip_point_id=drip_point_id
        )

        self._update_stat_cards(stats)
        self._update_status_chart(stats.get("by_status", {}))
        self._update_trend_chart(stats.get("trend", []))
        self._update_efficiency_table(stats.get("by_assignee", []))
        self._update_repeated_chart(stats.get("repeated_points", []))
        self._update_area_chart(stats.get("by_area", []))
        self._update_repeated_table(stats.get("repeated_points", []))
        self._update_history_table(stats.get("history", []))
        self._update_anomaly_charts(stats.get("by_anomaly_type", []))
        self._update_anomaly_table(stats.get("by_anomaly_type", []))

    def _update_stat_cards(self, stats: Dict):
        summary = stats.get("summary", {})
        self.stat_cards["total"].value_label.setText(str(summary.get("total_count", 0)))
        self.stat_cards["closed"].value_label.setText(str(summary.get("closed_count", 0)))
        self.stat_cards["pending"].value_label.setText(str(summary.get("pending_count", 0)))
        self.stat_cards["overdue"].value_label.setText(str(summary.get("overdue_count", 0)))
        
        avg_hours = summary.get("avg_duration_hours", 0)
        if avg_hours >= 24:
            days = avg_hours / 24
            self.stat_cards["avg_duration"].value_label.setText(f"{days:.1f} 天")
        else:
            self.stat_cards["avg_duration"].value_label.setText(f"{avg_hours:.1f} 小时")
        
        self.stat_cards["repeated"].value_label.setText(str(summary.get("repeated_point_count", 0)))

    def _update_status_chart(self, by_status: Dict):
        series = QPieSeries()
        series.setHoleSize(0.35)
        
        for status, count in by_status.items():
            if count > 0:
                name = WORK_ORDER_STATUS_NAMES.get(status, status)
                color = WORK_ORDER_STATUS_COLORS.get(status, "#909399")
                slice_ = QPieSlice(name, count)
                slice_.setColor(QColor(color))
                slice_.setLabelVisible(True)
                slice_.setLabelColor(QColor("#303133"))
                series.append(slice_)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("工单状态分布")
        chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setBackgroundVisible(False)
        self.status_chart_view.setChart(chart)

    def _update_trend_chart(self, trend: List[Dict]):
        series = QLineSeries()
        series.setName("工单数量")
        
        for i, item in enumerate(trend):
            date_str = item.get("date", "")
            count = item.get("count", 0)
            if date_str:
                dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
                series.append(dt.toMSecsSinceEpoch(), count)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("工单趋势")
        chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM-dd")
        axis_x.setTitleText("日期")
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("工单数量")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        self.trend_chart_view.setChart(chart)

    def _update_efficiency_table(self, data: List[Dict]):
        data_sorted = sorted(data, key=lambda x: x.get("completed_count", 0), reverse=True)
        self.efficiency_table.setRowCount(len(data_sorted))
        
        for row, item in enumerate(data_sorted):
            self.efficiency_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self.efficiency_table.setItem(row, 1, QTableWidgetItem(item.get("assignee", "-")))
            self.efficiency_table.setItem(row, 2, QTableWidgetItem(str(item.get("completed_count", 0))))
            self.efficiency_table.setItem(row, 3, QTableWidgetItem(f"{item.get('avg_duration', 0):.1f}"))
            
            total = item.get("total_count", 0)
            on_time = item.get("on_time_count", 0)
            rate = (on_time / total * 100) if total > 0 else 0
            
            rate_item = QTableWidgetItem(f"{rate:.1f}%")
            if rate >= 90:
                rate_item.setForeground(QBrush(QColor("#67C23A")))
            elif rate >= 70:
                rate_item.setForeground(QBrush(QColor("#E6A23C")))
            else:
                rate_item.setForeground(QBrush(QColor("#F56C6C")))
            self.efficiency_table.setItem(row, 4, rate_item)
            
            for col in range(5):
                it = self.efficiency_table.item(row, col)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)

    def _update_repeated_chart(self, points: List[Dict]):
        top_points = sorted(points, key=lambda x: x.get("count", 0), reverse=True)[:10]
        
        series = QBarSeries()
        bar_set = QBarSet("异常次数")
        categories = []
        
        for p in top_points:
            bar_set.append(p.get("count", 0))
            categories.append(p.get("code", p.get("name", "")))
        
        series.append(bar_set)
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("异常点位频次 Top 10")
        chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-30)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("次数")
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)
        
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        self.repeated_chart_view.setChart(chart)

    def _update_area_chart(self, areas: List[Dict]):
        series = QPieSeries()
        
        for a in areas:
            name = f"{a.get('code', '')} - {a.get('name', '')}"
            count = a.get("count", 0)
            if count > 0:
                series.append(name, count)
        
        if series.count() > 0:
            for i, slice_ in enumerate(series.slices()):
                colors = ["#409EFF", "#67C23A", "#E6A23C", "#F56C6C", "#909399", "#9b59b6"]
                slice_.setColor(QColor(colors[i % len(colors)]))
                slice_.setLabelVisible(True)
                slice_.setLabelColor(QColor("#303133"))
        
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("按洞区分布")
        chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setBackgroundVisible(False)
        self.area_chart_view.setChart(chart)

    def _update_repeated_table(self, points: List[Dict]):
        sorted_points = sorted(points, key=lambda x: x.get("count", 0), reverse=True)
        self.repeated_table.setRowCount(len(sorted_points))
        
        for row, p in enumerate(sorted_points):
            self.repeated_table.setItem(row, 0, QTableWidgetItem(p.get("code", "-")))
            self.repeated_table.setItem(row, 1, QTableWidgetItem(p.get("name", "-")))
            
            count = p.get("count", 0)
            count_item = QTableWidgetItem(str(count))
            if count >= 5:
                count_item.setForeground(QBrush(QColor("#F56C6C")))
                count_item.setFont(QFont("", -1, QFont.Bold))
            elif count >= 3:
                count_item.setForeground(QBrush(QColor("#E6A23C")))
            self.repeated_table.setItem(row, 2, count_item)
            
            self.repeated_table.setItem(row, 3, QTableWidgetItem(p.get("last_time", "-")))
            anomaly_type = p.get("top_anomaly_type", "")
            self.repeated_table.setItem(row, 4, QTableWidgetItem(
                ANOMALY_TYPE_NAMES.get(anomaly_type, anomaly_type) if anomaly_type else "-"
            ))
            self.repeated_table.setItem(row, 5, QTableWidgetItem(
                f"{p.get('area_code', '')} - {p.get('area_name', '')}" if p.get("area_code") else "-"
            ))
            
            for col in range(6):
                it = self.repeated_table.item(row, col)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)

    def _update_history_table(self, history: List[Dict]):
        self.history_table.setRowCount(len(history))
        
        for row, item in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(item.get("work_order_code", "-")))
            
            anomaly_type = item.get("anomaly_type", "")
            self.history_table.setItem(row, 1, QTableWidgetItem(
                ANOMALY_TYPE_NAMES.get(anomaly_type, anomaly_type) if anomaly_type else "-"
            ))
            self.history_table.setItem(row, 2, QTableWidgetItem(
                f"{item.get('drip_point_code', '')} - {item.get('drip_point_name', '')}" if item.get("drip_point_code") else "-"
            ))
            self.history_table.setItem(row, 3, QTableWidgetItem(item.get("assignee", "-")))
            self.history_table.setItem(row, 4, QTableWidgetItem(item.get("created_at", "-")))
            self.history_table.setItem(row, 5, QTableWidgetItem(item.get("closed_at", "-") or "-"))
            
            duration = item.get("duration_hours", 0)
            if duration >= 0:
                if duration >= 24:
                    self.history_table.setItem(row, 6, QTableWidgetItem(f"{duration/24:.1f} 天"))
                else:
                    self.history_table.setItem(row, 6, QTableWidgetItem(f"{duration:.1f} 小时"))
            else:
                self.history_table.setItem(row, 6, QTableWidgetItem("-"))
            
            status = item.get("status", "")
            status_item = QTableWidgetItem(
                WORK_ORDER_STATUS_NAMES.get(status, status) if status else "-"
            )
            status_item.setForeground(QColor(WORK_ORDER_STATUS_COLORS.get(status, "#000")))
            self.history_table.setItem(row, 7, status_item)
            
            for col in range(8):
                it = self.history_table.item(row, col)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)

    def _update_anomaly_charts(self, anomaly_types: List[Dict]):
        pie_series = QPieSeries()
        bar_series = QBarSeries()
        categories = []
        bar_set = QBarSet("工单数量")
        
        for i, item in enumerate(anomaly_types):
            type_val = item.get("anomaly_type", "")
            count = item.get("total_count", 0)
            name = ANOMALY_TYPE_NAMES.get(type_val, type_val)
            color = ANOMALY_TYPE_COLORS.get(type_val, f"hsl({i * 60}, 70%, 50%)")
            
            if count > 0:
                slice_ = QPieSlice(name, count)
                slice_.setColor(QColor(color))
                slice_.setLabelVisible(True)
                slice_.setLabelColor(QColor("#303133"))
                pie_series.append(slice_)
            
            bar_set.append(count)
            categories.append(name)
        
        bar_series.append(bar_set)
        
        pie_chart = QChart()
        pie_chart.addSeries(pie_series)
        pie_chart.setTitle("异常类型占比")
        pie_chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        pie_chart.legend().setAlignment(Qt.AlignBottom)
        pie_chart.setBackgroundVisible(False)
        self.anomaly_pie_view.setChart(pie_chart)
        
        bar_chart = QChart()
        bar_chart.addSeries(bar_series)
        bar_chart.setTitle("各类型工单数量")
        bar_chart.setTitleFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        bar_chart.setAnimationOptions(QChart.SeriesAnimations)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-30)
        bar_chart.addAxis(axis_x, Qt.AlignBottom)
        bar_series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setTitleText("数量")
        bar_chart.addAxis(axis_y, Qt.AlignLeft)
        bar_series.attachAxis(axis_y)
        
        bar_chart.legend().setVisible(False)
        bar_chart.setBackgroundVisible(False)
        self.anomaly_bar_view.setChart(bar_chart)

    def _update_anomaly_table(self, anomaly_types: List[Dict]):
        self.anomaly_table.setRowCount(len(anomaly_types))
        
        for row, item in enumerate(anomaly_types):
            type_val = item.get("anomaly_type", "")
            name = ANOMALY_TYPE_NAMES.get(type_val, type_val)
            type_item = QTableWidgetItem(name)
            type_item.setForeground(QColor(ANOMALY_TYPE_COLORS.get(type_val, "#000")))
            type_item.setFont(QFont("", -1, QFont.Bold))
            self.anomaly_table.setItem(row, 0, type_item)
            
            total = item.get("total_count", 0)
            closed = item.get("closed_count", 0)
            pending = item.get("pending_count", 0)
            overdue = item.get("overdue_count", 0)
            
            self.anomaly_table.setItem(row, 1, QTableWidgetItem(str(total)))
            self.anomaly_table.setItem(row, 2, QTableWidgetItem(str(closed)))
            self.anomaly_table.setItem(row, 3, QTableWidgetItem(str(pending)))
            
            overdue_item = QTableWidgetItem(str(overdue))
            if overdue > 0:
                overdue_item.setForeground(QBrush(QColor("#F56C6C")))
            self.anomaly_table.setItem(row, 4, overdue_item)
            
            rate = (closed / total * 100) if total > 0 else 0
            rate_item = QTableWidgetItem(f"{rate:.1f}%")
            if rate >= 90:
                rate_item.setForeground(QBrush(QColor("#67C23A")))
            elif rate >= 70:
                rate_item.setForeground(QBrush(QColor("#E6A23C")))
            else:
                rate_item.setForeground(QBrush(QColor("#F56C6C")))
            self.anomaly_table.setItem(row, 5, rate_item)
            
            for col in range(6):
                it = self.anomaly_table.item(row, col)
                if it:
                    it.setTextAlignment(Qt.AlignCenter)
