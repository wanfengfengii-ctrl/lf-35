from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QComboBox, QAbstractItemView, QSplitter,
    QTabWidget, QListWidget, QListWidgetItem, QDateEdit, QSpinBox,
    QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import (
    ROUTE_ASSIGNMENT_STATUSES, ROUTE_ASSIGNMENT_STATUS_NAMES,
    ROUTE_ASSIGNMENT_STATUS_COLORS, USER_ROLES
)


class RouteDialog(QDialog):
    def __init__(self, parent=None, route_data: Optional[Dict] = None):
        super().__init__(parent)
        self.route_data = route_data
        self.db = get_db()
        self.setWindowTitle("编辑路线" if route_data else "新建路线")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self._init_ui()
        if route_data:
            self._load_data()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("路线编号（如：RT-001）")
        layout.addRow("路线编号 *:", self.code_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("路线名称")
        layout.addRow("路线名称 *:", self.name_edit)

        self.area_combo = QComboBox()
        self.area_combo.addItem("请选择洞区", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        layout.addRow("所属洞区:", self.area_combo)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("路线描述")
        self.desc_edit.setMaximumHeight(80)
        layout.addRow("路线描述:", self.desc_edit)

        self.created_by_edit = QLineEdit()
        self.created_by_edit.setPlaceholderText("创建人")
        layout.addRow("创建人:", self.created_by_edit)

        point_group = QGroupBox("路线点位（可调整顺序）")
        point_layout = QVBoxLayout(point_group)

        point_select_row = QHBoxLayout()
        self.point_combo = QComboBox()
        self.point_combo.addItem("请选择滴水点", None)
        self._refresh_point_combo()
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        point_select_row.addWidget(self.point_combo, stretch=1)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 300)
        self.duration_spin.setValue(15)
        self.duration_spin.setSuffix(" 分钟")
        point_select_row.addWidget(QLabel("预计时长:"))
        point_select_row.addWidget(self.duration_spin)

        add_point_btn = QPushButton("添加点位")
        add_point_btn.clicked.connect(self._on_add_point)
        point_select_row.addWidget(add_point_btn)
        point_layout.addLayout(point_select_row)

        self.point_list = QListWidget()
        self.point_list.setSelectionMode(QAbstractItemView.SingleSelection)
        point_layout.addWidget(self.point_list, stretch=1)

        btn_row = QHBoxLayout()
        up_btn = QPushButton("↑ 上移")
        up_btn.clicked.connect(self._on_move_up)
        down_btn = QPushButton("↓ 下移")
        down_btn.clicked.connect(self._on_move_down)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._on_delete_point)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        point_layout.addLayout(btn_row)

        layout.addRow(point_group)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def _refresh_point_combo(self):
        area_id = self.area_combo.currentData()
        self.point_combo.clear()
        self.point_combo.addItem("请选择滴水点", None)
        
        if area_id:
            points = self.db.get_drip_points_by_area(area_id)
        else:
            points = self.db.get_all_drip_points()
        
        for p in points:
            self.point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])

    def _on_area_changed(self):
        self._refresh_point_combo()

    def _on_add_point(self):
        point_id = self.point_combo.currentData()
        if not point_id:
            QMessageBox.warning(self, "提示", "请选择一个滴水点")
            return
        
        for i in range(self.point_list.count()):
            item = self.point_list.item(i)
            data = item.data(Qt.UserRole)
            if data.get("drip_point_id") == point_id:
                QMessageBox.warning(self, "提示", "该点位已在路线中")
                return
        
        point_data = self.db.get_drip_point(point_id)
        duration = self.duration_spin.value()
        
        item = QListWidgetItem(
            f"[{self.point_list.count() + 1}] {point_data['code']} - {point_data['name']}  (预计 {duration} 分钟)"
        )
        item.setData(Qt.UserRole, {
            "drip_point_id": point_id,
            "duration": duration,
            "code": point_data["code"],
            "name": point_data["name"]
        })
        self.point_list.addItem(item)

    def _on_move_up(self):
        row = self.point_list.currentRow()
        if row > 0:
            item = self.point_list.takeItem(row)
            self.point_list.insertItem(row - 1, item)
            self._update_sequence_numbers()

    def _on_move_down(self):
        row = self.point_list.currentRow()
        if row < self.point_list.count() - 1:
            item = self.point_list.takeItem(row)
            self.point_list.insertItem(row + 1, item)
            self._update_sequence_numbers()

    def _on_delete_point(self):
        row = self.point_list.currentRow()
        if row >= 0:
            self.point_list.takeItem(row)
            self._update_sequence_numbers()

    def _update_sequence_numbers(self):
        for i in range(self.point_list.count()):
            item = self.point_list.item(i)
            data = item.data(Qt.UserRole)
            item.setText(
                f"[{i + 1}] {data['code']} - {data['name']}  (预计 {data['duration']} 分钟)"
            )

    def _load_data(self):
        if not self.route_data:
            return
        self.code_edit.setText(self.route_data.get("route_code", ""))
        self.name_edit.setText(self.route_data.get("route_name", ""))
        self.desc_edit.setPlainText(self.route_data.get("description", ""))
        self.created_by_edit.setText(self.route_data.get("created_by", ""))
        
        area_id = self.route_data.get("area_id")
        if area_id:
            idx = self.area_combo.findData(area_id)
            if idx >= 0:
                self.area_combo.setCurrentIndex(idx)
        
        route_points = self.db.get_route_points(self.route_data["id"])
        for rp in route_points:
            item = QListWidgetItem(
                f"[{rp['sequence']}] {rp['drip_point_code']} - {rp['drip_point_name']}  (预计 {rp.get('estimated_duration', 15)} 分钟)"
            )
            item.setData(Qt.UserRole, {
                "drip_point_id": rp["drip_point_id"],
                "duration": rp.get("estimated_duration", 15),
                "code": rp["drip_point_code"],
                "name": rp["drip_point_name"]
            })
            self.point_list.addItem(item)

    def _on_ok(self):
        code = self.code_edit.text().strip()
        name = self.name_edit.text().strip()
        if not code:
            QMessageBox.warning(self, "提示", "请输入路线编号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入路线名称")
            return
        if self.point_list.count() == 0:
            QMessageBox.warning(self, "提示", "请至少添加一个点位")
            return
        self.accept()

    def get_data(self) -> Dict:
        points = []
        for i in range(self.point_list.count()):
            item = self.point_list.item(i)
            data = item.data(Qt.UserRole)
            points.append({
                "drip_point_id": data["drip_point_id"],
                "sequence": i + 1,
                "estimated_duration": data["duration"]
            })
        
        return {
            "route_code": self.code_edit.text().strip(),
            "route_name": self.name_edit.text().strip(),
            "area_id": self.area_combo.currentData(),
            "description": self.desc_edit.toPlainText().strip(),
            "created_by": self.created_by_edit.text().strip(),
            "points": points
        }


class RouteAssignmentDialog(QDialog):
    def __init__(self, parent=None, route_id: Optional[int] = None):
        super().__init__(parent)
        self.route_id = route_id
        self.db = get_db()
        self.setWindowTitle("分配巡检路线")
        self.setMinimumWidth(400)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.route_combo = QComboBox()
        routes = self.db.get_all_inspection_routes()
        self.route_combo.addItem("请选择路线", None)
        for r in routes:
            self.route_combo.addItem(f"{r['route_code']} - {r['route_name']}", r["id"])
        if self.route_id:
            idx = self.route_combo.findData(self.route_id)
            if idx >= 0:
                self.route_combo.setCurrentIndex(idx)
        layout.addRow("巡检路线 *:", self.route_combo)

        users = self.db.get_all_users(role="inspector")
        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("请选择巡检人员", None)
        for u in users:
            self.assignee_combo.addItem(u["real_name"], u["real_name"])
        layout.addRow("巡检人员 *:", self.assignee_combo)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        layout.addRow("计划日期 *:", self.date_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("备注信息")
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

    def _on_ok(self):
        route_id = self.route_combo.currentData()
        assignee = self.assignee_combo.currentData()
        if not route_id:
            QMessageBox.warning(self, "提示", "请选择巡检路线")
            return
        if not assignee:
            QMessageBox.warning(self, "提示", "请选择巡检人员")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "route_id": self.route_combo.currentData(),
            "assignee": self.assignee_combo.currentData(),
            "plan_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "notes": self.notes_edit.toPlainText().strip()
        }


class RoutePanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.current_route_id: Optional[int] = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)

        self.area_filter = QComboBox()
        self.area_filter.addItem("全部洞区", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_filter.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("洞区:"))
        filter_layout.addWidget(self.area_filter)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索路线编号/名称")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_edit)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Horizontal)

        route_group = QGroupBox("巡检路线")
        route_layout = QVBoxLayout(route_group)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建路线")
        self.add_btn.clicked.connect(self._on_add_route)
        self.edit_btn = QPushButton("编辑路线")
        self.edit_btn.clicked.connect(self._on_edit_route)
        self.edit_btn.setEnabled(False)
        self.delete_btn = QPushButton("删除路线")
        self.delete_btn.clicked.connect(self._on_delete_route)
        self.delete_btn.setEnabled(False)
        self.assign_btn = QPushButton("分配路线")
        self.assign_btn.clicked.connect(self._on_assign_route)
        self.assign_btn.setEnabled(False)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.assign_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        route_layout.addLayout(btn_layout)

        self.route_table = QTableWidget()
        self.route_table.setColumnCount(6)
        self.route_table.setHorizontalHeaderLabels([
            "ID", "路线编号", "路线名称", "洞区", "点位数量", "创建时间"
        ])
        self.route_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.route_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.route_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.route_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.route_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.route_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.route_table.itemSelectionChanged.connect(self._on_route_selected)
        self.route_table.itemDoubleClicked.connect(self._on_edit_route)
        route_layout.addWidget(self.route_table)

        splitter.addWidget(route_group)

        right_group = QGroupBox("路线详情与分配记录")
        right_layout = QVBoxLayout(right_group)

        self.detail_tabs = QTabWidget()

        points_tab = QWidget()
        points_layout = QVBoxLayout(points_tab)
        points_layout.addWidget(QLabel("路线点位:"))
        self.point_table = QTableWidget()
        self.point_table.setColumnCount(5)
        self.point_table.setHorizontalHeaderLabels([
            "顺序", "点位编号", "点位名称", "预计时长(分钟)", "位置"
        ])
        self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.point_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.point_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        points_layout.addWidget(self.point_table)
        self.detail_tabs.addTab(points_tab, "路线点位")

        assignment_tab = QWidget()
        assignment_layout = QVBoxLayout(assignment_tab)
        assignment_btn_row = QHBoxLayout()
        assignment_btn_row.addWidget(QLabel("分配记录:"))
        self.add_assignment_btn = QPushButton("新增分配")
        self.add_assignment_btn.clicked.connect(self._on_assign_route)
        self.add_assignment_btn.setEnabled(False)
        assignment_btn_row.addStretch()
        assignment_btn_row.addWidget(self.add_assignment_btn)
        assignment_layout.addLayout(assignment_btn_row)

        self.assignment_table = QTableWidget()
        self.assignment_table.setColumnCount(6)
        self.assignment_table.setHorizontalHeaderLabels([
            "ID", "巡检人员", "计划日期", "状态", "完成进度", "创建时间"
        ])
        self.assignment_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.assignment_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.assignment_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        assignment_layout.addWidget(self.assignment_table)
        self.detail_tabs.addTab(assignment_tab, "分配记录")

        right_layout.addWidget(self.detail_tabs)
        splitter.addWidget(right_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        area_id = self.area_filter.currentData()
        search = self.search_edit.text().strip().lower()

        routes = self.db.get_all_inspection_routes(area_id=area_id)
        
        if search:
            routes = [r for r in routes if search in r.get("route_code", "").lower()
                      or search in r.get("route_name", "").lower()]

        self.route_table.setRowCount(len(routes))
        for row, route in enumerate(routes):
            self.route_table.setItem(row, 0, QTableWidgetItem(str(route["id"])))
            self.route_table.setItem(row, 1, QTableWidgetItem(route.get("route_code", "-")))
            self.route_table.setItem(row, 2, QTableWidgetItem(route.get("route_name", "-")))
            self.route_table.setItem(row, 3, QTableWidgetItem(
                f"{route.get('area_code', '')} - {route.get('area_name', '')}" if route.get('area_code') else "-"
            ))
            
            points = self.db.get_route_points(route["id"])
            self.route_table.setItem(row, 4, QTableWidgetItem(str(len(points))))
            
            self.route_table.setItem(row, 5, QTableWidgetItem(route.get("created_at", "-")))
            
            for col in range(6):
                item = self.route_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self._clear_details()

    def _on_route_selected(self):
        has = len(self.route_table.selectedItems()) > 0
        self.edit_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)
        self.assign_btn.setEnabled(has)
        self.add_assignment_btn.setEnabled(has)
        
        if has:
            row = self.route_table.currentRow()
            self.current_route_id = int(self.route_table.item(row, 0).text())
            self._load_route_details()
        else:
            self.current_route_id = None
            self._clear_details()

    def _clear_details(self):
        self.point_table.setRowCount(0)
        self.assignment_table.setRowCount(0)

    def _load_route_details(self):
        if not self.current_route_id:
            return
        
        points = self.db.get_route_points(self.current_route_id)
        self.point_table.setRowCount(len(points))
        total_duration = 0
        for row, p in enumerate(points):
            self.point_table.setItem(row, 0, QTableWidgetItem(str(p.get("sequence", row + 1))))
            self.point_table.setItem(row, 1, QTableWidgetItem(p.get("drip_point_code", "-")))
            self.point_table.setItem(row, 2, QTableWidgetItem(p.get("drip_point_name", "-")))
            duration = p.get("estimated_duration", 15)
            total_duration += duration
            self.point_table.setItem(row, 3, QTableWidgetItem(str(duration)))
            self.point_table.setItem(row, 4, QTableWidgetItem(p.get("location", "-")))
            
            for col in range(5):
                item = self.point_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        assignments = self.db.get_route_assignments()
        route_assignments = [a for a in assignments if a.get("route_id") == self.current_route_id]
        self.assignment_table.setRowCount(len(route_assignments))
        for row, a in enumerate(route_assignments):
            self.assignment_table.setItem(row, 0, QTableWidgetItem(str(a["id"])))
            self.assignment_table.setItem(row, 1, QTableWidgetItem(a.get("assignee", "-")))
            self.assignment_table.setItem(row, 2, QTableWidgetItem(a.get("plan_date", "-")))
            
            status_val = a.get("status", "pending")
            status_item = QTableWidgetItem(ROUTE_ASSIGNMENT_STATUS_NAMES.get(status_val, status_val))
            status_color = QColor(ROUTE_ASSIGNMENT_STATUS_COLORS.get(status_val, "#000"))
            status_item.setForeground(status_color)
            self.assignment_table.setItem(row, 3, status_item)
            
            completed = a.get("completed_count", 0)
            total = a.get("total_count", 0)
            progress = f"{completed}/{total}" if total > 0 else "-"
            self.assignment_table.setItem(row, 4, QTableWidgetItem(progress))
            
            self.assignment_table.setItem(row, 5, QTableWidgetItem(a.get("created_at", "-")))
            
            for col in range(6):
                item = self.assignment_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_add_route(self):
        dialog = RouteDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            points = data.pop("points", [])
            success, msg, route_id = self.db.add_inspection_route(
                route_name=data["route_name"],
                route_code=data["route_code"],
                area_id=data["area_id"],
                description=data["description"],
                created_by=data["created_by"]
            )
            if success and route_id:
                for p in points:
                    self.db.add_route_point(
                        route_id=route_id,
                        drip_point_id=p["drip_point_id"],
                        sequence=p["sequence"],
                        estimated_duration=p["estimated_duration"]
                    )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_route(self):
        if not self.current_route_id:
            return
        route = self.db.get_inspection_route(self.current_route_id)
        if not route:
            return
        
        dialog = RouteDialog(self, route_data=route)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            points = data.pop("points", [])
            
            success, msg = self.db.update_inspection_route(
                self.current_route_id,
                route_name=data["route_name"],
                route_code=data["route_code"],
                area_id=data["area_id"],
                description=data["description"]
            )
            
            if success:
                existing_points = self.db.get_route_points(self.current_route_id)
                for ep in existing_points:
                    self.db.delete_route_point(ep["id"])
                
                for p in points:
                    self.db.add_route_point(
                        route_id=self.current_route_id,
                        drip_point_id=p["drip_point_id"],
                        sequence=p["sequence"],
                        estimated_duration=p["estimated_duration"]
                    )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_route(self):
        if not self.current_route_id:
            return
        route = self.db.get_inspection_route(self.current_route_id)
        if not route:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除路线 [{route.get('route_code', '')} - {route.get('route_name', '')}] 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_inspection_route(self.current_route_id)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_assign_route(self):
        if not self.current_route_id:
            return
        
        dialog = RouteAssignmentDialog(self, route_id=self.current_route_id)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_route_assignment(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self._load_route_details()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)
