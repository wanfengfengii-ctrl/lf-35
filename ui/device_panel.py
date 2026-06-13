from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QAbstractItemView, QComboBox, QDateEdit,
    QDoubleSpinBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import DEVICE_STATUSES


class DeviceDialog(QDialog):
    def __init__(self, parent=None, device_data: Optional[Dict] = None):
        super().__init__(parent)
        self.device_data = device_data
        self.setWindowTitle("编辑设备" if device_data else "新增设备")
        self.setMinimumWidth(450)
        self._init_ui()
        if device_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：DEV-001，不能重复")
        layout.addRow("设备编号 *:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：滴水监测仪A")
        layout.addRow("设备名称 *:", self.name_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("例如：DRM-2000")
        layout.addRow("型号:", self.model_edit)

        self.manufacturer_edit = QLineEdit()
        self.manufacturer_edit.setPlaceholderText("例如：某仪器公司")
        layout.addRow("厂商:", self.manufacturer_edit)

        self.sensor_type_edit = QComboBox()
        self.sensor_type_edit.addItems(["", "压力传感器", "光电传感器", "声学传感器", "电容式", "其他"])
        layout.addRow("传感器类型:", self.sensor_type_edit)

        self.install_date_edit = QDateEdit()
        self.install_date_edit.setCalendarPopup(True)
        self.install_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.install_date_edit.setDate(QDate.currentDate())
        self.install_date_edit.setSpecialValueText(" ")
        layout.addRow("安装日期:", self.install_date_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItems(DEVICE_STATUSES)
        layout.addRow("状态:", self.status_combo)

        self.point_combo = QComboBox()
        self.point_combo.addItem("未绑定", None)
        db = get_db()
        points = db.get_all_drip_points()
        for p in points:
            self.point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])
        layout.addRow("绑定滴水点:", self.point_combo)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("设备备注信息")
        self.desc_edit.setMaximumHeight(80)
        layout.addRow("描述:", self.desc_edit)

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
        if self.device_data:
            self.code_edit.setText(self.device_data.get("code", ""))
            self.name_edit.setText(self.device_data.get("name", ""))
            self.model_edit.setText(self.device_data.get("model", ""))
            self.manufacturer_edit.setText(self.device_data.get("manufacturer", ""))
            st = self.device_data.get("sensor_type", "")
            idx = self.sensor_type_edit.findText(st)
            if idx >= 0:
                self.sensor_type_edit.setCurrentIndex(idx)
            if self.device_data.get("install_date"):
                try:
                    d = QDate.fromString(self.device_data["install_date"], "yyyy-MM-dd")
                    if d.isValid():
                        self.install_date_edit.setDate(d)
                except Exception:
                    pass
            status = self.device_data.get("status", "在用")
            idx = self.status_combo.findText(status)
            if idx >= 0:
                self.status_combo.setCurrentIndex(idx)
            pid = self.device_data.get("drip_point_id")
            if pid:
                idx = self.point_combo.findData(pid)
                if idx >= 0:
                    self.point_combo.setCurrentIndex(idx)
            self.desc_edit.setPlainText(self.device_data.get("description", ""))

    def _on_ok(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()

        if not code:
            QMessageBox.warning(self, "提示", "请输入设备编号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入设备名称")
            return

        self.accept()

    def get_data(self) -> Dict:
        install_date = self.install_date_edit.date().toString("yyyy-MM-dd")
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "model": self.model_edit.text().strip(),
            "manufacturer": self.manufacturer_edit.text().strip(),
            "sensor_type": self.sensor_type_edit.currentText().strip(),
            "install_date": install_date,
            "status": self.status_combo.currentText(),
            "drip_point_id": self.point_combo.currentData(),
            "description": self.desc_edit.toPlainText().strip(),
        }


class CalibrationDialog(QDialog):
    def __init__(self, parent=None, calib_data: Optional[Dict] = None, device_id: Optional[int] = None):
        super().__init__(parent)
        self.calib_data = calib_data
        self.device_id = device_id
        self.setWindowTitle("编辑校准记录" if calib_data else "新增校准记录")
        self.setMinimumWidth(450)
        self._init_ui()
        if calib_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.device_combo = QComboBox()
        db = get_db()
        devices = db.get_all_devices()
        for d in devices:
            self.device_combo.addItem(f"{d['code']} - {d['name']}", d["id"])
        if self.device_id:
            idx = self.device_combo.findData(self.device_id)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)
        layout.addRow("设备 *:", self.device_combo)

        self.calib_date_edit = QDateEdit()
        self.calib_date_edit.setCalendarPopup(True)
        self.calib_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.calib_date_edit.setDate(QDate.currentDate())
        layout.addRow("校准日期 *:", self.calib_date_edit)

        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("操作人员姓名")
        layout.addRow("操作人:", self.operator_edit)

        self.before_spin = QDoubleSpinBox()
        self.before_spin.setRange(0, 99999)
        self.before_spin.setDecimals(2)
        self.before_spin.setSuffix(" s")
        self.before_spin.setSpecialValueText(" ")
        layout.addRow("校准前读数:", self.before_spin)

        self.after_spin = QDoubleSpinBox()
        self.after_spin.setRange(0, 99999)
        self.after_spin.setDecimals(2)
        self.after_spin.setSuffix(" s")
        self.after_spin.setSpecialValueText(" ")
        layout.addRow("校准后读数:", self.after_spin)

        self.error_spin = QDoubleSpinBox()
        self.error_spin.setRange(-9999, 9999)
        self.error_spin.setDecimals(2)
        self.error_spin.setSuffix(" s")
        self.error_spin.setSpecialValueText(" ")
        layout.addRow("误差:", self.error_spin)

        self.cert_edit = QLineEdit()
        self.cert_edit.setPlaceholderText("校准证书编号")
        layout.addRow("证书编号:", self.cert_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("校准备注")
        self.notes_edit.setMaximumHeight(80)
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
        if self.calib_data:
            if "device_id" in self.calib_data:
                idx = self.device_combo.findData(self.calib_data["device_id"])
                if idx >= 0:
                    self.device_combo.setCurrentIndex(idx)
            if self.calib_data.get("calibration_date"):
                try:
                    d = QDate.fromString(self.calib_data["calibration_date"], "yyyy-MM-dd")
                    if d.isValid():
                        self.calib_date_edit.setDate(d)
                except Exception:
                    pass
            self.operator_edit.setText(self.calib_data.get("operator", ""))
            if self.calib_data.get("before_value") is not None:
                self.before_spin.setValue(self.calib_data["before_value"])
            if self.calib_data.get("after_value") is not None:
                self.after_spin.setValue(self.calib_data["after_value"])
            if self.calib_data.get("error") is not None:
                self.error_spin.setValue(self.calib_data["error"])
            self.cert_edit.setText(self.calib_data.get("certificate_no", ""))
            self.notes_edit.setPlainText(self.calib_data.get("notes", ""))

    def _on_ok(self):
        if self.device_combo.currentData() is None:
            QMessageBox.warning(self, "提示", "请选择设备")
            return
        self.accept()

    def get_data(self) -> Dict:
        before = self.before_spin.value()
        after = self.after_spin.value()
        error = self.error_spin.value()
        if before > 0 and after > 0 and error == self.error_spin.minimum():
            error = after - before
        return {
            "device_id": self.device_combo.currentData(),
            "calibration_date": self.calib_date_edit.date().toString("yyyy-MM-dd"),
            "operator": self.operator_edit.text().strip(),
            "before_value": before if before != self.before_spin.minimum() else None,
            "after_value": after if after != self.after_spin.minimum() else None,
            "error": error if error != self.error_spin.minimum() else None,
            "certificate_no": self.cert_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class DevicePanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        dev_group = QGroupBox("设备档案")
        dev_layout = QVBoxLayout(dev_group)

        btn_layout1 = QHBoxLayout()
        self.add_dev_btn = QPushButton("新增设备")
        self.edit_dev_btn = QPushButton("编辑设备")
        self.delete_dev_btn = QPushButton("删除设备")
        self.refresh_btn = QPushButton("刷新")
        self.add_dev_btn.clicked.connect(self._on_add_device)
        self.edit_dev_btn.clicked.connect(self._on_edit_device)
        self.delete_dev_btn.clicked.connect(self._on_delete_device)
        self.refresh_btn.clicked.connect(self.refresh)
        self.edit_dev_btn.setEnabled(False)
        self.delete_dev_btn.setEnabled(False)
        btn_layout1.addWidget(self.add_dev_btn)
        btn_layout1.addWidget(self.edit_dev_btn)
        btn_layout1.addWidget(self.delete_dev_btn)
        btn_layout1.addStretch()
        btn_layout1.addWidget(self.refresh_btn)
        dev_layout.addLayout(btn_layout1)

        self.device_table = QTableWidget()
        self.device_table.setColumnCount(8)
        self.device_table.setHorizontalHeaderLabels(
            ["ID", "编号", "名称", "型号", "传感器类型", "状态", "绑定滴水点", "安装日期"]
        )
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_table.itemSelectionChanged.connect(self._on_device_selection_changed)
        self.device_table.cellDoubleClicked.connect(self._on_edit_device)
        dev_layout.addWidget(self.device_table)
        splitter.addWidget(dev_group)

        calib_group = QGroupBox("校准记录")
        calib_layout = QVBoxLayout(calib_group)

        btn_layout2 = QHBoxLayout()
        self.add_calib_btn = QPushButton("新增校准")
        self.edit_calib_btn = QPushButton("编辑校准")
        self.delete_calib_btn = QPushButton("删除校准")
        self.add_calib_btn.clicked.connect(self._on_add_calibration)
        self.edit_calib_btn.clicked.connect(self._on_edit_calibration)
        self.delete_calib_btn.clicked.connect(self._on_delete_calibration)
        self.edit_calib_btn.setEnabled(False)
        self.delete_calib_btn.setEnabled(False)
        btn_layout2.addWidget(self.add_calib_btn)
        btn_layout2.addWidget(self.edit_calib_btn)
        btn_layout2.addWidget(self.delete_calib_btn)
        btn_layout2.addStretch()
        calib_layout.addLayout(btn_layout2)

        self.calib_table = QTableWidget()
        self.calib_table.setColumnCount(8)
        self.calib_table.setHorizontalHeaderLabels(
            ["ID", "设备", "校准日期", "操作人", "校准前", "校准后", "误差", "证书编号"]
        )
        self.calib_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.calib_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.calib_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.calib_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.calib_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.calib_table.itemSelectionChanged.connect(self._on_calib_selection_changed)
        calib_layout.addWidget(self.calib_table)
        splitter.addWidget(calib_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def refresh(self):
        self._refresh_devices()
        self._refresh_calibrations()

    def _refresh_devices(self):
        devices = self.db.get_all_devices()

        self.device_table.blockSignals(True)
        self.device_table.setRowCount(len(devices))

        status_colors = {
            "在用": QColor("#2ca02c"),
            "停用": QColor("#7f7f7f"),
            "维修中": QColor("#ff7f0e"),
            "待校准": QColor("#d62728"),
        }

        for row, dev in enumerate(devices):
            self.device_table.setItem(row, 0, QTableWidgetItem(str(dev["id"])))
            self.device_table.setItem(row, 1, QTableWidgetItem(dev["code"]))
            self.device_table.setItem(row, 2, QTableWidgetItem(dev["name"]))
            self.device_table.setItem(row, 3, QTableWidgetItem(dev.get("model", "-")))
            self.device_table.setItem(row, 4, QTableWidgetItem(dev.get("sensor_type", "-")))

            status_item = QTableWidgetItem(dev.get("status", "-"))
            color = status_colors.get(dev.get("status", ""), QColor("#000"))
            status_item.setForeground(color)
            self.device_table.setItem(row, 5, status_item)

            point_text = "-"
            if dev.get("drip_point_code"):
                point_text = f"{dev['drip_point_code']} - {dev['drip_point_name']}"
            self.device_table.setItem(row, 6, QTableWidgetItem(point_text))
            self.device_table.setItem(row, 7, QTableWidgetItem(dev.get("install_date", "-")))

            for col in range(8):
                item = self.device_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.device_table.blockSignals(False)

        self.edit_dev_btn.setEnabled(False)
        self.delete_dev_btn.setEnabled(False)

    def _refresh_calibrations(self, device_id: Optional[int] = None):
        records = self.db.get_calibration_records(device_id)

        self.calib_table.blockSignals(True)
        self.calib_table.setRowCount(len(records))

        for row, rec in enumerate(records):
            self.calib_table.setItem(row, 0, QTableWidgetItem(str(rec["id"])))
            self.calib_table.setItem(row, 1, QTableWidgetItem(
                f"{rec.get('device_code', '-')} - {rec.get('device_name', '-')}"
            ))
            self.calib_table.setItem(row, 2, QTableWidgetItem(rec.get("calibration_date", "-")))
            self.calib_table.setItem(row, 3, QTableWidgetItem(rec.get("operator", "-")))
            self.calib_table.setItem(row, 4, QTableWidgetItem(
                f"{rec['before_value']:.2f}" if rec.get("before_value") is not None else "-"
            ))
            self.calib_table.setItem(row, 5, QTableWidgetItem(
                f"{rec['after_value']:.2f}" if rec.get("after_value") is not None else "-"
            ))

            error_item = QTableWidgetItem(
                f"{rec['error']:.2f}" if rec.get("error") is not None else "-"
            )
            if rec.get("error") is not None and abs(rec["error"]) > 1.0:
                error_item.setForeground(QColor("#d62728"))
            self.calib_table.setItem(row, 6, error_item)

            self.calib_table.setItem(row, 7, QTableWidgetItem(rec.get("certificate_no", "-")))

            for col in range(8):
                item = self.calib_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.calib_table.blockSignals(False)

        self.edit_calib_btn.setEnabled(False)
        self.delete_calib_btn.setEnabled(False)

    def _on_device_selection_changed(self):
        has = len(self.device_table.selectedItems()) > 0
        self.edit_dev_btn.setEnabled(has)
        self.delete_dev_btn.setEnabled(has)
        if has:
            row = self.device_table.currentRow()
            dev_id = int(self.device_table.item(row, 0).text())
            self._refresh_calibrations(dev_id)

    def _on_calib_selection_changed(self):
        has = len(self.calib_table.selectedItems()) > 0
        self.edit_calib_btn.setEnabled(has)
        self.delete_calib_btn.setEnabled(has)

    def _get_selected_device(self) -> Optional[Dict]:
        row = self.device_table.currentRow()
        if row < 0:
            return None
        dev_id = int(self.device_table.item(row, 0).text())
        return self.db.get_device(dev_id)

    def _get_selected_calibration(self) -> Optional[Dict]:
        row = self.calib_table.currentRow()
        if row < 0:
            return None
        rec_id = int(self.calib_table.item(row, 0).text())
        records = self.db.get_calibration_records()
        for r in records:
            if r["id"] == rec_id:
                return r
        return None

    def _on_add_device(self):
        dialog = DeviceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_device(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_device(self):
        dev = self._get_selected_device()
        if not dev:
            return
        dialog = DeviceDialog(self, dev)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_device(dev["id"], **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_device(self):
        dev = self._get_selected_device()
        if not dev:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除设备 [{dev['code']} - {dev['name']}] 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_device(dev["id"])
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_add_calibration(self):
        dev = self._get_selected_device()
        device_id = dev["id"] if dev else None
        dialog = CalibrationDialog(self, device_id=device_id)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_calibration_record(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_calibration(self):
        rec = self._get_selected_calibration()
        if not rec:
            return
        dialog = CalibrationDialog(self, calib_data=rec, device_id=rec.get("device_id"))
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_calibration_record(rec["id"], **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_calibration(self):
        rec = self._get_selected_calibration()
        if not rec:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除该校准记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_calibration_record(rec["id"])
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)
