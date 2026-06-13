from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QAbstractItemView, QComboBox, QDoubleSpinBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import AdvancedAnomalyDetector


class CaveAreaDialog(QDialog):
    def __init__(self, parent=None, area_data: Optional[Dict] = None):
        super().__init__(parent)
        self.area_data = area_data
        self.setWindowTitle("编辑洞区" if area_data else "新增洞区")
        self.setMinimumWidth(450)
        self._init_ui()
        if area_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)
        
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：HSD-01，不能重复")
        layout.addRow("编号 *:", self.code_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：海蚀洞一号")
        layout.addRow("名称 *:", self.name_edit)
        
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：青岛市崂山区")
        layout.addRow("位置:", self.location_edit)
        
        self.geological_edit = QComboBox()
        self.geological_edit.addItems(["", "花岗岩", "石灰岩", "玄武岩", "砂岩", "变质岩", "其他"])
        layout.addRow("地质类型:", self.geological_edit)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("洞区地质描述、研究历史等")
        self.desc_edit.setMaximumHeight(100)
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
        if self.area_data:
            self.code_edit.setText(self.area_data.get("code", ""))
            self.name_edit.setText(self.area_data.get("name", ""))
            self.location_edit.setText(self.area_data.get("location", ""))
            geo = self.area_data.get("geological_type", "")
            idx = self.geological_edit.findText(geo)
            if idx >= 0:
                self.geological_edit.setCurrentIndex(idx)
            self.desc_edit.setPlainText(self.area_data.get("description", ""))

    def _on_ok(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        
        if not code:
            QMessageBox.warning(self, "提示", "请输入洞区编号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入洞区名称")
            return
        
        self.accept()

    def get_data(self) -> Dict:
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "location": self.location_edit.text().strip(),
            "geological_type": self.geological_edit.currentText().strip(),
            "description": self.desc_edit.toPlainText().strip(),
        }


class CaveZoneDialog(QDialog):
    def __init__(self, parent=None, zone_data: Optional[Dict] = None, area_id: Optional[int] = None):
        super().__init__(parent)
        self.zone_data = zone_data
        self.area_id = area_id
        self.setWindowTitle("编辑子区域" if zone_data else "新增子区域")
        self.setMinimumWidth(450)
        self._init_ui()
        if zone_data:
            self._load_data()

    def _init_ui(self):
        layout = QFormLayout(self)
        
        self.area_combo = QComboBox()
        db = get_db()
        areas = db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        if self.area_id:
            idx = self.area_combo.findData(self.area_id)
            if idx >= 0:
                self.area_combo.setCurrentIndex(idx)
        layout.addRow("所属洞区 *:", self.area_combo)
        
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例如：A-01，同一洞区内不能重复")
        layout.addRow("编号 *:", self.code_edit)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：主洞大厅")
        layout.addRow("名称 *:", self.name_edit)
        
        self.layer_edit = QComboBox()
        self.layer_edit.addItems(["", "上层", "中层", "下层", "底层"])
        layout.addRow("分层:", self.layer_edit)
        
        self.elevation_spin = QDoubleSpinBox()
        self.elevation_spin.setRange(-100, 5000)
        self.elevation_spin.setDecimals(1)
        self.elevation_spin.setSuffix(" m")
        self.elevation_spin.setSpecialValueText("")
        layout.addRow("海拔:", self.elevation_spin)
        
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("子区域描述")
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
        if self.zone_data:
            if "area_id" in self.zone_data:
                idx = self.area_combo.findData(self.zone_data["area_id"])
                if idx >= 0:
                    self.area_combo.setCurrentIndex(idx)
            self.code_edit.setText(self.zone_data.get("code", ""))
            self.name_edit.setText(self.zone_data.get("name", ""))
            layer = self.zone_data.get("layer", "")
            idx = self.layer_edit.findText(layer)
            if idx >= 0:
                self.layer_edit.setCurrentIndex(idx)
            if self.zone_data.get("elevation") is not None:
                self.elevation_spin.setValue(self.zone_data["elevation"])
            self.desc_edit.setPlainText(self.zone_data.get("description", ""))

    def _on_ok(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        area_id = self.area_combo.currentData()
        
        if not area_id:
            QMessageBox.warning(self, "提示", "请选择所属洞区")
            return
        if not code:
            QMessageBox.warning(self, "提示", "请输入子区域编号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入子区域名称")
            return
        
        self.accept()

    def get_data(self) -> Dict:
        return {
            "area_id": self.area_combo.currentData(),
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "layer": self.layer_edit.currentText().strip(),
            "elevation": self.elevation_spin.value() if self.elevation_spin.value() != self.elevation_spin.minimum() else None,
            "description": self.desc_edit.toPlainText().strip(),
        }


class CavePanel(QWidget):
    area_selected = Signal(int)
    zone_selected = Signal(int)
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._init_ui()
        self.refresh_areas()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Vertical)
        
        area_group = QGroupBox("洞区管理")
        area_layout = QVBoxLayout(area_group)
        
        btn_layout1 = QHBoxLayout()
        self.add_area_btn = QPushButton("新增洞区")
        self.edit_area_btn = QPushButton("编辑洞区")
        self.delete_area_btn = QPushButton("删除洞区")
        self.joint_analysis_btn = QPushButton("联合分析")
        self.area_stat_btn = QPushButton("区域统计")
        self.add_area_btn.clicked.connect(self._on_add_area)
        self.edit_area_btn.clicked.connect(self._on_edit_area)
        self.delete_area_btn.clicked.connect(self._on_delete_area)
        self.joint_analysis_btn.clicked.connect(self._on_joint_analysis)
        self.area_stat_btn.clicked.connect(self._on_area_stats)
        btn_layout1.addWidget(self.add_area_btn)
        btn_layout1.addWidget(self.edit_area_btn)
        btn_layout1.addWidget(self.delete_area_btn)
        btn_layout1.addStretch()
        btn_layout1.addWidget(self.area_stat_btn)
        btn_layout1.addWidget(self.joint_analysis_btn)
        area_layout.addLayout(btn_layout1)
        
        self.area_table = QTableWidget()
        self.area_table.setColumnCount(6)
        self.area_table.setHorizontalHeaderLabels(["ID", "编号", "名称", "子区域数", "滴水点数", "数据量"])
        self.area_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.area_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.area_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.area_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.area_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.area_table.itemSelectionChanged.connect(self._on_area_selection_changed)
        self.area_table.cellDoubleClicked.connect(self._on_edit_area)
        area_layout.addWidget(self.area_table)
        
        splitter.addWidget(area_group)
        
        zone_group = QGroupBox("子区域管理")
        zone_layout = QVBoxLayout(zone_group)
        
        btn_layout2 = QHBoxLayout()
        self.add_zone_btn = QPushButton("新增子区域")
        self.edit_zone_btn = QPushButton("编辑子区域")
        self.delete_zone_btn = QPushButton("删除子区域")
        self.add_zone_btn.clicked.connect(self._on_add_zone)
        self.edit_zone_btn.clicked.connect(self._on_edit_zone)
        self.delete_zone_btn.clicked.connect(self._on_delete_zone)
        btn_layout2.addWidget(self.add_zone_btn)
        btn_layout2.addWidget(self.edit_zone_btn)
        btn_layout2.addWidget(self.delete_zone_btn)
        btn_layout2.addStretch()
        zone_layout.addLayout(btn_layout2)
        
        self.zone_table = QTableWidget()
        self.zone_table.setColumnCount(7)
        self.zone_table.setHorizontalHeaderLabels(["ID", "所属洞区", "编号", "名称", "分层", "海拔", "滴水点数"])
        self.zone_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.zone_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.zone_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.zone_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.zone_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.zone_table.itemSelectionChanged.connect(self._on_zone_selection_changed)
        self.zone_table.cellDoubleClicked.connect(self._on_edit_zone)
        zone_layout.addWidget(self.zone_table)
        
        splitter.addWidget(zone_group)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def refresh_areas(self):
        areas = self.db.get_all_cave_areas()
        self.area_table.setRowCount(len(areas))
        
        for row, area in enumerate(areas):
            stats = self.db.get_cave_area_stats(area["id"])
            
            self.area_table.setItem(row, 0, QTableWidgetItem(str(area["id"])))
            self.area_table.setItem(row, 1, QTableWidgetItem(area["code"]))
            
            name_item = QTableWidgetItem(area["name"])
            if area.get("geological_type"):
                name_item.setToolTip(f"地质类型: {area['geological_type']}")
            self.area_table.setItem(row, 2, name_item)
            
            zone_count = stats.get("zone_count", 0)
            point_count = stats.get("point_count", 0)
            data_count = stats.get("data_count", 0)
            
            z_item = QTableWidgetItem(str(zone_count))
            p_item = QTableWidgetItem(str(point_count))
            d_item = QTableWidgetItem(str(data_count))
            
            if point_count > 0:
                p_item.setForeground(QColor("#1f77b4"))
                p_item.setBackground(QBrush(QColor("#1f77b4").lighter(190)))
            if data_count > 0:
                d_item.setForeground(QColor("#2ca02c"))
            
            self.area_table.setItem(row, 3, z_item)
            self.area_table.setItem(row, 4, p_item)
            self.area_table.setItem(row, 5, d_item)
            
            for col in range(6):
                item = self.area_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
        
        self.edit_area_btn.setEnabled(False)
        self.delete_area_btn.setEnabled(False)
        self.joint_analysis_btn.setEnabled(False)
        self.area_stat_btn.setEnabled(False)
        self.refresh_zones()

    def refresh_zones(self, area_id: Optional[int] = None):
        if area_id is not None:
            zones = self.db.get_zones_by_area(area_id)
        else:
            zones = []
            areas = self.db.get_all_cave_areas()
            for a in areas:
                zones.extend(self.db.get_zones_by_area(a["id"]))
        
        self.zone_table.setRowCount(len(zones))
        
        for row, zone in enumerate(zones):
            point_count = len(self.db.get_drip_points_by_zone(zone["id"]))
            
            self.zone_table.setItem(row, 0, QTableWidgetItem(str(zone["id"])))
            self.zone_table.setItem(row, 1, QTableWidgetItem(zone.get("area_code", "-")))
            self.zone_table.setItem(row, 2, QTableWidgetItem(zone["code"]))
            self.zone_table.setItem(row, 3, QTableWidgetItem(zone["name"]))
            self.zone_table.setItem(row, 4, QTableWidgetItem(zone.get("layer", "-")))
            self.zone_table.setItem(row, 5, QTableWidgetItem(f"{zone['elevation']:.1f} m" if zone.get("elevation") is not None else "-"))
            
            p_item = QTableWidgetItem(str(point_count))
            if point_count > 0:
                p_item.setForeground(QColor("#1f77b4"))
            self.zone_table.setItem(row, 6, p_item)
            
            for col in range(7):
                item = self.zone_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
        
        self.edit_zone_btn.setEnabled(False)
        self.delete_zone_btn.setEnabled(False)

    def _on_area_selection_changed(self):
        has_selection = len(self.area_table.selectedItems()) > 0
        self.edit_area_btn.setEnabled(has_selection)
        self.delete_area_btn.setEnabled(has_selection)
        self.joint_analysis_btn.setEnabled(has_selection)
        self.area_stat_btn.setEnabled(has_selection)
        
        if has_selection:
            row = self.area_table.currentRow()
            area_id = int(self.area_table.item(row, 0).text())
            self.refresh_zones(area_id)
            self.area_selected.emit(area_id)

    def _on_zone_selection_changed(self):
        has_selection = len(self.zone_table.selectedItems()) > 0
        self.edit_zone_btn.setEnabled(has_selection)
        self.delete_zone_btn.setEnabled(has_selection)
        
        if has_selection:
            row = self.zone_table.currentRow()
            zone_id = int(self.zone_table.item(row, 0).text())
            self.zone_selected.emit(zone_id)

    def _get_selected_area(self) -> Optional[Dict]:
        row = self.area_table.currentRow()
        if row < 0:
            return None
        area_id = int(self.area_table.item(row, 0).text())
        return self.db.get_cave_area(area_id)

    def _get_selected_zone(self) -> Optional[Dict]:
        row = self.zone_table.currentRow()
        if row < 0:
            return None
        zone_id = int(self.zone_table.item(row, 0).text())
        return self.db.get_cave_zone(zone_id)

    def _on_add_area(self):
        dialog = CaveAreaDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, area_id = self.db.add_cave_area(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_area(self):
        area = self._get_selected_area()
        if not area:
            return
        
        dialog = CaveAreaDialog(self, area)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_cave_area(area["id"], **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_area(self):
        area = self._get_selected_area()
        if not area:
            return
        
        stats = self.db.get_cave_area_stats(area["id"])
        if stats.get("point_count", 0) > 0:
            QMessageBox.warning(self, "提示", 
                f"该洞区已有 {stats['point_count']} 个滴水点，禁止删除。\n请先删除或迁移相关滴水点。")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除洞区 [{area['code']} - {area['name']}] 吗？\n"
            f"其下的 {stats.get('zone_count', 0)} 个子区域也将被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_cave_area(area["id"])
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_add_zone(self):
        area = self._get_selected_area()
        dialog = CaveZoneDialog(self, area_id=area["id"] if area else None)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, zone_id = self.db.add_cave_zone(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_zone(self):
        zone = self._get_selected_zone()
        if not zone:
            return
        
        dialog = CaveZoneDialog(self, zone)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_cave_zone(zone["id"], **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_zone(self):
        zone = self._get_selected_zone()
        if not zone:
            return
        
        point_count = len(self.db.get_drip_points_by_zone(zone["id"]))
        if point_count > 0:
            QMessageBox.warning(self, "提示", 
                f"该子区域已有 {point_count} 个滴水点，禁止删除。\n请先删除或迁移相关滴水点。")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除子区域 [{zone['code']} - {zone['name']}] 吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_cave_zone(zone["id"])
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh_areas()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_joint_analysis(self):
        area = self._get_selected_area()
        if not area:
            return
        
        points = self.db.get_drip_points_by_area(area["id"])
        if len(points) < 2:
            QMessageBox.information(self, "提示", "该洞区至少需要2个滴水点才能进行联合分析")
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
            QMessageBox.information(self, "提示", "有数据的滴水点不足2个，请先导入数据")
            return
        
        result = AdvancedAnomalyDetector.joint_analysis(
            area["id"], f"{area['code']} - {area['name']}", points_data
        )
        
        msg = f"【{result.area_name}】联合分析结果\n\n"
        msg += f"综合风险等级: {result.combined_risk_level}\n"
        msg += f"分析点位数量: {result.anomaly_summary['total_points']}\n"
        msg += f"累计异常数量: {result.anomaly_summary['total_anomalies']}\n"
        msg += f"高风险点位: {result.anomaly_summary['high_risk_points']}\n"
        msg += f"高相关性配对: {result.anomaly_summary['high_correlation_pairs']}\n\n"
        msg += "【各点位分析】\n"
        for pr in result.point_results:
            msg += f"  {pr.point_code}: {pr.trend} | 异常{pr.anomaly_count}个 | 均值{pr.avg_interval:.1f}s\n"
        
        if result.recommendations:
            msg += "\n【建议】\n"
            for rec in result.recommendations:
                msg += f"  • {rec}\n"
        
        box = QMessageBox(self)
        box.setWindowTitle("联合分析结果")
        box.setText(msg)
        box.setDetailedText(self._get_detailed_correlation(result))
        box.exec()

    def _get_detailed_correlation(self, result) -> str:
        text = "【相关性矩阵】\n"
        for (pid1, pid2), corr in result.correlation_matrix.items():
            code1 = next((pr.point_code for pr in result.point_results if pr.point_id == pid1), str(pid1))
            code2 = next((pr.point_code for pr in result.point_results if pr.point_id == pid2), str(pid2))
            level = "高" if abs(corr) > 0.7 else ("中" if abs(corr) > 0.4 else "低")
            text += f"{code1} - {code2}: 相关系数 {corr:.3f} ({level}相关)\n"
        return text

    def _on_area_stats(self):
        area = self._get_selected_area()
        if not area:
            return
        
        stats = self.db.get_cave_area_stats(area["id"])
        points = self.db.get_drip_points_by_area(area["id"])
        
        msg = f"【{area['code']} - {area['name']}】区域统计\n\n"
        msg += f"子区域数量: {stats.get('zone_count', 0)}\n"
        msg += f"滴水点数量: {stats.get('point_count', 0)}\n"
        msg += f"监测数据总量: {stats.get('data_count', 0)} 条\n\n"
        
        if points:
            msg += "【滴水点列表】\n"
            for p in points:
                count = self.db.get_monitoring_data_count(p["id"])
                msg += f"  {p['code']} - {p['name']}: {count} 条数据\n"
        
        QMessageBox.information(self, "区域统计", msg)
