from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QComboBox, QDateEdit, QAbstractItemView, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import ANOMALY_TYPES, HANDLING_STATUSES, ANOMALY_STATUS_COLORS


class HandlingRecordDialog(QDialog):
    def __init__(self, parent=None, record_data: Optional[Dict] = None,
                 anomaly_id: Optional[int] = None, current_status: str = "待处理"):
        super().__init__(parent)
        self.record_data = record_data
        self.anomaly_id = anomaly_id
        self.current_status = current_status
        self.setWindowTitle("编辑处理记录" if record_data else "新增处理记录")
        self.setMinimumWidth(500)
        self._init_ui()
        if record_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.anomaly_label = QLabel()
        if self.anomaly_id:
            self.anomaly_label.setText(f"异常记录 ID: {self.anomaly_id}")
        else:
            self.anomaly_label.setText("未指定")
        layout.addRow("关联异常:", self.anomaly_label)

        self.handler_edit = QLineEdit()
        self.handler_edit.setPlaceholderText("处理人姓名")
        layout.addRow("处理人 *:", self.handler_edit)

        self.handle_time_edit = QDateEdit()
        self.handle_time_edit.setCalendarPopup(True)
        self.handle_time_edit.setDisplayFormat("yyyy-MM-dd")
        self.handle_time_edit.setDate(QDate.currentDate())
        layout.addRow("处理时间 *:", self.handle_time_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(HANDLING_STATUSES)
        if self.current_status == "待处理":
            self.status_combo.setCurrentText("处理中")
        elif self.current_status == "处理中":
            self.status_combo.setCurrentText("已处理")
        layout.addRow("处理状态 *:", self.status_combo)

        self.measures_edit = QTextEdit()
        self.measures_edit.setPlaceholderText("采取的处理措施")
        self.measures_edit.setMaximumHeight(80)
        layout.addRow("处理措施:", self.measures_edit)

        self.result_edit = QLineEdit()
        self.result_edit.setPlaceholderText("处理结果描述")
        layout.addRow("处理结果:", self.result_edit)

        self.follow_up_edit = QDateEdit()
        self.follow_up_edit.setCalendarPopup(True)
        self.follow_up_edit.setDisplayFormat("yyyy-MM-dd")
        self.follow_up_edit.setDate(QDate.currentDate().addDays(7))
        self.follow_up_edit.setSpecialValueText(" ")
        layout.addRow("跟进日期:", self.follow_up_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("备注信息")
        self.notes_edit.setMaximumHeight(60)
        layout.addRow("备注:", self.notes_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _load_data(self):
        if not self.record_data:
            return
        self.handler_edit.setText(self.record_data.get("handler", ""))
        if self.record_data.get("handle_time"):
            try:
                d = QDate.fromString(self.record_data["handle_time"], "yyyy-MM-dd")
                if d.isValid():
                    self.handle_time_edit.setDate(d)
            except Exception:
                pass
        status = self.record_data.get("status", "处理中")
        idx = self.status_combo.findText(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.measures_edit.setPlainText(self.record_data.get("measures", ""))
        self.result_edit.setText(self.record_data.get("result", ""))
        if self.record_data.get("follow_up_date"):
            try:
                d = QDate.fromString(self.record_data["follow_up_date"], "yyyy-MM-dd")
                if d.isValid():
                    self.follow_up_edit.setDate(d)
            except Exception:
                pass
        self.notes_edit.setPlainText(self.record_data.get("notes", ""))

    def _on_ok(self):
        handler = self.handler_edit.text().strip()
        if not handler:
            QMessageBox.warning(self, "提示", "请输入处理人")
            return
        self.accept()

    def get_data(self) -> Dict:
        follow_up = self.follow_up_edit.date().toString("yyyy-MM-dd")
        return {
            "anomaly_id": self.anomaly_id,
            "handler": self.handler_edit.text().strip(),
            "handle_time": self.handle_time_edit.date().toString("yyyy-MM-dd"),
            "status": self.status_combo.currentText(),
            "measures": self.measures_edit.toPlainText().strip(),
            "result": self.result_edit.text().strip(),
            "follow_up_date": follow_up,
            "notes": self.notes_edit.toPlainText().strip(),
        }


class HandlingPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("处理状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        for status in HANDLING_STATUSES:
            self.status_filter.addItem(status, status)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addWidget(QLabel("洞区:"))
        self.area_filter = QComboBox()
        self.area_filter.addItem("全部洞区", None)
        areas = self.db.get_all_cave_areas()
        for area in areas:
            self.area_filter.addItem(area["name"], area["id"])
        self.area_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.area_filter)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Vertical)

        anomaly_group = QGroupBox("异常记录")
        anomaly_layout = QVBoxLayout(anomaly_group)

        btn_layout1 = QHBoxLayout()
        self.add_handling_btn = QPushButton("新增处理记录")
        self.refresh_btn = QPushButton("刷新")
        self.add_handling_btn.clicked.connect(self._on_add_handling)
        self.refresh_btn.clicked.connect(self.refresh)
        self.add_handling_btn.setEnabled(False)
        btn_layout1.addWidget(self.add_handling_btn)
        btn_layout1.addStretch()
        btn_layout1.addWidget(self.refresh_btn)
        anomaly_layout.addLayout(btn_layout1)

        self.anomaly_table = QTableWidget()
        self.anomaly_table.setColumnCount(8)
        self.anomaly_table.setHorizontalHeaderLabels([
            "ID", "滴水点", "异常类型", "风险等级",
            "处理状态", "开始时间", "结束时间", "描述"
        ])
        self.anomaly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.anomaly_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.anomaly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.anomaly_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.anomaly_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.anomaly_table.itemSelectionChanged.connect(self._on_anomaly_selection_changed)
        anomaly_layout.addWidget(self.anomaly_table)
        splitter.addWidget(anomaly_group)

        handling_group = QGroupBox("处理记录")
        handling_layout = QVBoxLayout(handling_group)

        self.handling_table = QTableWidget()
        self.handling_table.setColumnCount(8)
        self.handling_table.setHorizontalHeaderLabels([
            "ID", "异常类型", "风险等级", "滴水点",
            "处理人", "处理时间", "状态", "处理结果"
        ])
        self.handling_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.handling_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.handling_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.handling_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.handling_table.setSelectionMode(QAbstractItemView.SingleSelection)
        handling_layout.addWidget(self.handling_table)
        splitter.addWidget(handling_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

    def refresh(self):
        self._refresh_anomalies()
        self._refresh_handling_records()

    def _refresh_anomalies(self):
        status = self.status_filter.currentData()
        area_id = self.area_filter.currentData()

        if status and area_id:
            records = self.db.get_anomalies_by_status(status=status, risk_level=None, area_id=area_id)
        elif status:
            records = self.db.get_anomalies_by_status(status=status, risk_level=None, area_id=None)
        elif area_id:
            all_records = self.db.get_anomaly_records()
            records = [r for r in all_records if r.get("area_id") == area_id]
        else:
            records = self.db.get_anomaly_records()

        self.anomaly_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.anomaly_table.setItem(row, 0, QTableWidgetItem(str(rec["id"])))
            self.anomaly_table.setItem(row, 1, QTableWidgetItem(
                f"{rec.get('drip_point_code', '-')} - {rec.get('drip_point_name', '-')}"
            ))
            self.anomaly_table.setItem(row, 2, QTableWidgetItem(rec.get("anomaly_type", "-")))

            risk_item = QTableWidgetItem(rec.get("risk_level", "-"))
            risk_color = self._get_risk_color(rec.get("risk_level", ""))
            risk_item.setForeground(risk_color)
            self.anomaly_table.setItem(row, 3, risk_item)

            status_text = rec.get("status", "待处理")
            status_item = QTableWidgetItem(status_text)
            color_hex = ANOMALY_STATUS_COLORS.get(status_text, "#000000")
            status_item.setForeground(QColor(color_hex))
            self.anomaly_table.setItem(row, 4, status_item)

            self.anomaly_table.setItem(row, 5, QTableWidgetItem(rec.get("start_time", "-")))
            self.anomaly_table.setItem(row, 6, QTableWidgetItem(rec.get("end_time", "-")))
            self.anomaly_table.setItem(row, 7, QTableWidgetItem(rec.get("description", "-")))

            for col in range(8):
                item = self.anomaly_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.add_handling_btn.setEnabled(False)

    def _refresh_handling_records(self, anomaly_id: Optional[int] = None):
        if anomaly_id:
            records = self.db.get_handling_records(anomaly_id)
        else:
            records = self.db.get_handling_records()

        self.handling_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.handling_table.setItem(row, 0, QTableWidgetItem(str(rec["id"])))
            self.handling_table.setItem(row, 1, QTableWidgetItem(rec.get("anomaly_type", "-")))

            risk_item = QTableWidgetItem(rec.get("risk_level", "-"))
            risk_color = self._get_risk_color(rec.get("risk_level", ""))
            risk_item.setForeground(risk_color)
            self.handling_table.setItem(row, 2, risk_item)

            self.handling_table.setItem(row, 3, QTableWidgetItem(
                f"{rec.get('drip_point_code', '-')} - {rec.get('drip_point_name', '-')}"
            ))
            self.handling_table.setItem(row, 4, QTableWidgetItem(rec.get("handler", "-")))
            self.handling_table.setItem(row, 5, QTableWidgetItem(rec.get("handle_time", "-")))

            status_text = rec.get("status", "处理中")
            status_item = QTableWidgetItem(status_text)
            color_hex = ANOMALY_STATUS_COLORS.get(status_text, "#000000")
            status_item.setForeground(QColor(color_hex))
            self.handling_table.setItem(row, 6, status_item)

            self.handling_table.setItem(row, 7, QTableWidgetItem(rec.get("result", "-")))

            for col in range(8):
                item = self.handling_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_anomaly_selection_changed(self):
        has = len(self.anomaly_table.selectedItems()) > 0
        self.add_handling_btn.setEnabled(has)
        if has:
            row = self.anomaly_table.currentRow()
            anomaly_id = int(self.anomaly_table.item(row, 0).text())
            self._refresh_handling_records(anomaly_id)

    def _get_selected_anomaly(self) -> Optional[Dict]:
        row = self.anomaly_table.currentRow()
        if row < 0:
            return None
        anomaly_id = int(self.anomaly_table.item(row, 0).text())
        records = self.db.get_anomaly_records()
        for r in records:
            if r["id"] == anomaly_id:
                return r
        return None

    def _get_risk_color(self, risk_level: str) -> QColor:
        colors = {
            "低": QColor("#2ca02c"),
            "中": QColor("#ffbb78"),
            "高": QColor("#ff7f0e"),
            "极高": QColor("#d62728"),
        }
        return colors.get(risk_level, QColor("#000000"))

    def _on_add_handling(self):
        anomaly = self._get_selected_anomaly()
        if not anomaly:
            return

        current_status = anomaly.get("status", "待处理")
        dialog = HandlingRecordDialog(
            self, anomaly_id=anomaly["id"], current_status=current_status
        )
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_handling_record(
                anomaly_id=data["anomaly_id"],
                handler=data["handler"],
                handle_time=data["handle_time"],
                status=data["status"],
                measures=data["measures"],
                result=data["result"],
                follow_up_date=data["follow_up_date"],
                notes=data["notes"]
            )
            if success:
                new_status = data["status"]
                self.db.update_anomaly_status(
                    anomaly_id=anomaly["id"],
                    status=new_status,
                    handler=data["handler"],
                    handling_time=data["handle_time"],
                    handling_result=data["result"]
                )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)
