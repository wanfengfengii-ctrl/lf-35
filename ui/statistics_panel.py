from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QLabel, QGroupBox, QAbstractItemView, QComboBox,
    QDateEdit, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor

from database.db_manager import get_db
from core.statistics import StatisticsAnalyzer, PeriodStatistics, MultiPointComparison
from core.anomaly_detector import ANOMALY_TYPES


class StatisticsPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._period_stats: List[PeriodStatistics] = []
        self._comparison: Optional[MultiPointComparison] = None
        self._init_ui()
        self._load_point_options()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        filter_group = QGroupBox("统计条件")
        filter_layout = QVBoxLayout(filter_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("区域:"))
        self.area_combo = QComboBox()
        self.area_combo.addItem("全部区域", None)
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        row1.addWidget(self.area_combo)

        row1.addWidget(QLabel("滴水点:"))
        self.point_combo = QComboBox()
        self.point_combo.addItem("全部滴水点", None)
        row1.addWidget(self.point_combo)

        row1.addWidget(QLabel("粒度:"))
        self.period_combo = QComboBox()
        self.period_combo.addItems(["日", "周", "月"])
        self.period_combo.setCurrentIndex(0)
        row1.addWidget(self.period_combo)
        row1.addStretch()
        filter_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        row2.addWidget(self.start_date)

        row2.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        row2.addWidget(self.end_date)

        self.run_btn = QPushButton("执行统计")
        self.run_btn.clicked.connect(self._on_run_statistics)
        row2.addWidget(self.run_btn)

        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self._on_export)
        self.export_btn.setEnabled(False)
        row2.addWidget(self.export_btn)
        row2.addStretch()
        filter_layout.addLayout(row2)

        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Vertical)

        self.tabs = QTabWidget()

        period_tab = QWidget()
        period_layout = QVBoxLayout(period_tab)
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(11)
        self.stats_table.setHorizontalHeaderLabels([
            "时段", "数据量", "平均间隔(s)", "最小间隔(s)", "最大间隔(s)",
            "标准差(s)", "变异系数(%)", "平均温度(℃)", "平均湿度(%)",
            "平均盐度(‰)", "异常数"
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.stats_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        period_layout.addWidget(self.stats_table)
        self.tabs.addTab(period_tab, "时段统计")

        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        summary_layout.addWidget(self.summary_table)

        self.seasonal_group = QGroupBox("季节指数")
        seasonal_layout = QVBoxLayout(self.seasonal_group)
        self.seasonal_table = QTableWidget()
        self.seasonal_table.setColumnCount(4)
        self.seasonal_table.setHorizontalHeaderLabels(["季节", "数据量", "均值(s)", "季节指数(%)"])
        self.seasonal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.seasonal_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        seasonal_layout.addWidget(self.seasonal_table)
        summary_layout.addWidget(self.seasonal_group)
        self.tabs.addTab(summary_tab, "汇总统计")

        comparison_tab = QWidget()
        comparison_layout = QVBoxLayout(comparison_tab)
        self.comparison_stats_table = QTableWidget()
        self.comparison_stats_table.setColumnCount(8)
        self.comparison_stats_table.setHorizontalHeaderLabels([
            "滴水点", "数据量", "平均间隔(s)", "最小间隔(s)", "最大间隔(s)",
            "标准差(s)", "变异系数(%)", "趋势"
        ])
        self.comparison_stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comparison_stats_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        comparison_layout.addWidget(QLabel("各点综合统计:"))
        comparison_layout.addWidget(self.comparison_stats_table)

        comparison_layout.addWidget(QLabel("相关性矩阵:"))
        self.correlation_table = QTableWidget()
        self.correlation_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.correlation_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.correlation_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        comparison_layout.addWidget(self.correlation_table)
        self.tabs.addTab(comparison_tab, "多点对比")

        splitter.addWidget(self.tabs)

        self.summary_label = QLabel('请选择条件后点击"执行统计"')
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("padding: 6px; background: #f5f5f5; border-radius: 4px;")
        splitter.addWidget(self.summary_label)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _load_point_options(self):
        self.area_combo.blockSignals(True)
        self.area_combo.clear()
        self.area_combo.addItem("全部区域", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_combo.blockSignals(False)

        self._refresh_point_combo()

    def _refresh_point_combo(self):
        self.point_combo.clear()
        self.point_combo.addItem("全部滴水点", None)
        area_id = self.area_combo.currentData()
        if area_id:
            points = self.db.get_drip_points_by_area(area_id)
        else:
            points = self.db.get_all_drip_points()
        for p in points:
            self.point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])

    def _on_area_changed(self):
        self._refresh_point_combo()

    def _get_selected_point_ids(self) -> List[int]:
        point_id = self.point_combo.currentData()
        if point_id is not None:
            return [point_id]
        area_id = self.area_combo.currentData()
        if area_id:
            points = self.db.get_drip_points_by_area(area_id)
            return [p["id"] for p in points]
        points = self.db.get_all_drip_points()
        return [p["id"] for p in points]

    def _on_run_statistics(self):
        point_id = self.point_combo.currentData()
        point_ids = self._get_selected_point_ids()

        if not point_ids:
            QMessageBox.warning(self, "提示", "没有可统计的滴水点")
            return

        period_map = {"日": "day", "周": "week", "月": "month"}
        period = period_map.get(self.period_combo.currentText(), "day")
        start_time = self.start_date.date().toString("yyyy-MM-dd")
        end_time = self.end_date.date().toString("yyyy-MM-dd")

        if point_id is not None:
            self._run_single_point(point_id, period, start_time, end_time)
        else:
            self._run_multi_point(point_ids, period, start_time, end_time)

        self.export_btn.setEnabled(True)
        self.data_changed.emit()

    def _run_single_point(self, point_id: int, period: str, start_time: str, end_time: str):
        self._period_stats = StatisticsAnalyzer.analyze_period(
            self.db, point_id, period, start_time, end_time
        )
        self._populate_period_table(self._period_stats)

        summary = StatisticsAnalyzer.get_summary_statistics(self.db, point_id)
        self._populate_summary_table(summary)

        seasonal = StatisticsAnalyzer.calculate_seasonal_index(self.db, point_id)
        self._populate_seasonal_table(seasonal)

        self.tabs.setTabEnabled(2, False)
        self.tabs.setCurrentIndex(0)

        self._update_summary_label_single(point_id, self._period_stats, summary)

    def _run_multi_point(self, point_ids: List[int], period: str, start_time: str, end_time: str):
        if len(point_ids) == 1:
            self._run_single_point(point_ids[0], period, start_time, end_time)
            return

        first_point = point_ids[0]
        self._period_stats = StatisticsAnalyzer.analyze_period(
            self.db, first_point, period, start_time, end_time
        )
        self._populate_period_table(self._period_stats)

        summary = StatisticsAnalyzer.get_summary_statistics(self.db, first_point)
        self._populate_summary_table(summary)

        seasonal = StatisticsAnalyzer.calculate_seasonal_index(self.db, first_point)
        self._populate_seasonal_table(seasonal)

        self._comparison = StatisticsAnalyzer.compare_multiple_points(
            self.db, point_ids, start_time, end_time
        )
        self._populate_comparison_tables(self._comparison)

        self.tabs.setTabEnabled(2, True)
        self.tabs.setCurrentIndex(2)

        self._update_summary_label_multi(self._comparison)

    def _populate_period_table(self, stats: List[PeriodStatistics]):
        self.stats_table.setRowCount(len(stats))
        for row, s in enumerate(stats):
            self._set_table_item(self.stats_table, row, 0, s.period)
            self._set_table_item(self.stats_table, row, 1, str(s.data_count))
            self._set_table_item(self.stats_table, row, 2, f"{s.avg_interval:.2f}")
            self._set_table_item(self.stats_table, row, 3, f"{s.min_interval:.2f}")
            self._set_table_item(self.stats_table, row, 4, f"{s.max_interval:.2f}")
            self._set_table_item(self.stats_table, row, 5, f"{s.std_interval:.2f}")

            cv_item = QTableWidgetItem(f"{s.cv_interval:.2f}")
            if s.cv_interval > 50:
                cv_item.setForeground(QColor("#d62728"))
            elif s.cv_interval > 30:
                cv_item.setForeground(QColor("#ff7f0e"))
            cv_item.setTextAlignment(Qt.AlignCenter)
            self.stats_table.setItem(row, 6, cv_item)

            self._set_table_item(self.stats_table, row, 7,
                                 f"{s.avg_temperature:.2f}" if s.avg_temperature is not None else "-")
            self._set_table_item(self.stats_table, row, 8,
                                 f"{s.avg_humidity:.2f}" if s.avg_humidity is not None else "-")
            self._set_table_item(self.stats_table, row, 9,
                                 f"{s.avg_salinity:.2f}" if s.avg_salinity is not None else "-")
            self._set_table_item(self.stats_table, row, 10, str(s.anomaly_count))

    def _populate_summary_table(self, summary: Dict):
        if not summary:
            self.summary_table.setRowCount(0)
            return

        labels = {
            "total_records": "总记录数",
            "date_range": "数据时间范围",
            "interval_mean": "间隔均值(s)",
            "interval_median": "间隔中位数(s)",
            "interval_std": "间隔标准差(s)",
            "interval_cv": "变异系数(%)",
            "interval_min": "间隔最小值(s)",
            "interval_max": "间隔最大值(s)",
            "trend": "趋势",
            "data_quality": "数据质量",
        }

        rows = []
        for key, label in labels.items():
            val = summary.get(key, "-")
            if isinstance(val, float):
                val = f"{val:.2f}"
            rows.append((label, str(val)))

        self.summary_table.setRowCount(len(rows))
        for row, (label, value) in enumerate(rows):
            self._set_table_item(self.summary_table, row, 0, label)
            self._set_table_item(self.summary_table, row, 1, value)

    def _populate_seasonal_table(self, seasonal: Dict[str, Dict]):
        if not seasonal:
            self.seasonal_table.setRowCount(0)
            return

        rows = list(seasonal.items())
        self.seasonal_table.setRowCount(len(rows))
        for row, (season, data) in enumerate(rows):
            self._set_table_item(self.seasonal_table, row, 0, season)
            self._set_table_item(self.seasonal_table, row, 1, str(data.get("count", 0)))
            self._set_table_item(self.seasonal_table, row, 2, f"{data.get('mean', 0):.2f}")
            self._set_table_item(self.seasonal_table, row, 3, f"{data.get('index', 0):.2f}")

    def _populate_comparison_tables(self, comp: MultiPointComparison):
        self.comparison_stats_table.setRowCount(len(comp.point_ids))
        for row, pid in enumerate(comp.point_ids):
            code = comp.point_codes.get(pid, str(pid))
            self._set_table_item(self.comparison_stats_table, row, 0, code)

            stats = comp.overall_stats.get(pid)
            if stats:
                self._set_table_item(self.comparison_stats_table, row, 1, str(stats.data_count))
                self._set_table_item(self.comparison_stats_table, row, 2, f"{stats.avg_interval:.2f}")
                self._set_table_item(self.comparison_stats_table, row, 3, f"{stats.min_interval:.2f}")
                self._set_table_item(self.comparison_stats_table, row, 4, f"{stats.max_interval:.2f}")
                self._set_table_item(self.comparison_stats_table, row, 5, f"{stats.std_interval:.2f}")
                self._set_table_item(self.comparison_stats_table, row, 6, f"{stats.cv_interval:.2f}")
            else:
                for col in range(1, 7):
                    self._set_table_item(self.comparison_stats_table, row, col, "-")

            trend = comp.trends.get(pid, "-")
            trend_item = QTableWidgetItem(trend)
            trend_colors = {
                "显著上升": QColor("#d62728"),
                "上升": QColor("#ff7f0e"),
                "下降": QColor("#1f77b4"),
                "显著下降": QColor("#2ca02c"),
            }
            color = trend_colors.get(trend)
            if color:
                trend_item.setForeground(color)
            trend_item.setTextAlignment(Qt.AlignCenter)
            self.comparison_stats_table.setItem(row, 7, trend_item)

        n = len(comp.point_ids)
        self.correlation_table.setRowCount(n)
        self.correlation_table.setColumnCount(n)
        codes = [comp.point_codes.get(pid, str(pid)) for pid in comp.point_ids]
        self.correlation_table.setHorizontalHeaderLabels(codes)
        self.correlation_table.setVerticalHeaderLabels(codes)

        for i in range(n):
            for j in range(n):
                if i == j:
                    item = QTableWidgetItem("1.00")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.correlation_table.setItem(i, j, item)
                else:
                    pid_i = comp.point_ids[i]
                    pid_j = comp.point_ids[j]
                    key = (min(pid_i, pid_j), max(pid_i, pid_j))
                    corr = comp.correlation_matrix.get(key)
                    if corr is not None:
                        text = f"{corr:.2f}"
                        item = QTableWidgetItem(text)
                        if abs(corr) > 0.7:
                            item.setForeground(QColor("#2ca02c"))
                        elif abs(corr) > 0.4:
                            item.setForeground(QColor("#ff7f0e"))
                        else:
                            item.setForeground(QColor("#7f7f7f"))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.correlation_table.setItem(i, j, item)
                    else:
                        self._set_table_item(self.correlation_table, i, j, "-")

    def _update_summary_label_single(self, point_id: int,
                                      stats: List[PeriodStatistics], summary: Dict):
        point = self.db.get_drip_point(point_id)
        name = f"{point['code']} - {point['name']}" if point else str(point_id)
        count = len(stats)
        total_data = sum(s.data_count for s in stats)
        avg_cv = sum(s.cv_interval for s in stats) / count if count else 0
        trend = summary.get("trend", "-")
        quality = summary.get("data_quality", "-")
        self.summary_label.setText(
            f"滴水点: {name} | 时段数: {count} | 总数据量: {total_data} | "
            f"平均变异系数: {avg_cv:.2f}% | 趋势: {trend} | 数据质量: {quality}"
        )

    def _update_summary_label_multi(self, comp: MultiPointComparison):
        n = len(comp.point_ids)
        start, end = comp.common_period
        period_text = f"{start} 至 {end}" if start and end else "未知"
        self.summary_label.setText(
            f"多点对比 | 滴水点数: {n} | 公共时段: {period_text}"
        )

    def _set_table_item(self, table: QTableWidget, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def refresh(self):
        self._load_point_options()
        self.stats_table.setRowCount(0)
        self.summary_table.setRowCount(0)
        self.seasonal_table.setRowCount(0)
        self.comparison_stats_table.setRowCount(0)
        self.correlation_table.setRowCount(0)
        self.correlation_table.setColumnCount(0)
        self.summary_label.setText('请选择条件后点击"执行统计"')
        self.export_btn.setEnabled(False)

    def _on_export(self):
        QMessageBox.information(self, "提示", "导出功能开发中")
