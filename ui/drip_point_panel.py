from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QAbstractItemView, QComboBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from database.db_manager import get_db


class DripPointDialog(QDialog):
    def __init__(self, parent=None, point_data: Optional[Dict] = None):
        super().__init__(parent)
        self.point_data = point_data
        self.setWindowTitle("编辑滴水点" if point_data else "新增滴水点")
        self.setMinimumWidth(450)
        self._init_ui()
        if point_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：HSD-001，不能重复")
        layout.addRow("编号 *:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：主洞滴水点A")
        layout.addRow("名称 *:", self.name_edit)

        self.area_combo = QComboBox()
        self.area_combo.addItem("未指定", None)
        db = get_db()
        areas = db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        layout.addRow("所属洞区:", self.area_combo)

        self.zone_combo = QComboBox()
        self.zone_combo.addItem("未指定", None)
        layout.addRow("所属子区域:", self.zone_combo)

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：海蚀洞东区15米处")
        layout.addRow("位置:", self.location_edit)

        self.elevation_spin = QDoubleSpinBox()
        self.elevation_spin.setRange(-100, 5000)
        self.elevation_spin.setDecimals(1)
        self.elevation_spin.setSuffix(" m")
        self.elevation_spin.setSpecialValueText("")
        layout.addRow("海拔:", self.elevation_spin)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("备注信息，如安装日期、传感器型号等")
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("描述:", self.desc_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def _on_area_changed(self):
        area_id = self.area_combo.currentData()
        self.zone_combo.clear()
        self.zone_combo.addItem("未指定", None)
        if area_id:
            db = get_db()
            zones = db.get_zones_by_area(area_id)
            for z in zones:
                layer_text = f" [{z['layer']}]" if z.get("layer") else ""
                self.zone_combo.addItem(f"{z['code']} - {z['name']}{layer_text}", z["id"])

    def _load_data(self):
        if self.point_data:
            self.code_edit.setText(self.point_data.get("code", ""))
            self.name_edit.setText(self.point_data.get("name", ""))
            self.location_edit.setText(self.point_data.get("location", ""))
            self.desc_edit.setPlainText(self.point_data.get("description", ""))

            if self.point_data.get("area_id"):
                idx = self.area_combo.findData(self.point_data["area_id"])
                if idx >= 0:
                    self.area_combo.setCurrentIndex(idx)

            if self.point_data.get("zone_id"):
                idx = self.zone_combo.findData(self.point_data["zone_id"])
                if idx >= 0:
                    self.zone_combo.setCurrentIndex(idx)

            if self.point_data.get("elevation") is not None:
                self.elevation_spin.setValue(self.point_data["elevation"])

    def _on_ok(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()

        if not code:
            QMessageBox.warning(self, "提示", "请输入滴水点编号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入滴水点名称")
            return

        self.accept()

    def get_data(self) -> Dict:
        elev = self.elevation_spin.value()
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "location": self.location_edit.text().strip(),
            "area_id": self.area_combo.currentData(),
            "zone_id": self.zone_combo.currentData(),
            "elevation": elev if elev != self.elevation_spin.minimum() else None,
            "description": self.desc_edit.toPlainText().strip(),
        }


class DripPointPanel(QWidget):
    point_selected = Signal(int)
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        info_group = QGroupBox("滴水点管理")
        info_layout = QVBoxLayout(info_group)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选洞区:"))
        self.area_filter = QComboBox()
        self.area_filter.addItem("全部", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_filter.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.area_filter)
        filter_layout.addStretch()
        info_layout.addLayout(filter_layout)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")
        self.refresh_btn = QPushButton("刷新")

        self.add_btn.clicked.connect(self._on_add)
        self.edit_btn.clicked.connect(self._on_edit)
        self.delete_btn.clicked.connect(self._on_delete)
        self.refresh_btn.clicked.connect(self.refresh)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)

        info_layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "编号", "名称", "所属洞区", "子区域", "位置", "海拔", "数据量"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.cellDoubleClicked.connect(self._on_edit)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        info_layout.addWidget(self.table)

        stat_layout = QHBoxLayout()
        self.stat_label = QLabel("共 0 个滴水点")
        stat_layout.addWidget(self.stat_label)
        stat_layout.addStretch()
        info_layout.addLayout(stat_layout)

        main_layout.addWidget(info_group)

    def refresh(self):
        area_id = self.area_filter.currentData()

        if area_id:
            points = self.db.get_drip_points_by_area(area_id)
        else:
            points = self.db.get_all_drip_points()

        areas_map = {}
        for a in self.db.get_all_cave_areas():
            areas_map[a["id"]] = f"{a['code']} - {a['name']}"

        zones_map = {}
        for a in self.db.get_all_cave_areas():
            for z in self.db.get_zones_by_area(a["id"]):
                zones_map[z["id"]] = f"{z['code']} - {z['name']}"

        self.table.setRowCount(len(points))

        for row, point in enumerate(points):
            data_count = self.db.get_monitoring_data_count(point["id"])

            self.table.setItem(row, 0, QTableWidgetItem(str(point["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(point["code"]))
            self.table.setItem(row, 2, QTableWidgetItem(point["name"]))

            area_text = areas_map.get(point.get("area_id"), "-")
            self.table.setItem(row, 3, QTableWidgetItem(area_text))

            zone_text = zones_map.get(point.get("zone_id"), "-")
            self.table.setItem(row, 4, QTableWidgetItem(zone_text))

            self.table.setItem(row, 5, QTableWidgetItem(point.get("location", "-")))

            elev_text = f"{point['elevation']:.1f} m" if point.get("elevation") is not None else "-"
            self.table.setItem(row, 6, QTableWidgetItem(elev_text))

            count_item = QTableWidgetItem(str(data_count))
            if data_count > 0:
                count_item.setForeground(QColor("#1f77b4"))
            self.table.setItem(row, 7, count_item)

            for col in range(8):
                item = self.table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self.stat_label.setText(f"共 {len(points)} 个滴水点")

        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def _on_selection_changed(self):
        has_selection = len(self.table.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

        if has_selection:
            row = self.table.currentRow()
            point_id = int(self.table.item(row, 0).text())
            self.point_selected.emit(point_id)

    def _get_selected_point(self) -> Optional[Dict]:
        row = self.table.currentRow()
        if row < 0:
            return None
        point_id = int(self.table.item(row, 0).text())
        return self.db.get_drip_point(point_id)

    def _on_add(self):
        dialog = DripPointDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, point_id = self.db.add_drip_point(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit(self):
        point = self._get_selected_point()
        if not point:
            return

        dialog = DripPointDialog(self, point)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_drip_point(
                point["id"], **data
            )
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete(self):
        point = self._get_selected_point()
        if not point:
            return

        data_count = self.db.get_monitoring_data_count(point["id"])

        if data_count > 0:
            QMessageBox.warning(
                self, "无法删除",
                f"滴水点 [{point['code']} - {point['name']}] 已有 {data_count} 条历史监测数据，无法删除。\n\n"
                "如需删除，请先在【数据导入】模块清空该滴水点的所有历史数据，或联系管理员。"
            )
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除滴水点 [{point['code']} - {point['name']}] 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_drip_point(point["id"])
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def get_selected_point_id(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())
