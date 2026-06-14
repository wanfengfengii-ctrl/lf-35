from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QComboBox, QDateEdit, QAbstractItemView, QSplitter,
    QTabWidget, QFileDialog, QListWidget, QListWidgetItem, QDateTimeEdit,
    QFrame, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QDate, QDateTime, QTimer
from PySide6.QtGui import QColor, QBrush, QDesktopServices, QFont
from PySide6.QtCore import QUrl

from database.db_manager import get_db
from core.anomaly_detector import (
    ANOMALY_TYPES, RISK_LEVELS, ANOMALY_TYPE_NAMES,
    WORK_ORDER_STATUSES, WORK_ORDER_STATUS_COLORS,
    WORK_ORDER_PRIORITIES, WORK_ORDER_PRIORITY_COLORS,
    WORK_ORDER_STATUS_FLOW, WORK_ORDER_NEEDS_APPROVAL_PRIORITIES,
    ESCALATION_LEVELS, ESCALATION_LEVEL_NAMES, ESCALATION_LEVEL_COLORS,
    REMINDER_TYPES, REMINDER_TYPE_NAMES, REMINDER_TYPE_COLORS,
    WORK_ORDER_ACTION_TYPES, APPROVAL_STATUSES
)
import os


class WorkOrderDialog(QDialog):
    def __init__(self, parent=None, order_data: Optional[Dict] = None,
                 anomaly_id: Optional[int] = None):
        super().__init__(parent)
        self.order_data = order_data
        self.anomaly_id = anomaly_id
        self.db = get_db()
        self.setWindowTitle("编辑工单" if order_data else "新建工单")
        self.setMinimumWidth(650)
        self.setMinimumHeight(700)
        self._init_ui()
        if order_data:
            self._load_data()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("工单标题")
        layout.addRow("工单标题 *:", self.title_edit)

        point_row = QHBoxLayout()
        self.area_combo = QComboBox()
        self.area_combo.addItem("请选择洞区", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_combo.currentIndexChanged.connect(self._on_area_changed)
        point_row.addWidget(QLabel("洞区:"))
        point_row.addWidget(self.area_combo)

        self.point_combo = QComboBox()
        self.point_combo.addItem("请选择滴水点", None)
        point_row.addWidget(QLabel("滴水点:"))
        point_row.addWidget(self.point_combo)
        point_row.addStretch()
        layout.addRow("关联位置:", point_row)

        info_row = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItem("请选择", None)
        for type_key, type_name in ANOMALY_TYPES.items():
            self.type_combo.addItem(type_name, type_key)
        info_row.addWidget(QLabel("异常类型:"))
        info_row.addWidget(self.type_combo)

        self.risk_combo = QComboBox()
        for level in RISK_LEVELS:
            self.risk_combo.addItem(level, level)
        self.risk_combo.setCurrentText("中")
        info_row.addWidget(QLabel("风险等级:"))
        info_row.addWidget(self.risk_combo)
        info_row.addStretch()
        layout.addRow("异常信息:", info_row)

        assign_row = QHBoxLayout()
        self.assignee_edit = QLineEdit()
        self.assignee_edit.setPlaceholderText("责任人姓名")
        assign_row.addWidget(QLabel("责任人:"))
        assign_row.addWidget(self.assignee_edit)

        self.priority_combo = QComboBox()
        for p in WORK_ORDER_PRIORITIES:
            self.priority_combo.addItem(p, p)
        self.priority_combo.setCurrentText("普通")
        assign_row.addWidget(QLabel("优先级:"))
        assign_row.addWidget(self.priority_combo)
        layout.addRow("分配信息:", assign_row)

        time_row = QHBoxLayout()
        self.plan_time_edit = QDateTimeEdit()
        self.plan_time_edit.setCalendarPopup(True)
        self.plan_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.plan_time_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        time_row.addWidget(QLabel("计划巡检时间:"))
        time_row.addWidget(self.plan_time_edit)

        self.arrive_time_edit = QDateTimeEdit()
        self.arrive_time_edit.setCalendarPopup(True)
        self.arrive_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.arrive_time_edit.setMinimumDateTime(QDateTime.fromString("1900-01-01 00:00", "yyyy-MM-dd HH:mm"))
        self.arrive_time_edit.setDateTime(self.arrive_time_edit.minimumDateTime())
        self.arrive_time_edit.setSpecialValueText("未到场")
        self.arrive_time_edit.setEnabled(False)
        time_row.addWidget(QLabel("实际到场时间:"))
        time_row.addWidget(self.arrive_time_edit)
        layout.addRow("时间安排:", time_row)

        self.status_combo = QComboBox()
        for status in WORK_ORDER_STATUSES:
            self.status_combo.addItem(status, status)
        self.status_combo.setCurrentText("待处理")
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        layout.addRow("工单状态:", self.status_combo)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("问题描述")
        self.desc_edit.setMaximumHeight(80)
        layout.addRow("问题描述:", self.desc_edit)

        self.inspection_edit = QTextEdit()
        self.inspection_edit.setPlaceholderText("巡检内容")
        self.inspection_edit.setMaximumHeight(80)
        layout.addRow("巡检内容:", self.inspection_edit)

        self.measures_edit = QTextEdit()
        self.measures_edit.setPlaceholderText("处理措施")
        self.measures_edit.setMaximumHeight(80)
        layout.addRow("处理措施:", self.measures_edit)

        self.recheck_edit = QTextEdit()
        self.recheck_edit.setPlaceholderText("复检结论")
        self.recheck_edit.setMaximumHeight(60)
        layout.addRow("复检结论:", self.recheck_edit)

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

        scroll.setWidget(content)
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def _on_area_changed(self):
        area_id = self.area_combo.currentData()
        self._refresh_point_combo(area_id)

    def _on_status_changed(self):
        status = self.status_combo.currentData()
        if status and status in ("处理中", "待复检", "已完成", "已关闭"):
            self.arrive_time_edit.setEnabled(True)
            if self.arrive_time_edit.dateTime() == self.arrive_time_edit.minimumDateTime():
                self.arrive_time_edit.setDateTime(QDateTime.currentDateTime())
        else:
            self.arrive_time_edit.setEnabled(False)
            self.arrive_time_edit.setDateTime(self.arrive_time_edit.minimumDateTime())

    def _load_data(self):
        if not self.order_data:
            return
        self.title_edit.setText(self.order_data.get("title", ""))

        area_id = self.order_data.get("area_id")
        point_id = self.order_data.get("drip_point_id")

        if not area_id and point_id:
            pt = self.db.get_drip_point(point_id)
            if pt and pt.get("area_id"):
                area_id = pt["area_id"]

        self.area_combo.blockSignals(True)
        if area_id:
            idx = self.area_combo.findData(area_id)
            if idx >= 0:
                self.area_combo.setCurrentIndex(idx)
                self._refresh_point_combo(area_id)
                if point_id:
                    p_idx = self.point_combo.findData(point_id)
                    if p_idx >= 0:
                        self.point_combo.setCurrentIndex(p_idx)
        self.area_combo.blockSignals(False)

        anomaly_type = self.order_data.get("anomaly_type", "")
        type_map = {v: k for k, v in ANOMALY_TYPES.items()}
        type_key = type_map.get(anomaly_type, anomaly_type)
        idx = self.type_combo.findData(type_key)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        risk = self.order_data.get("risk_level", "中")
        idx = self.risk_combo.findData(risk)
        if idx >= 0:
            self.risk_combo.setCurrentIndex(idx)

        self.assignee_edit.setText(self.order_data.get("assignee", ""))

        priority = self.order_data.get("priority", "普通")
        idx = self.priority_combo.findData(priority)
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)

        plan_time = self.order_data.get("plan_inspect_time", "")
        if plan_time:
            dt = QDateTime.fromString(plan_time, "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.plan_time_edit.setDateTime(dt)

        arrive_time = self.order_data.get("actual_arrive_time", "")
        if arrive_time:
            dt = QDateTime.fromString(arrive_time, "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.arrive_time_edit.setDateTime(dt)
                self.arrive_time_edit.setEnabled(True)
        else:
            self.arrive_time_edit.setDateTime(self.arrive_time_edit.minimumDateTime())
            self.arrive_time_edit.setEnabled(False)

        self.status_combo.blockSignals(True)
        status = self.order_data.get("status", "待处理")
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.status_combo.blockSignals(False)

        self.desc_edit.setPlainText(self.order_data.get("description", ""))
        self.inspection_edit.setPlainText(self.order_data.get("inspection_content", ""))
        self.measures_edit.setPlainText(self.order_data.get("measures", ""))
        self.recheck_edit.setPlainText(self.order_data.get("recheck_conclusion", ""))
        self.notes_edit.setPlainText(self.order_data.get("notes", ""))

    def _refresh_point_combo(self, area_id):
        self.point_combo.clear()
        self.point_combo.addItem("请选择滴水点", None)
        if area_id:
            points = self.db.get_drip_points_by_area(area_id)
            for p in points:
                self.point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])

    def _on_ok(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "提示", "请输入工单标题")
            return
        self.accept()

    def get_data(self) -> Dict:
        type_key = self.type_combo.currentData()
        type_name = ANOMALY_TYPES.get(type_key, "") if type_key else ""
        plan_time = self.plan_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        arrive_dt = self.arrive_time_edit.dateTime()
        arrive_time = "" if arrive_dt == self.arrive_time_edit.minimumDateTime() else arrive_dt.toString("yyyy-MM-dd HH:mm:ss")

        return {
            "title": self.title_edit.text().strip(),
            "anomaly_id": self.order_data.get("anomaly_id") if self.order_data else self.anomaly_id,
            "drip_point_id": self.point_combo.currentData(),
            "area_id": self.area_combo.currentData(),
            "zone_id": None,
            "anomaly_type": type_name,
            "risk_level": self.risk_combo.currentData(),
            "assignee": self.assignee_edit.text().strip(),
            "status": self.status_combo.currentData(),
            "priority": self.priority_combo.currentData(),
            "plan_inspect_time": plan_time,
            "actual_arrive_time": arrive_time,
            "description": self.desc_edit.toPlainText().strip(),
            "inspection_content": self.inspection_edit.toPlainText().strip(),
            "measures": self.measures_edit.toPlainText().strip(),
            "recheck_conclusion": self.recheck_edit.toPlainText().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class InspectionRecordDialog(QDialog):
    def __init__(self, parent=None, work_order_id: Optional[int] = None):
        super().__init__(parent)
        self.work_order_id = work_order_id
        self.setWindowTitle("新增巡检记录")
        self.setMinimumWidth(500)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.inspector_edit = QLineEdit()
        self.inspector_edit.setPlaceholderText("巡检人员姓名")
        layout.addRow("巡检人 *:", self.inspector_edit)

        self.inspect_time_edit = QDateTimeEdit()
        self.inspect_time_edit.setCalendarPopup(True)
        self.inspect_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.inspect_time_edit.setDateTime(QDateTime.currentDateTime())
        layout.addRow("巡检时间 *:", self.inspect_time_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("巡检内容描述")
        self.content_edit.setMaximumHeight(80)
        layout.addRow("巡检内容:", self.content_edit)

        self.measures_edit = QTextEdit()
        self.measures_edit.setPlaceholderText("采取的处理措施")
        self.measures_edit.setMaximumHeight(80)
        layout.addRow("处理措施:", self.measures_edit)

        self.result_edit = QLineEdit()
        self.result_edit.setPlaceholderText("处理结果")
        layout.addRow("处理结果:", self.result_edit)

        self.recheck_edit = QLineEdit()
        self.recheck_edit.setPlaceholderText("复检结论")
        layout.addRow("复检结论:", self.recheck_edit)

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

    def _on_ok(self):
        inspector = self.inspector_edit.text().strip()
        if not inspector:
            QMessageBox.warning(self, "提示", "请输入巡检人姓名")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "work_order_id": self.work_order_id,
            "inspector": self.inspector_edit.text().strip(),
            "inspect_time": self.inspect_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "inspection_content": self.content_edit.toPlainText().strip(),
            "measures": self.measures_edit.toPlainText().strip(),
            "result": self.result_edit.text().strip(),
            "recheck_conclusion": self.recheck_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class WorkOrderDetailDialog(QDialog):
    def __init__(self, parent=None, order_id: Optional[int] = None):
        super().__init__(parent)
        self.order_id = order_id
        self.db = get_db()
        self.setWindowTitle("工单详情")
        self.setMinimumWidth(750)
        self.setMinimumHeight(650)
        self._init_ui()
        if order_id:
            self._load_order()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)

        btn_row = QHBoxLayout()
        self.edit_btn = QPushButton("编辑工单")
        self.edit_btn.clicked.connect(self._on_edit)
        self.status_btn = QPushButton("状态流转")
        self.status_btn.clicked.connect(self._on_status_flow)
        self.delete_btn = QPushButton("删除工单")
        self.delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.status_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.delete_btn)
        info_layout.addLayout(btn_row)

        self.tabs.addTab(info_tab, "工单信息")

        inspection_tab = QWidget()
        inspection_layout = QVBoxLayout(inspection_tab)

        insp_btn_row = QHBoxLayout()
        self.add_insp_btn = QPushButton("新增巡检记录")
        self.add_insp_btn.clicked.connect(self._on_add_inspection)
        insp_btn_row.addWidget(self.add_insp_btn)
        insp_btn_row.addStretch()
        inspection_layout.addLayout(insp_btn_row)

        self.insp_table = QTableWidget()
        self.insp_table.setColumnCount(6)
        self.insp_table.setHorizontalHeaderLabels([
            "ID", "巡检人", "巡检时间", "巡检内容", "处理结果", "备注"
        ])
        self.insp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.insp_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.insp_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.insp_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        inspection_layout.addWidget(self.insp_table)

        self.tabs.addTab(inspection_tab, "巡检记录")

        attach_tab = QWidget()
        attach_layout = QVBoxLayout(attach_tab)

        attach_btn_row = QHBoxLayout()
        self.upload_btn = QPushButton("上传附件")
        self.upload_btn.clicked.connect(self._on_upload)
        self.view_btn = QPushButton("打开文件")
        self.view_btn.clicked.connect(self._on_view_attachment)
        self.view_btn.setEnabled(False)
        self.del_attach_btn = QPushButton("删除附件")
        self.del_attach_btn.clicked.connect(self._on_delete_attachment)
        self.del_attach_btn.setEnabled(False)
        attach_btn_row.addWidget(self.upload_btn)
        attach_btn_row.addWidget(self.view_btn)
        attach_btn_row.addWidget(self.del_attach_btn)
        attach_btn_row.addStretch()
        attach_layout.addLayout(attach_btn_row)

        self.attach_list = QListWidget()
        self.attach_list.itemSelectionChanged.connect(self._on_attach_selection_changed)
        attach_layout.addWidget(self.attach_list)

        self.tabs.addTab(attach_tab, "附件")

        main_layout.addWidget(self.tabs)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)

    def _load_order(self):
        if not self.order_id:
            return
        order = self.db.get_work_order(self.order_id)
        if not order:
            return

        info = f"""
        <h3>工单信息</h3>
        <table cellpadding="6" style="border-collapse: collapse;">
        <tr><td><b>工单编号:</b></td><td>{order.get('order_no', '-')}</td>
            <td><b>状态:</b></td><td><span style="color:{WORK_ORDER_STATUS_COLORS.get(order.get('status',''), '#000')}"><b>{order.get('status', '-')}</b></span></td></tr>
        <tr><td><b>标题:</b></td><td colspan="3">{order.get('title', '-')}</td></tr>
        <tr><td><b>洞区:</b></td><td>{order.get('area_code', '-')} - {order.get('area_name', '-')}</td>
            <td><b>滴水点:</b></td><td>{order.get('drip_point_code', '-')} - {order.get('drip_point_name', '-')}</td></tr>
        <tr><td><b>异常类型:</b></td><td>{order.get('anomaly_type', '-')}</td>
            <td><b>风险等级:</b></td><td>{order.get('risk_level', '-')}</td></tr>
        <tr><td><b>责任人:</b></td><td>{order.get('assignee', '-')}</td>
            <td><b>优先级:</b></td><td>{order.get('priority', '-')}</td></tr>
        <tr><td><b>计划巡检:</b></td><td>{order.get('plan_inspect_time', '-')}</td>
            <td><b>实际到场:</b></td><td>{order.get('actual_arrive_time', '-')}</td></tr>
        <tr><td><b>处理时长:</b></td><td>{f"{order.get('handle_duration')} 分钟" if order.get('handle_duration') is not None else '-'}</td>
            <td><b>关闭时间:</b></td><td>{order.get('closed_at', '-')}</td></tr>
        <tr><td><b>创建时间:</b></td><td>{order.get('created_at', '-')}</td>
            <td><b>更新时间:</b></td><td>{order.get('updated_at', '-')}</td></tr>
        </table>
        <h4>问题描述</h4>
        <p>{order.get('description', '-')}</p>
        <h4>巡检内容</h4>
        <p>{order.get('inspection_content', '-')}</p>
        <h4>处理措施</h4>
        <p>{order.get('measures', '-')}</p>
        <h4>复检结论</h4>
        <p>{order.get('recheck_conclusion', '-')}</p>
        <h4>备注</h4>
        <p>{order.get('notes', '-')}</p>
        """
        self.info_text.setHtml(info)

        self._load_inspections()
        self._load_attachments()

    def _load_inspections(self):
        records = self.db.get_inspection_records(self.order_id)
        self.insp_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.insp_table.setItem(row, 0, QTableWidgetItem(str(rec["id"])))
            self.insp_table.setItem(row, 1, QTableWidgetItem(rec.get("inspector", "-")))
            self.insp_table.setItem(row, 2, QTableWidgetItem(rec.get("inspect_time", "-")))
            self.insp_table.setItem(row, 3, QTableWidgetItem(rec.get("inspection_content", "-")))
            self.insp_table.setItem(row, 4, QTableWidgetItem(rec.get("result", "-")))
            self.insp_table.setItem(row, 5, QTableWidgetItem(rec.get("notes", "-")))
            for col in range(6):
                item = self.insp_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _load_attachments(self):
        self.attach_list.clear()
        self.view_btn.setEnabled(False)
        self.del_attach_btn.setEnabled(False)
        attachments = self.db.get_attachments(self.order_id)
        for att in attachments:
            item = QListWidgetItem(f"📎 {att['file_name']} ({self._format_size(att.get('file_size', 0))}) - {att.get('uploaded_at', '')}")
            item.setData(Qt.UserRole, att)
            self.attach_list.addItem(item)

    def _format_size(self, size: Optional[int]) -> str:
        if not size:
            return "未知"
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/(1024*1024):.1f} MB"

    def _on_attach_selection_changed(self):
        has_selection = self.attach_list.currentItem() is not None
        self.view_btn.setEnabled(has_selection)
        self.del_attach_btn.setEnabled(has_selection)

    def _on_edit(self):
        if not self.order_id:
            return
        order = self.db.get_work_order(self.order_id)
        dialog = WorkOrderDialog(self, order_data=order)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_work_order(self.order_id, **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self._load_order()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_status_flow(self):
        if not self.order_id:
            return
        order = self.db.get_work_order(self.order_id)
        if not order:
            return

        current_status = order.get("status", "待处理")
        next_statuses = WORK_ORDER_STATUS_FLOW.get(current_status, [])
        if not next_statuses:
            QMessageBox.information(self, "提示", f"当前状态 [{current_status}] 无可流转状态")
            return

        from PySide6.QtWidgets import QInputDialog
        new_status, ok = QInputDialog.getItem(
            self, "状态流转", f"当前状态: {current_status}\n请选择目标状态:",
            next_statuses, 0, False
        )
        if ok and new_status:
            assignee = order.get("assignee", "")
            success, msg = self.db.update_work_order_status(
                self.order_id, new_status, assignee
            )
            if success:
                QMessageBox.information(self, "成功", msg)
                self._load_order()
                if hasattr(self.parent(), 'data_changed'):
                    pass
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete(self):
        if not self.order_id:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            "确定要删除这个工单吗？相关的巡检记录和附件也会被删除。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_work_order(self.order_id)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_add_inspection(self):
        if not self.order_id:
            return
        dialog = InspectionRecordDialog(self, work_order_id=self.order_id)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_inspection_record(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self._load_inspections()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_upload(self):
        if not self.order_id:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择附件", "", "所有文件 (*.*)"
        )
        if not file_path:
            return

        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_type = os.path.splitext(file_name)[1].lower()

            import shutil
            attach_dir = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "attachments")
            os.makedirs(attach_dir, exist_ok=True)

            import time
            save_name = f"{int(time.time())}_{file_name}"
            save_path = os.path.join(attach_dir, save_name)
            shutil.copy2(file_path, save_path)

            success, msg, _ = self.db.add_attachment(
                work_order_id=self.order_id,
                file_name=file_name,
                file_path=save_path,
                file_size=file_size,
                file_type=file_type
            )
            if success:
                QMessageBox.information(self, "成功", msg)
                self._load_attachments()
            else:
                QMessageBox.warning(self, "失败", msg)
        except Exception as e:
            QMessageBox.warning(self, "失败", f"上传失败: {str(e)}")

    def _on_view_attachment(self):
        item = self.attach_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个附件")
            return
        att = item.data(Qt.UserRole)
        if att and os.path.exists(att["file_path"]):
            QDesktopServices.openUrl(QUrl.fromLocalFile(att["file_path"]))
        else:
            QMessageBox.warning(self, "提示", "文件不存在")

    def _on_delete_attachment(self):
        item = self.attach_list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个附件")
            return
        att = item.data(Qt.UserRole)
        if not att:
            return

        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除附件 [{att['file_name']}] 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_attachment(att["id"])
            if success:
                try:
                    if os.path.exists(att["file_path"]):
                        os.remove(att["file_path"])
                except Exception:
                    pass
                QMessageBox.information(self, "成功", msg)
                self._load_attachments()
            else:
                QMessageBox.warning(self, "失败", msg)


class BatchAssignDialog(QDialog):
    def __init__(self, parent=None, work_order_ids: Optional[List[int]] = None):
        super().__init__(parent)
        self.work_order_ids = work_order_ids or []
        self.db = get_db()
        self.setWindowTitle(f"批量派单 ({len(self.work_order_ids)} 个工单)")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.assignee_combo = QComboBox()
        users = self.db.get_all_users(role="inspector")
        self.assignee_combo.addItem("请选择巡检人员", None)
        for u in users:
            self.assignee_combo.addItem(u["real_name"], u["real_name"])
        layout.addRow("指派给 *:", self.assignee_combo)

        self.plan_time_edit = QDateTimeEdit()
        self.plan_time_edit.setCalendarPopup(True)
        self.plan_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.plan_time_edit.setDateTime(QDateTime.currentDateTime().addDays(1))
        layout.addRow("计划巡检时间 *:", self.plan_time_edit)

        self.priority_combo = QComboBox()
        for p in WORK_ORDER_PRIORITIES:
            self.priority_combo.addItem(p, p)
        self.priority_combo.setCurrentText("普通")
        layout.addRow("优先级:", self.priority_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("派单备注（可选）")
        self.notes_edit.setMaximumHeight(80)
        layout.addRow("备注:", self.notes_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定派单")
        cancel_btn = QPushButton("取消")
        ok_btn.setStyleSheet("QPushButton { background: #409EFF; color: white; border: none; padding: 8px 20px; border-radius: 4px; } QPushButton:hover { background: #66b1ff; }")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _on_ok(self):
        assignee = self.assignee_combo.currentData()
        if not assignee:
            QMessageBox.warning(self, "提示", "请选择巡检人员")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "assignee": self.assignee_combo.currentData(),
            "plan_inspect_time": self.plan_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "priority": self.priority_combo.currentData(),
            "notes": self.notes_edit.toPlainText().strip()
        }


class RecheckReminderDialog(QDialog):
    def __init__(self, parent=None, work_order_id: Optional[int] = None):
        super().__init__(parent)
        self.work_order_id = work_order_id
        self.db = get_db()
        self.setWindowTitle("发送复检提醒")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.recipient_combo = QComboBox()
        users = self.db.get_all_users(role="inspector")
        self.recipient_combo.addItem("请选择提醒对象", None)
        for u in users:
            self.recipient_combo.addItem(u["real_name"], u["real_name"])
        layout.addRow("提醒对象 *:", self.recipient_combo)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_date_edit.setDate(QDate.currentDate().addDays(3))
        layout.addRow("复检截止日期 *:", self.due_date_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("提醒内容，如：请尽快完成以下工单的复检工作...")
        self.content_edit.setPlainText("请尽快完成该工单的复检工作，确认异常已解决。")
        self.content_edit.setMaximumHeight(100)
        layout.addRow("提醒内容 *:", self.content_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("发送提醒")
        cancel_btn = QPushButton("取消")
        ok_btn.setStyleSheet("QPushButton { background: #E6A23C; color: white; border: none; padding: 8px 20px; border-radius: 4px; } QPushButton:hover { background: #f5d76e; }")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _on_ok(self):
        recipient = self.recipient_combo.currentData()
        if not recipient:
            QMessageBox.warning(self, "提示", "请选择提醒对象")
            return
        content = self.content_edit.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "提示", "请输入提醒内容")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "work_order_id": self.work_order_id,
            "recipient": self.recipient_combo.currentData(),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "content": self.content_edit.toPlainText().strip()
        }


class EscalationDialog(QDialog):
    def __init__(self, parent=None, work_order_id: Optional[int] = None, current_level: int = 0):
        super().__init__(parent)
        self.work_order_id = work_order_id
        self.current_level = current_level
        self.db = get_db()
        self.setWindowTitle("工单升级")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        layout = QFormLayout(self)

        current_label = QLabel(f"当前升级级别: <b>{ESCALATION_LEVEL_NAMES.get(self.current_level, '普通')}</b>")
        current_label.setTextFormat(Qt.RichText)
        layout.addRow(current_label)

        next_level = min(self.current_level + 1, 3)
        level_name = ESCALATION_LEVEL_NAMES.get(next_level, "紧急升级")
        level_color = ESCALATION_LEVEL_COLORS.get(next_level, "#F56C6C")
        level_label = QLabel(f"拟升级为: <b><span style='color:{level_color}'>{level_name}</span></b>")
        level_label.setTextFormat(Qt.RichText)
        layout.addRow(level_label)

        self.escalate_to_combo = QComboBox()
        managers = self.db.get_all_users(role="manager")
        self.escalate_to_combo.addItem("请选择上报领导", None)
        for m in managers:
            self.escalate_to_combo.addItem(m["real_name"], m["real_name"])
        layout.addRow("上报给 *:", self.escalate_to_combo)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText("升级原因说明，如：问题复杂、多次处理仍未解决、存在重大安全隐患等...")
        self.reason_edit.setMaximumHeight(100)
        layout.addRow("升级原因 *:", self.reason_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确认升级")
        cancel_btn = QPushButton("取消")
        ok_btn.setStyleSheet("QPushButton { background: #F56C6C; color: white; border: none; padding: 8px 20px; border-radius: 4px; } QPushButton:hover { background: #f78989; }")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def _on_ok(self):
        escalate_to = self.escalate_to_combo.currentData()
        if not escalate_to:
            QMessageBox.warning(self, "提示", "请选择上报领导")
            return
        reason = self.reason_edit.toPlainText().strip()
        if not reason:
            QMessageBox.warning(self, "提示", "请输入升级原因")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "work_order_id": self.work_order_id,
            "new_level": min(self.current_level + 1, 3),
            "escalate_to": self.escalate_to_combo.currentData(),
            "reason": self.reason_edit.toPlainText().strip()
        }


class WorkOrderHistoryDialog(QDialog):
    def __init__(self, parent=None, work_order_id: Optional[int] = None):
        super().__init__(parent)
        self.work_order_id = work_order_id
        self.db = get_db()
        self.setWindowTitle("工单历史记录")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._init_ui()
        self._load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "时间", "操作类型", "操作人", "详情", "备注"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("alternate-background-color: #f5f7fa;")
        layout.addWidget(self.history_table)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _load_history(self):
        if not self.work_order_id:
            return
        history = self.db.get_work_order_history(self.work_order_id)
        self.history_table.setRowCount(len(history))
        
        for row, h in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(h.get("created_at", "-")))
            
            action = h.get("action_type", "")
            action_name = WORK_ORDER_ACTION_TYPES.get(action, action)
            action_item = QTableWidgetItem(action_name)
            
            if action in ("create", "status_change"):
                action_item.setForeground(QColor("#409EFF"))
            elif action == "escalate":
                action_item.setForeground(QColor("#F56C6C"))
                action_item.setFont(QFont("", -1, QFont.Bold))
            elif action == "approve":
                action_item.setForeground(QColor("#67C23A"))
            elif action == "reject":
                action_item.setForeground(QColor("#F56C6C"))
            elif action == "recheck":
                action_item.setForeground(QColor("#E6A23C"))
            elif action == "reminder":
                action_item.setForeground(QColor("#E6A23C"))
            
            self.history_table.setItem(row, 1, action_item)
            self.history_table.setItem(row, 2, QTableWidgetItem(h.get("operator", "-")))
            self.history_table.setItem(row, 3, QTableWidgetItem(h.get("details", "-")))
            self.history_table.setItem(row, 4, QTableWidgetItem(h.get("notes", "-") or "-"))
            
            for col in range(5):
                item = self.history_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)


class WorkOrderPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self._last_overdue_count = 0
        self._init_ui()
        self.refresh()

        self._overdue_timer = QTimer(self)
        self._overdue_timer.timeout.connect(self._check_overdue)
        self._overdue_timer.start(60000)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        stats_group = QGroupBox("工单统计")
        stats_layout = QHBoxLayout(stats_group)

        self.total_label = self._create_stat_card("全部工单", "0", "#1f77b4")
        self.pending_label = self._create_stat_card("待处理", "0", "#d62728")
        self.processing_label = self._create_stat_card("处理中", "0", "#ff7f0e")
        self.recheck_label = self._create_stat_card("待复检", "0", "#9467bd")
        self.completed_label = self._create_stat_card("已完成", "0", "#2ca02c")
        self.overdue_label = self._create_stat_card("已超期", "0", "#d62728")

        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.pending_label)
        stats_layout.addWidget(self.processing_label)
        stats_layout.addWidget(self.recheck_label)
        stats_layout.addWidget(self.completed_label)
        stats_layout.addWidget(self.overdue_label)
        stats_layout.addStretch()
        main_layout.addWidget(stats_group)

        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        for status in WORK_ORDER_STATUSES:
            self.status_filter.addItem(status, status)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)

        self.area_filter = QComboBox()
        self.area_filter.addItem("全部洞区", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_filter.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("洞区:"))
        filter_layout.addWidget(self.area_filter)

        self.risk_filter = QComboBox()
        self.risk_filter.addItem("全部等级", None)
        for level in RISK_LEVELS:
            self.risk_filter.addItem(level, level)
        self.risk_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("风险等级:"))
        filter_layout.addWidget(self.risk_filter)

        self.assignee_filter = QLineEdit()
        self.assignee_filter.setPlaceholderText("责任人姓名")
        self.assignee_filter.setMaximumWidth(150)
        self.assignee_filter.textChanged.connect(self._on_assignee_changed)
        filter_layout.addWidget(QLabel("责任人:"))
        filter_layout.addWidget(self.assignee_filter)

        filter_layout.addWidget(QLabel("开始:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.start_date)

        filter_layout.addWidget(QLabel("结束:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate())
        self.end_date.dateChanged.connect(self.refresh)
        filter_layout.addWidget(self.end_date)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Vertical)

        order_group = QGroupBox("工单列表")
        order_layout = QVBoxLayout(order_group)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建工单")
        self.add_btn.clicked.connect(self._on_add_order)
        self.detail_btn = QPushButton("查看详情")
        self.detail_btn.clicked.connect(self._on_view_detail)
        self.detail_btn.setEnabled(False)
        self.history_btn = QPushButton("历史记录")
        self.history_btn.clicked.connect(self._on_view_history)
        self.history_btn.setEnabled(False)
        self.batch_assign_btn = QPushButton("批量派单")
        self.batch_assign_btn.clicked.connect(self._on_batch_assign)
        self.batch_assign_btn.setEnabled(False)
        self.batch_assign_btn.setStyleSheet("QPushButton { background: #409EFF; color: white; border: none; padding: 6px 16px; border-radius: 4px; } QPushButton:hover { background: #66b1ff; } QPushButton:disabled { background: #c0c4cc; }")
        self.recheck_reminder_btn = QPushButton("复检提醒")
        self.recheck_reminder_btn.clicked.connect(self._on_send_recheck_reminder)
        self.recheck_reminder_btn.setEnabled(False)
        self.recheck_reminder_btn.setStyleSheet("QPushButton { background: #E6A23C; color: white; border: none; padding: 6px 16px; border-radius: 4px; } QPushButton:hover { background: #f5d76e; } QPushButton:disabled { background: #c0c4cc; }")
        self.escalate_btn = QPushButton("工单升级")
        self.escalate_btn.clicked.connect(self._on_escalate)
        self.escalate_btn.setEnabled(False)
        self.escalate_btn.setStyleSheet("QPushButton { background: #F56C6C; color: white; border: none; padding: 6px 16px; border-radius: 4px; } QPushButton:hover { background: #f78989; } QPushButton:disabled { background: #c0c4cc; }")
        self.auto_remind_btn = QPushButton("自动催办")
        self.auto_remind_btn.clicked.connect(self._on_auto_remind)
        self.auto_remind_btn.setStyleSheet("QPushButton { background: #67C23A; color: white; border: none; padding: 6px 16px; border-radius: 4px; } QPushButton:hover { background: #85ce61; }")
        self.auto_escalate_btn = QPushButton("自动升级")
        self.auto_escalate_btn.clicked.connect(self._on_auto_escalate)
        self.auto_escalate_btn.setStyleSheet("QPushButton { background: #909399; color: white; border: none; padding: 6px 16px; border-radius: 4px; } QPushButton:hover { background: #a6a9ad; }")
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.detail_btn)
        btn_layout.addWidget(self.history_btn)
        btn_layout.addWidget(self.batch_assign_btn)
        btn_layout.addWidget(self.recheck_reminder_btn)
        btn_layout.addWidget(self.escalate_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.auto_remind_btn)
        btn_layout.addWidget(self.auto_escalate_btn)
        btn_layout.addWidget(self.refresh_btn)
        order_layout.addLayout(btn_layout)

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(12)
        self.order_table.setHorizontalHeaderLabels([
            "☑", "ID", "工单编号", "标题", "洞区", "滴水点", "异常类型",
            "风险等级", "责任人", "状态", "计划巡检时间", "创建时间"
        ])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.order_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.order_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.order_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.order_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.order_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.order_table.itemDoubleClicked.connect(self._on_view_detail)
        self.order_table.itemSelectionChanged.connect(self._on_selection_changed)
        self.order_table.itemClicked.connect(self._on_item_clicked)
        order_layout.addWidget(self.order_table)
        splitter.addWidget(order_group)

        analysis_group = QGroupBox("统计分析")
        analysis_layout = QVBoxLayout(analysis_group)

        self.tabs = QTabWidget()

        eff_tab = QWidget()
        eff_layout = QVBoxLayout(eff_tab)
        self.eff_table = QTableWidget()
        self.eff_table.setColumnCount(2)
        self.eff_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.eff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.eff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.eff_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        eff_layout.addWidget(self.eff_table)
        self.tabs.addTab(eff_tab, "处置效率")

        repeat_tab = QWidget()
        repeat_layout = QVBoxLayout(repeat_tab)
        self.repeat_table = QTableWidget()
        self.repeat_table.setColumnCount(5)
        self.repeat_table.setHorizontalHeaderLabels([
            "滴水点", "洞区", "工单数量", "异常类型", "操作"
        ])
        self.repeat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.repeat_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.repeat_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        repeat_layout.addWidget(self.repeat_table)
        self.tabs.addTab(repeat_tab, "重复异常点位")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)

        hist_filter_row = QHBoxLayout()
        hist_filter_row.addWidget(QLabel("选择滴水点:"))
        self.hist_point_combo = QComboBox()
        self.hist_point_combo.addItem("请选择", None)
        for p in self.db.get_all_drip_points():
            self.hist_point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])
        hist_filter_row.addWidget(self.hist_point_combo)
        self.hist_query_btn = QPushButton("查询历史")
        self.hist_query_btn.clicked.connect(self._on_query_history)
        hist_filter_row.addStretch()
        history_layout.addLayout(hist_filter_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "工单编号", "标题", "异常类型", "风险等级", "状态", "处理时长(分钟)", "创建时间"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        history_layout.addWidget(self.history_table)
        self.tabs.addTab(history_tab, "历史维护记录")

        overdue_tab = QWidget()
        overdue_layout = QVBoxLayout(overdue_tab)
        self.overdue_table = QTableWidget()
        self.overdue_table.setColumnCount(7)
        self.overdue_table.setHorizontalHeaderLabels([
            "工单编号", "标题", "洞区", "滴水点", "责任人", "计划时间", "超期天数"
        ])
        self.overdue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.overdue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.overdue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.overdue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        overdue_layout.addWidget(self.overdue_table)
        self.tabs.addTab(overdue_tab, "超期工单")

        analysis_layout.addWidget(self.tabs)

        stat_btn_layout = QHBoxLayout()
        self.run_stat_btn = QPushButton("执行统计")
        self.run_stat_btn.clicked.connect(self._run_analysis)
        stat_btn_layout.addStretch()
        stat_btn_layout.addWidget(self.run_stat_btn)
        analysis_layout.addLayout(stat_btn_layout)

        splitter.addWidget(analysis_group)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 10, 15, 10)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #666; font-size: 13px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        return card

    def _update_stat_card(self, card: QFrame, value: str):
        layout = card.layout()
        if layout and layout.count() > 1:
            item = layout.itemAt(1)
            if item and item.widget():
                item.widget().setText(value)

    def _on_assignee_changed(self):
        self.refresh()

    def _on_selection_changed(self):
        has_single = len(self.order_table.selectionModel().selectedRows()) == 1
        has_selection = len(self.order_table.selectionModel().selectedRows()) > 0
        self.detail_btn.setEnabled(has_single)
        self.history_btn.setEnabled(has_single)
        self.recheck_reminder_btn.setEnabled(has_single)
        self.escalate_btn.setEnabled(has_single)
        self.batch_assign_btn.setEnabled(has_selection)

    def _on_item_clicked(self, item: QTableWidgetItem):
        if item.column() == 0:
            checked_count = self._get_checked_count()
            self.batch_assign_btn.setEnabled(checked_count > 0)

    def _get_checked_order_ids(self) -> List[int]:
        order_ids = []
        for row in range(self.order_table.rowCount()):
            item = self.order_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                id_item = self.order_table.item(row, 1)
                if id_item:
                    order_ids.append(int(id_item.text()))
        return order_ids

    def _get_checked_count(self) -> int:
        count = 0
        for row in range(self.order_table.rowCount()):
            item = self.order_table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                count += 1
        return count

    def _get_current_order_id(self) -> Optional[int]:
        row = self.order_table.currentRow()
        if row < 0:
            return None
        id_item = self.order_table.item(row, 1)
        if id_item:
            return int(id_item.text())
        return None

    def refresh(self):
        self._refresh_orders()
        self._refresh_stats()
        self.data_changed.emit()

    def _refresh_orders(self):
        status = self.status_filter.currentData()
        area_id = self.area_filter.currentData()
        risk = self.risk_filter.currentData()
        assignee = self.assignee_filter.text().strip()
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")

        orders = self.db.get_work_orders(
            status=status,
            area_id=area_id,
            risk_level=risk,
            assignee=assignee if assignee else None,
            start_date=start_date,
            end_date=end_date
        )

        self.order_table.setRowCount(len(orders))
        for row, order in enumerate(orders):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            check_item.setCheckState(Qt.Unchecked)
            check_item.setTextAlignment(Qt.AlignCenter)
            self.order_table.setItem(row, 0, check_item)
            
            self.order_table.setItem(row, 1, QTableWidgetItem(str(order["id"])))
            self.order_table.setItem(row, 2, QTableWidgetItem(order.get("order_no", "-")))
            self.order_table.setItem(row, 3, QTableWidgetItem(order.get("title", "-")))
            self.order_table.setItem(row, 4, QTableWidgetItem(
                f"{order.get('area_code', '-')} - {order.get('area_name', '-')}" if order.get('area_code') else "-"
            ))
            self.order_table.setItem(row, 5, QTableWidgetItem(
                f"{order.get('drip_point_code', '-')} - {order.get('drip_point_name', '-')}" if order.get('drip_point_code') else "-"
            ))
            self.order_table.setItem(row, 6, QTableWidgetItem(order.get("anomaly_type", "-")))

            risk_item = QTableWidgetItem(order.get("risk_level", "-"))
            risk_colors = {
                "低": QColor("#2ca02c"), "中": QColor("#ffbb78"),
                "高": QColor("#ff7f0e"), "极高": QColor("#d62728")
            }
            risk_color = risk_colors.get(order.get("risk_level", ""), QColor("#000"))
            risk_item.setForeground(risk_color)
            self.order_table.setItem(row, 7, risk_item)

            self.order_table.setItem(row, 8, QTableWidgetItem(order.get("assignee", "-")))

            status_text = order.get("status", "-")
            status_item = QTableWidgetItem(status_text)
            status_color = QColor(WORK_ORDER_STATUS_COLORS.get(status_text, "#000000"))
            status_item.setForeground(status_color)
            status_item.setBackground(QBrush(status_color.lighter(190)))
            self.order_table.setItem(row, 9, status_item)

            plan_time = order.get("plan_inspect_time", "-") or "-"
            plan_item = QTableWidgetItem(plan_time)
            if order.get("plan_inspect_time") and order.get("status") in ("待处理", "处理中"):
                plan_dt = QDateTime.fromString(order["plan_inspect_time"], "yyyy-MM-dd HH:mm:ss")
                if plan_dt.isValid() and plan_dt < QDateTime.currentDateTime():
                    plan_item.setForeground(QColor("#d62728"))
            self.order_table.setItem(row, 10, plan_item)

            self.order_table.setItem(row, 11, QTableWidgetItem(order.get("created_at", "-")))

            for col in range(12):
                item = self.order_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _refresh_stats(self):
        stats = self.db.get_work_order_stats()
        self._update_stat_card(self.total_label, str(stats.get("total", 0)))
        self._update_stat_card(self.pending_label, str(stats.get("pending", 0)))
        self._update_stat_card(self.processing_label, str(stats.get("processing", 0)))
        self._update_stat_card(self.recheck_label, str(stats.get("recheck_pending", 0)))
        self._update_stat_card(self.completed_label, str(stats.get("completed", 0)))
        self._update_stat_card(self.overdue_label, str(stats.get("overdue", 0)))

    def _check_overdue(self):
        overdue = self.db.get_overdue_orders()
        count = len(overdue)
        if count > 0 and count != self._last_overdue_count:
            self._last_overdue_count = count
            self._refresh_stats()
            self._populate_overdue_table(overdue)
            high_risk = [o for o in overdue if o.get("risk_level") in ("高", "极高")]
            if high_risk:
                msg = f"当前有 {count} 个工单已超期，其中 {len(high_risk)} 个为高风险！"
            else:
                msg = f"当前有 {count} 个工单已超期，请及时处理。"
            self.statusMessage = msg

    def _populate_overdue_table(self, orders: List[Dict]):
        self.overdue_table.setRowCount(len(orders))
        for row, o in enumerate(orders):
            self.overdue_table.setItem(row, 0, QTableWidgetItem(o.get("order_no", "-")))
            self.overdue_table.setItem(row, 1, QTableWidgetItem(o.get("title", "-")))
            self.overdue_table.setItem(row, 2, QTableWidgetItem(
                f"{o.get('area_code', '-')} - {o.get('area_name', '-')}" if o.get('area_code') else "-"
            ))
            self.overdue_table.setItem(row, 3, QTableWidgetItem(
                f"{o.get('drip_point_code', '-')} - {o.get('drip_point_name', '-')}" if o.get('drip_point_code') else "-"
            ))
            self.overdue_table.setItem(row, 4, QTableWidgetItem(o.get("assignee", "-") or "未分配"))
            self.overdue_table.setItem(row, 5, QTableWidgetItem(o.get("plan_inspect_time", "-")))

            plan_dt = QDateTime.fromString(o.get("plan_inspect_time", ""), "yyyy-MM-dd HH:mm:ss")
            if plan_dt.isValid():
                secs = plan_dt.secsTo(QDateTime.currentDateTime())
                days = max(0, secs // 86400)
                overdue_item = QTableWidgetItem(f"{days} 天")
                overdue_item.setForeground(QColor("#d62728"))
            else:
                overdue_item = QTableWidgetItem("-")
            self.overdue_table.setItem(row, 6, overdue_item)

            for col in range(7):
                item = self.overdue_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_add_order(self):
        dialog = WorkOrderDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, order_id = self.db.add_work_order(**data)
            if success and order_id:
                priority = data.get("priority", "普通")
                if priority in WORK_ORDER_NEEDS_APPROVAL_PRIORITIES:
                    from ui.approval_panel import create_approval_for_work_order
                    create_approval_for_work_order(self.db, order_id, priority)
                
                self.db.add_work_order_history(
                    work_order_id=order_id,
                    action_type="create",
                    operator=data.get("assignee", "系统"),
                    details=f"创建工单，优先级：{priority}",
                    notes=data.get("notes", "")
                )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_view_detail(self):
        order_id = self._get_current_order_id()
        if not order_id:
            return
        dialog = WorkOrderDetailDialog(self, order_id=order_id)
        if dialog.exec() == QDialog.Accepted:
            self.refresh()

    def _on_view_history(self):
        order_id = self._get_current_order_id()
        if not order_id:
            return
        dialog = WorkOrderHistoryDialog(self, work_order_id=order_id)
        dialog.exec()

    def _on_batch_assign(self):
        order_ids = self._get_checked_order_ids()
        if not order_ids:
            order_ids = [self._get_current_order_id()] if self._get_current_order_id() else []
        
        if not order_ids:
            QMessageBox.warning(self, "提示", "请先勾选或选择要派单的工单")
            return
        
        pending_ids = []
        for oid in order_ids:
            order = self.db.get_work_order(oid)
            if order and order.get("status") == "待处理":
                pending_ids.append(oid)
        
        if not pending_ids:
            QMessageBox.information(self, "提示", "所选工单中没有待处理状态的工单")
            return
        
        dialog = BatchAssignDialog(self, work_order_ids=pending_ids)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, assigned_count = self.db.batch_assign_work_orders(
                work_order_ids=pending_ids,
                assignee=data["assignee"],
                plan_inspect_time=data["plan_inspect_time"],
                priority=data.get("priority"),
                notes=data.get("notes")
            )
            if success:
                for oid in pending_ids:
                    self.db.add_work_order_history(
                        work_order_id=oid,
                        action_type="assign",
                        operator=data["assignee"],
                        details=f"批量派单给 {data['assignee']}",
                        notes=data.get("notes", "")
                    )
                    self.db.add_reminder(
                        work_order_id=oid,
                        reminder_type="assignment",
                        recipient=data["assignee"],
                        content=f"您有新的工单需要处理，请及时前往现场巡检。",
                        due_date=data["plan_inspect_time"][:10]
                    )
                QMessageBox.information(self, "成功", f"{msg}\n共派单 {assigned_count} 个")
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_send_recheck_reminder(self):
        order_id = self._get_current_order_id()
        if not order_id:
            return
        
        order = self.db.get_work_order(order_id)
        if not order or order.get("status") != "待复检":
            QMessageBox.warning(self, "提示", "只有待复检状态的工单才能发送复检提醒")
            return
        
        dialog = RecheckReminderDialog(self, work_order_id=order_id)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, reminder_id = self.db.add_reminder(
                work_order_id=order_id,
                reminder_type="recheck",
                recipient=data["recipient"],
                content=data["content"],
                due_date=data["due_date"]
            )
            if success:
                self.db.add_work_order_history(
                    work_order_id=order_id,
                    action_type="reminder",
                    operator=data["recipient"],
                    details=f"发送复检提醒给 {data['recipient']}",
                    notes=data["content"]
                )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_escalate(self):
        order_id = self._get_current_order_id()
        if not order_id:
            return
        
        order = self.db.get_work_order(order_id)
        if not order:
            return
        
        escalations = self.db.get_work_order_escalations(order_id)
        current_level = max([e.get("level", 0) for e in escalations], default=0)
        
        if current_level >= 3:
            QMessageBox.warning(self, "提示", "该工单已达到最高升级级别")
            return
        
        dialog = EscalationDialog(self, work_order_id=order_id, current_level=current_level)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, escalation_id = self.db.add_escalation(
                work_order_id=order_id,
                escalation_level=data["new_level"],
                escalated_to=data["escalate_to"],
                escalation_reason=data["reason"]
            )
            if success:
                self.db.add_work_order_history(
                    work_order_id=order_id,
                    action_type="escalate",
                    operator=data["escalate_to"],
                    details=f"工单升级至 {ESCALATION_LEVEL_NAMES.get(data['new_level'], '')}，上报给 {data['escalate_to']}",
                    notes=data["reason"]
                )
                self.db.add_reminder(
                    work_order_id=order_id,
                    reminder_type="escalation",
                    recipient=data["escalate_to"],
                    content=f"工单 [{order.get('order_no', '')}] 已升级，请关注处理进度。\n升级原因：{data['reason']}",
                    due_date=QDate.currentDate().toString("yyyy-MM-dd")
                )
                QMessageBox.information(self, "成功", msg)
                self.refresh()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_auto_remind(self):
        reply = QMessageBox.question(
            self, "确认操作",
            "确定要对所有超期工单发送自动催办提醒吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            count, msg = self.db.auto_send_overdue_reminders()
            if count > 0:
                QMessageBox.information(self, "成功", f"已向 {count} 个超期工单发送催办提醒\n{msg}")
            else:
                QMessageBox.information(self, "提示", msg or "当前没有超期工单")
            self.refresh()

    def _on_auto_escalate(self):
        reply = QMessageBox.question(
            self, "确认操作",
            "确定要对所有超期工单执行自动升级检查吗？\n（超期3天→一级，超期7天→二级，超期14天→三级）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            count, msg = self.db.auto_escalate_overdue()
            if count > 0:
                QMessageBox.information(self, "成功", f"已自动升级 {count} 个超期工单\n{msg}")
            else:
                QMessageBox.information(self, "提示", msg or "没有需要升级的工单")
            self.refresh()

    def create_from_anomaly(self, anomaly_id: int):
        success, msg, order_id = self.db.create_work_order_from_anomaly(anomaly_id)
        if success and order_id:
            order = self.db.get_work_order(order_id)
            if order:
                priority = order.get("priority", "普通")
                if priority in WORK_ORDER_NEEDS_APPROVAL_PRIORITIES:
                    from ui.approval_panel import create_approval_for_work_order
                    create_approval_for_work_order(self.db, order_id, priority)
            
            QMessageBox.information(self, "成功", f"工单创建成功\n{msg}")
            self.refresh()
        else:
            QMessageBox.warning(self, "失败", msg)

    def _run_analysis(self):
        start_date = self.start_date.date().toString("yyyy-MM-dd")
        end_date = self.end_date.date().toString("yyyy-MM-dd")

        eff_stats = self.db.get_efficiency_stats(start_date, end_date)
        self._populate_eff_table(eff_stats)

        repeat_points = self.db.get_repeat_anomaly_points(start_date, end_date, 2)
        self._populate_repeat_table(repeat_points)

        overdue_orders = self.db.get_overdue_orders()
        self._populate_overdue_table(overdue_orders)

    def _populate_eff_table(self, stats: Dict):
        total = stats.get("total_orders", 0) or 0
        completed = stats.get("total_completed", 0) or 0
        avg_handle = stats.get("avg_handle_minutes")
        avg_response = stats.get("avg_response_minutes")
        overdue_count = stats.get("overdue_count", 0) or 0
        on_time = stats.get("on_time_count", 0) or 0
        arrived_with_plan = stats.get("arrived_with_plan_count", 0) or 0

        completion_rate = f"{completed / total * 100:.1f}%" if total > 0 else "暂无数据"
        on_time_rate = f"{on_time / arrived_with_plan * 100:.1f}%" if arrived_with_plan > 0 else "暂无数据"
        avg_handle_str = f"{avg_handle:.0f}" if avg_handle is not None else "暂无数据"
        avg_response_str = f"{avg_response:.0f}" if avg_response is not None else "暂无数据"

        rows = [
            ("工单总数", str(total)),
            ("已完成工单数", str(completed)),
            ("完成率", completion_rate),
            ("平均处置时长(分钟)", avg_handle_str),
            ("平均响应时长(分钟)", avg_response_str),
            ("超期工单数", str(overdue_count)),
            ("按时到场率", on_time_rate),
        ]
        self.eff_table.setRowCount(len(rows))
        for row, (label, value) in enumerate(rows):
            self.eff_table.setItem(row, 0, QTableWidgetItem(label))
            val_item = QTableWidgetItem(value)
            if label in ("超期工单数",) and value != "0":
                val_item.setForeground(QColor("#d62728"))
            self.eff_table.setItem(row, 1, val_item)
            for col in range(2):
                item = self.eff_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _populate_repeat_table(self, points: List[Dict]):
        self.repeat_table.setRowCount(len(points))
        for row, p in enumerate(points):
            self.repeat_table.setItem(row, 0, QTableWidgetItem(
                f"{p.get('drip_point_code', '-')} - {p.get('drip_point_name', '-')}"
            ))
            self.repeat_table.setItem(row, 1, QTableWidgetItem(
                f"{p.get('area_code', '-')} - {p.get('area_name', '-')}"
            ))
            self.repeat_table.setItem(row, 2, QTableWidgetItem(str(p.get("order_count", 0))))
            self.repeat_table.setItem(row, 3, QTableWidgetItem(p.get("anomaly_types", "-")))

            view_btn = QPushButton("查看历史")
            point_id = p.get("drip_point_id")
            view_btn.clicked.connect(lambda checked, pid=point_id: self._show_history_for_point(pid))
            self.repeat_table.setCellWidget(row, 4, view_btn)

            for col in range(4):
                item = self.repeat_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _show_history_for_point(self, drip_point_id: Optional[int]):
        if not drip_point_id:
            return
        idx = self.hist_point_combo.findData(drip_point_id)
        if idx >= 0:
            self.hist_point_combo.setCurrentIndex(idx)
        self._on_query_history()
        self.tabs.setCurrentIndex(2)

    def _on_query_history(self):
        point_id = self.hist_point_combo.currentData()
        if not point_id:
            self.history_table.setRowCount(0)
            return

        history = self.db.get_maintenance_history(point_id)
        self.history_table.setRowCount(len(history))
        for row, h in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(h.get("order_no", "-")))
            self.history_table.setItem(row, 1, QTableWidgetItem(h.get("title", "-")))
            self.history_table.setItem(row, 2, QTableWidgetItem(h.get("anomaly_type", "-") or "-"))

            risk_item = QTableWidgetItem(h.get("risk_level", "-"))
            risk_colors = {
                "低": QColor("#2ca02c"), "中": QColor("#ffbb78"),
                "高": QColor("#ff7f0e"), "极高": QColor("#d62728")
            }
            risk_color = risk_colors.get(h.get("risk_level", ""), QColor("#000"))
            risk_item.setForeground(risk_color)
            self.history_table.setItem(row, 3, risk_item)

            status_text = h.get("status", "-")
            status_item = QTableWidgetItem(status_text)
            status_color = QColor(WORK_ORDER_STATUS_COLORS.get(status_text, "#000000"))
            status_item.setForeground(status_color)
            self.history_table.setItem(row, 4, status_item)

            duration = h.get("handle_duration")
            self.history_table.setItem(row, 5, QTableWidgetItem(
                str(duration) if duration is not None else "-"
            ))
            self.history_table.setItem(row, 6, QTableWidgetItem(h.get("created_at", "-")))

            for col in range(7):
                item = self.history_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
