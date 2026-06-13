from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QLabel, QGroupBox, QComboBox,
    QAbstractItemView, QSplitter, QDoubleSpinBox, QSpinBox, QFormLayout, QDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import AnomalyDetector, ANOMALY_TYPES, RISK_LEVELS


class ThresholdDialog(QDialog):
    def __init__(self, parent=None, detector: Optional[AnomalyDetector] = None):
        super().__init__(parent)
        self.setWindowTitle("异常检测参数设置")
        self.setMinimumWidth(400)
        self._init_ui(detector)

    def _init_ui(self, detector: Optional[AnomalyDetector]):
        layout = QFormLayout(self)

        self.fluctuation_spin = QDoubleSpinBox()
        self.fluctuation_spin.setRange(0.1, 10.0)
        self.fluctuation_spin.setSingleStep(0.1)
        self.fluctuation_spin.setValue(detector.fluctuation_threshold if detector else 2.0)
        layout.addRow("波动阈值 (σ):", self.fluctuation_spin)

        self.consecutive_spin = QSpinBox()
        self.consecutive_spin.setRange(2, 50)
        self.consecutive_spin.setValue(detector.consecutive_count if detector else 5)
        layout.addRow("连续异常点数:", self.consecutive_spin)

        self.blockage_spin = QDoubleSpinBox()
        self.blockage_spin.setRange(1.0, 5.0)
        self.blockage_spin.setSingleStep(0.1)
        self.blockage_spin.setValue(detector.blockage_threshold if detector else 1.5)
        layout.addRow("堵塞阈值 (倍基线):", self.blockage_spin)

        self.seepage_spin = QDoubleSpinBox()
        self.seepage_spin.setRange(0.1, 1.0)
        self.seepage_spin.setSingleStep(0.05)
        self.seepage_spin.setValue(detector.seepage_threshold if detector else 0.6)
        layout.addRow("渗流增强阈值 (倍基线):", self.seepage_spin)

        self.sudden_spin = QDoubleSpinBox()
        self.sudden_spin.setRange(1.0, 5.0)
        self.sudden_spin.setSingleStep(0.1)
        self.sudden_spin.setValue(detector.sudden_change_threshold if detector else 2.5)
        layout.addRow("突变阈值 (倍):", self.sudden_spin)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def get_detector(self) -> AnomalyDetector:
        return AnomalyDetector(
            fluctuation_threshold=self.fluctuation_spin.value(),
            consecutive_count=self.consecutive_spin.value(),
            blockage_threshold=self.blockage_spin.value(),
            seepage_threshold=self.seepage_spin.value(),
            sudden_change_threshold=self.sudden_spin.value()
        )


class AnomalyPanel(QWidget):
    anomalies_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.detector = AnomalyDetector()
        self.current_point_id: Optional[int] = None
        self._init_ui()
        self.refresh_points()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_group = QGroupBox("异常检测")
        top_layout = QVBoxLayout(top_group)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("选择滴水点:"))
        self.point_combo = QComboBox()
        self.point_combo.setMinimumWidth(300)
        self.point_combo.currentIndexChanged.connect(self._on_point_changed)
        control_layout.addWidget(self.point_combo)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("全部类型", None)
        for type_key, type_name in ANOMALY_TYPES.items():
            self.filter_combo.addItem(type_name, type_key)
        self.filter_combo.currentIndexChanged.connect(self.refresh)
        control_layout.addWidget(QLabel("类型过滤:"))
        control_layout.addWidget(self.filter_combo)

        self.risk_combo = QComboBox()
        self.risk_combo.addItem("全部等级", None)
        for level in RISK_LEVELS:
            self.risk_combo.addItem(level, level)
        self.risk_combo.currentIndexChanged.connect(self.refresh)
        control_layout.addWidget(QLabel("风险等级:"))
        control_layout.addWidget(self.risk_combo)

        control_layout.addStretch()
        top_layout.addLayout(control_layout)

        btn_layout = QHBoxLayout()
        self.detect_btn = QPushButton("运行异常检测")
        self.detect_btn.clicked.connect(self._on_detect)
        self.save_btn = QPushButton("保存异常记录")
        self.save_btn.clicked.connect(self._on_save)
        self.settings_btn = QPushButton("参数设置")
        self.settings_btn.clicked.connect(self._on_settings)
        self.delete_btn = QPushButton("删除选中记录")
        self.delete_btn.clicked.connect(self._on_delete)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)

        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        btn_layout.addWidget(self.detect_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.settings_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        top_layout.addLayout(btn_layout)

        self.info_label = QLabel("请选择滴水点并运行异常检测")
        self.info_label.setStyleSheet("color: #666;")
        top_layout.addWidget(self.info_label)

        main_layout.addWidget(top_group)

        splitter = QSplitter(Qt.Vertical)

        record_group = QGroupBox("异常记录")
        record_layout = QVBoxLayout(record_group)
        self.record_table = QTableWidget()
        self.record_table.setColumnCount(8)
        self.record_table.setHorizontalHeaderLabels([
            "ID", "滴水点", "异常类型", "风险等级",
            "开始时间", "结束时间", "描述", "创建时间"
        ])
        self.record_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.record_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.record_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.record_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.record_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.record_table.itemSelectionChanged.connect(self._on_selection_changed)
        record_layout.addWidget(self.record_table)
        splitter.addWidget(record_group)

        stat_group = QGroupBox("检测结果统计")
        stat_layout = QVBoxLayout(stat_group)
        self.stat_table = QTableWidget()
        self.stat_table.setColumnCount(5)
        self.stat_table.setHorizontalHeaderLabels([
            "异常类型", "风险等级", "数量", "平均变化率", "描述"
        ])
        self.stat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.stat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        stat_layout.addWidget(self.stat_table)
        splitter.addWidget(stat_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

    def refresh_points(self):
        current_id = self.point_combo.currentData() if self.point_combo.count() > 0 else None
        self.point_combo.blockSignals(True)
        self.point_combo.clear()
        self.point_combo.addItem("全部滴水点", None)

        points = self.db.get_all_drip_points()
        for point in points:
            display = f"{point['code']} - {point['name']}"
            self.point_combo.addItem(display, point["id"])

        if current_id is not None:
            index = self.point_combo.findData(current_id)
            if index >= 0:
                self.point_combo.setCurrentIndex(index)
        self.point_combo.blockSignals(False)

    def set_selected_point(self, point_id: Optional[int]):
        if point_id is None:
            self.point_combo.setCurrentIndex(0)
        else:
            index = self.point_combo.findData(point_id)
            if index >= 0:
                self.point_combo.setCurrentIndex(index)

    def _on_point_changed(self):
        self.current_point_id = self.point_combo.currentData()
        self.save_btn.setEnabled(False)
        self.stat_table.setRowCount(0)
        self.refresh()

    def _on_selection_changed(self):
        has_selection = len(self.record_table.selectedItems()) > 0
        self.delete_btn.setEnabled(has_selection)

    def _get_risk_color(self, risk_level: str) -> QColor:
        colors = {
            "低": QColor("#2ca02c"),
            "中": QColor("#ffbb78"),
            "高": QColor("#ff7f0e"),
            "极高": QColor("#d62728"),
        }
        return colors.get(risk_level, QColor("#000000"))

    def _get_type_color(self, anomaly_type: str) -> QColor:
        type_map = {v: k for k, v in ANOMALY_TYPES.items()}
        type_key = type_map.get(anomaly_type, anomaly_type)
        colors = {
            "blockage": QColor("#d62728"),
            "increased_seepage": QColor("#9467bd"),
            "sudden_change": QColor("#ff7f0e"),
            "abnormal_fluctuation": QColor("#ffbb78"),
            "data_gap": QColor("#7f7f7f"),
        }
        return colors.get(type_key, QColor("#000000"))

    def refresh(self):
        point_id = self.current_point_id
        filter_type = self.filter_combo.currentData()
        filter_risk = self.risk_combo.currentData()

        if point_id is not None:
            records = self.db.get_anomaly_records(point_id)
        else:
            records = self.db.get_anomaly_records()

        if filter_type:
            records = [r for r in records if r["anomaly_type"] == ANOMALY_TYPES.get(filter_type, filter_type)]
        if filter_risk:
            records = [r for r in records if r["risk_level"] == filter_risk]

        self.record_table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.record_table.setItem(row, 0, QTableWidgetItem(str(record["id"])))
            self.record_table.setItem(row, 1, QTableWidgetItem(f"{record['drip_point_code']} - {record['drip_point_name']}"))

            type_item = QTableWidgetItem(record["anomaly_type"])
            type_item.setForeground(self._get_type_color(record["anomaly_type"]))
            self.record_table.setItem(row, 2, type_item)

            risk_item = QTableWidgetItem(record["risk_level"])
            risk_item.setForeground(self._get_risk_color(record["risk_level"]))
            risk_item.setBackground(QBrush(self._get_risk_color(record["risk_level"]).lighter(180)))
            self.record_table.setItem(row, 3, risk_item)

            self.record_table.setItem(row, 4, QTableWidgetItem(record.get("start_time", "-")))
            self.record_table.setItem(row, 5, QTableWidgetItem(record.get("end_time", "-")))
            self.record_table.setItem(row, 6, QTableWidgetItem(record.get("description", "-")))
            self.record_table.setItem(row, 7, QTableWidgetItem(record.get("created_at", "-")))

            for col in range(8):
                item = self.record_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.delete_btn.setEnabled(False)

    def _on_detect(self):
        point_id = self.current_point_id
        if point_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个滴水点")
            return

        data = self.db.get_monitoring_data(point_id)
        if len(data) < self.detector.consecutive_count * 2:
            QMessageBox.warning(self, "提示",
                f"数据量不足，至少需要 {self.detector.consecutive_count * 2} 条数据")
            return

        result = self.detector.detect_anomalies(data)

        self.info_label.setText(
            f"检测完成：基线 {result.baseline_mean:.2f}s ± {result.baseline_std:.2f}s，"
            f"共 {len(result.segments)} 个异常段"
        )

        self._show_detection_result(result)
        self.save_btn.setEnabled(len(result.segments) > 0)
        self.current_result = result

        self.anomalies_updated.emit()

    def _show_detection_result(self, result):
        self.stat_table.setRowCount(len(result.segments))
        for row, seg in enumerate(result.segments):
            type_name = ANOMALY_TYPES.get(seg.anomaly_type, seg.anomaly_type)
            type_item = QTableWidgetItem(type_name)
            type_item.setForeground(self._get_type_color(type_name))
            self.stat_table.setItem(row, 0, type_item)

            risk_item = QTableWidgetItem(seg.risk_level)
            risk_item.setForeground(self._get_risk_color(seg.risk_level))
            risk_item.setBackground(QBrush(self._get_risk_color(seg.risk_level).lighter(180)))
            self.stat_table.setItem(row, 1, risk_item)

            self.stat_table.setItem(row, 2, QTableWidgetItem(str(seg.end_idx - seg.start_idx + 1)))
            self.stat_table.setItem(row, 3, QTableWidgetItem(f"{seg.change_percent:+.1f}%"))
            self.stat_table.setItem(row, 4, QTableWidgetItem(seg.description))

            for col in range(5):
                item = self.stat_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_save(self):
        if not hasattr(self, 'current_result') or not self.current_result.segments:
            return

        point_id = self.current_point_id
        if point_id is None:
            return

        saved_count, msg = self.detector.save_anomalies_to_db(self.db, point_id, self.current_result)
        QMessageBox.information(self, "保存结果", msg)
        self.refresh()
        self.save_btn.setEnabled(False)

    def _on_settings(self):
        dialog = ThresholdDialog(self, self.detector)
        if dialog.exec() == QDialog.Accepted:
            self.detector = dialog.get_detector()

    def _on_delete(self):
        row = self.record_table.currentRow()
        if row < 0:
            return

        anomaly_id = int(self.record_table.item(row, 0).text())
        anomaly_type = self.record_table.item(row, 2).text()

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除这条 [{anomaly_type}] 异常记录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_anomaly_record(anomaly_id)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def get_detector(self) -> AnomalyDetector:
        return self.detector

    def get_current_detection_result(self):
        return getattr(self, 'current_result', None)
