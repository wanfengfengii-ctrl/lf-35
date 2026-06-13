from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QLabel, QGroupBox, QComboBox,
    QAbstractItemView, QSplitter, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QBrush, QFont

from database.db_manager import get_db
from core.anomaly_detector import AdvancedAnomalyDetector, ANOMALY_TYPES, RISK_LEVELS, ANOMALY_STATUS_COLORS


RISK_LEVEL_COLORS = {
    "低": "#2ca02c",
    "中": "#ffbb78",
    "高": "#ff7f0e",
    "极高": "#d62728",
}

OVERALL_RISK_BG = {
    "极高": "#ffcccc",
    "高": "#ffe0b2",
    "中": "#fff9c4",
    "低": "#c8e6c9",
}

OVERALL_RISK_FG = {
    "极高": "#b71c1c",
    "高": "#e65100",
    "中": "#f57f17",
    "低": "#1b5e20",
}


class DashboardPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.detector = AdvancedAnomalyDetector()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        risk_frame = QFrame()
        risk_frame.setFrameShape(QFrame.StyledPanel)
        risk_layout = QVBoxLayout(risk_frame)
        risk_layout.setContentsMargins(12, 12, 12, 12)

        risk_header = QLabel("整体风险评估")
        risk_header.setFont(QFont("", 14, QFont.Bold))
        risk_layout.addWidget(risk_header)

        risk_grid = QGridLayout()
        risk_grid.setSpacing(16)

        self.overall_risk_card = QFrame()
        self.overall_risk_card.setFrameShape(QFrame.StyledPanel)
        self.overall_risk_card.setMinimumHeight(100)
        card_layout = QVBoxLayout(self.overall_risk_card)
        self.risk_level_label = QLabel("--")
        self.risk_level_label.setFont(QFont("", 24, QFont.Bold))
        self.risk_level_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.risk_level_label)
        self.risk_score_label = QLabel("风险评分: --")
        self.risk_score_label.setFont(QFont("", 11))
        self.risk_score_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.risk_score_label)
        self.trend_label = QLabel("趋势: --")
        self.trend_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.trend_label)
        risk_grid.addWidget(self.overall_risk_card, 0, 0, 2, 1)

        self.total_card = self._create_summary_card("异常总数", "0", "#e3f2fd", "#1565c0")
        risk_grid.addWidget(self.total_card, 0, 1)

        self.pending_card = self._create_summary_card("待处理", "0", "#ffebee", "#c62828")
        risk_grid.addWidget(self.pending_card, 0, 2)

        self.processing_card = self._create_summary_card("处理中", "0", "#fff3e0", "#e65100")
        risk_grid.addWidget(self.processing_card, 0, 3)

        self.completed_card = self._create_summary_card("已处理", "0", "#e8f5e9", "#2e7d32")
        risk_grid.addWidget(self.completed_card, 1, 1)

        self.ignored_card = self._create_summary_card("已忽略", "0", "#f5f5f5", "#616161")
        risk_grid.addWidget(self.ignored_card, 1, 2)

        self.high_risk_card = self._create_summary_card("高风险点", "0", "#fce4ec", "#c62828")
        risk_grid.addWidget(self.high_risk_card, 1, 3)

        risk_layout.addLayout(risk_grid)
        splitter.addWidget(risk_frame)

        filter_group = QGroupBox("异常筛选")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("状态:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部状态", None)
        for status in ANOMALY_STATUS_COLORS:
            self.status_combo.addItem(status, status)
        self.status_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.status_combo)

        filter_layout.addWidget(QLabel("风险等级:"))
        self.risk_combo = QComboBox()
        self.risk_combo.addItem("全部等级", None)
        for level in RISK_LEVELS:
            self.risk_combo.addItem(level, level)
        self.risk_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.risk_combo)

        filter_layout.addWidget(QLabel("洞区:"))
        self.area_combo = QComboBox()
        self.area_combo.addItem("全部洞区", None)
        areas = self.db.get_all_cave_areas()
        for area in areas:
            self.area_combo.addItem(f"{area['code']} - {area['name']}", area["id"])
        self.area_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.area_combo)

        filter_layout.addStretch()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self.refresh_btn)

        self.auto_refresh_btn = QPushButton("自动刷新: 关")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.toggled.connect(self._toggle_auto_refresh)
        filter_layout.addWidget(self.auto_refresh_btn)

        splitter.addWidget(filter_group)

        anomaly_group = QGroupBox("当前异常列表")
        anomaly_layout = QVBoxLayout(anomaly_group)
        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(8)
        self.anomaly_table.setHorizontalHeaderLabels([
            "ID", "滴水点", "异常类型", "风险等级",
            "状态", "开始时间", "结束时间", "描述"
        ])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.anomaly_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anomaly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.anomaly_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.anomaly_table.setSelectionMode(QAbstractItemView.SingleSelection)
        anomaly_layout.addWidget(self.anomaly_table)
        splitter.addWidget(anomaly_group)

        bottom_splitter = QSplitter(Qt.Horizontal)

        type_group = QGroupBox("异常类型分布")
        type_layout = QVBoxLayout(type_group)
        self.type_table = QTableWidget()
        self.type_table.setColumnCount(3)
        self.type_table.setHorizontalHeaderLabels(["异常类型", "数量", "占比"])
        self.type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.type_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.type_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        type_layout.addWidget(self.type_table)
        bottom_splitter.addWidget(type_group)

        rec_group = QGroupBox("风险评估建议")
        rec_layout = QVBoxLayout(rec_group)
        self.rec_label = QLabel("暂无建议")
        self.rec_label.setWordWrap(True)
        self.rec_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.rec_label.setStyleSheet("padding: 8px; font-size: 13px;")
        rec_layout.addWidget(self.rec_label)
        bottom_splitter.addWidget(rec_group)

        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 1)
        splitter.addWidget(bottom_splitter)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 3)
        splitter.setStretchFactor(3, 2)

        main_layout.addWidget(splitter)

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self.refresh)

    def _create_summary_card(self, title: str, value: str, bg_color: str, fg_color: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border-radius: 6px; padding: 4px; }}"
        )
        layout = QVBoxLayout(card)
        title_label = QLabel(title)
        title_label.setFont(QFont("", 10))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"color: {fg_color};")
        layout.addWidget(title_label)
        value_label = QLabel(value)
        value_label.setFont(QFont("", 20, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"color: {fg_color};")
        value_label.setObjectName("cardValue")
        layout.addWidget(value_label)
        return card

    def _set_card_value(self, card: QFrame, value: str):
        label = card.findChild(QLabel, "cardValue")
        if label:
            label.setText(value)

    def refresh(self):
        try:
            risk_result = AdvancedAnomalyDetector.assess_overall_risk(self.db)
        except Exception:
            risk_result = None

        self._update_risk_card(risk_result)
        self._update_summary_cards(risk_result)
        self._update_anomaly_table()
        self._update_type_distribution(risk_result)
        self._update_recommendations(risk_result)

    def _update_risk_card(self, risk_result):
        if risk_result is None:
            self.risk_level_label.setText("--")
            self.risk_score_label.setText("风险评分: --")
            self.trend_label.setText("趋势: --")
            self.overall_risk_card.setStyleSheet("QFrame { background-color: #f5f5f5; border-radius: 6px; }")
            return

        level = risk_result.overall_risk
        bg = OVERALL_RISK_BG.get(level, "#f5f5f5")
        fg = OVERALL_RISK_FG.get(level, "#333333")

        self.overall_risk_card.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border-radius: 6px; }}"
        )
        self.risk_level_label.setText(level)
        self.risk_level_label.setStyleSheet(f"color: {fg};")
        self.risk_score_label.setText(f"风险评分: {risk_result.risk_score}")
        self.risk_score_label.setStyleSheet(f"color: {fg};")
        self.trend_label.setText(f"趋势: {risk_result.trend_analysis}")
        self.trend_label.setStyleSheet(f"color: {fg};")

    def _update_summary_cards(self, risk_result):
        if risk_result is None:
            for card in [self.total_card, self.pending_card, self.processing_card,
                         self.completed_card, self.ignored_card, self.high_risk_card]:
                self._set_card_value(card, "0")
            return

        all_pending = self.db.get_anomalies_by_status(status="待处理")
        all_processing = self.db.get_anomalies_by_status(status="处理中")
        all_completed = self.db.get_anomalies_by_status(status="已处理")
        all_ignored = self.db.get_anomalies_by_status(status="已忽略")
        total = len(all_pending) + len(all_processing) + len(all_completed) + len(all_ignored)

        self._set_card_value(self.total_card, str(total))
        self._set_card_value(self.pending_card, str(len(all_pending)))
        self._set_card_value(self.processing_card, str(len(all_processing)))
        self._set_card_value(self.completed_card, str(len(all_completed)))
        self._set_card_value(self.ignored_card, str(len(all_ignored)))
        self._set_card_value(self.high_risk_card, str(len(risk_result.high_risk_points)))

    def _update_anomaly_table(self):
        status = self.status_combo.currentData()
        risk_level = self.risk_combo.currentData()
        area_id = self.area_combo.currentData()

        anomalies = self.db.get_anomalies_by_status(
            status=status, risk_level=risk_level, area_id=area_id
        )

        self.anomaly_table.setRowCount(len(anomalies))
        for row, a in enumerate(anomalies):
            self.anomaly_table.setItem(row, 0, QTableWidgetItem(str(a["id"])))
            point_text = f"{a.get('drip_point_code', '-')} - {a.get('drip_point_name', '-')}"
            self.anomaly_table.setItem(row, 1, QTableWidgetItem(point_text))

            type_item = QTableWidgetItem(a.get("anomaly_type", "-"))
            self.anomaly_table.setItem(row, 2, type_item)

            risk_item = QTableWidgetItem(a.get("risk_level", "-"))
            risk_color_str = RISK_LEVEL_COLORS.get(a.get("risk_level", ""), "#000000")
            risk_color = QColor(risk_color_str)
            risk_item.setForeground(risk_color)
            risk_item.setBackground(QBrush(risk_color.lighter(180)))
            self.anomaly_table.setItem(row, 3, risk_item)

            status_text = a.get("status", "待处理")
            status_item = QTableWidgetItem(status_text)
            status_color_str = ANOMALY_STATUS_COLORS.get(status_text, "#000000")
            status_item.setForeground(QColor(status_color_str))
            self.anomaly_table.setItem(row, 4, status_item)

            self.anomaly_table.setItem(row, 5, QTableWidgetItem(a.get("start_time", "-")))
            self.anomaly_table.setItem(row, 6, QTableWidgetItem(a.get("end_time", "-")))
            self.anomaly_table.setItem(row, 7, QTableWidgetItem(a.get("description", "-")))

            for col in range(8):
                item = self.anomaly_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _update_type_distribution(self, risk_result):
        if risk_result is None:
            self.type_table.setRowCount(0)
            return

        counts = risk_result.anomaly_counts
        total = sum(counts.values()) if counts else 0
        self.type_table.setRowCount(len(counts))

        for row, (atype, count) in enumerate(counts.items()):
            type_item = QTableWidgetItem(atype)
            self.type_table.setItem(row, 0, type_item)
            self.type_table.setItem(row, 1, QTableWidgetItem(str(count)))
            pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
            self.type_table.setItem(row, 2, QTableWidgetItem(pct))

            for col in range(3):
                item = self.type_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _update_recommendations(self, risk_result):
        if risk_result is None or not risk_result.recommendations:
            self.rec_label.setText("暂无建议")
            return

        lines = []
        for i, rec in enumerate(risk_result.recommendations, 1):
            lines.append(f"  {i}. {rec}")
        self.rec_label.setText("\n".join(lines))

    def _on_filter_changed(self):
        self._update_anomaly_table()

    def _toggle_auto_refresh(self, checked: bool):
        if checked:
            self.auto_refresh_btn.setText("自动刷新: 开")
            self._auto_refresh_timer.start(30000)
        else:
            self.auto_refresh_btn.setText("自动刷新: 关")
            self._auto_refresh_timer.stop()
