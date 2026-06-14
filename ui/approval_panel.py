from typing import Optional, Dict, List, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QComboBox, QAbstractItemView, QSplitter,
    QTabWidget, QDateTimeEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import (
    APPROVAL_STATUSES, APPROVAL_STATUS_NAMES, APPROVAL_STATUS_COLORS,
    APPROVAL_STEPS, WORK_ORDER_STATUS_COLORS, WORK_ORDER_PRIORITY_COLORS,
    WORK_ORDER_NEEDS_APPROVAL_PRIORITIES, USER_ROLES
)


def create_approval_for_work_order_impl(db, work_order_id: int, priority: str = "普通") -> Tuple[bool, str]:
    if priority not in WORK_ORDER_NEEDS_APPROVAL_PRIORITIES:
        return True, "该优先级工单无需审批"

    order = db.get_work_order(work_order_id)
    if not order:
        return False, "工单不存在"

    success, msg, _ = db.add_approval_record(
        work_order_id=work_order_id,
        approval_step=1,
        approval_status="pending",
        approver_name=""
    )

    if success:
        db.add_reminder(
            work_order_id, "approval",
            recipient="manager",
            content=f"工单 [{order.get('order_no', '')}] 待审批"
        )

    return success, msg


create_approval_for_work_order = create_approval_for_work_order_impl


class ApprovalDialog(QDialog):
    def __init__(self, parent=None, approval_data: Optional[Dict] = None):
        super().__init__(parent)
        self.approval_data = approval_data
        self.db = get_db()
        self.setWindowTitle("审批工单")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._init_ui()
        if approval_data:
            self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)

        self.order_info = QTextEdit()
        self.order_info.setReadOnly(True)
        self.order_info.setMinimumHeight(200)
        layout.addRow("工单信息:", self.order_info)

        self.status_combo = QComboBox()
        self.status_combo.addItem("批准", "approved")
        self.status_combo.addItem("驳回", "rejected")
        layout.addRow("审批结果 *:", self.status_combo)

        self.step_combo = QComboBox()
        for step, name in APPROVAL_STEPS.items():
            self.step_combo.addItem(name, step)
        layout.addRow("审批步骤:", self.step_combo)

        self.approver_edit = QLineEdit()
        self.approver_edit.setPlaceholderText("审批人姓名")
        layout.addRow("审批人 *:", self.approver_edit)

        self.opinion_edit = QTextEdit()
        self.opinion_edit.setPlaceholderText("请输入审批意见...")
        self.opinion_edit.setMaximumHeight(120)
        layout.addRow("审批意见:", self.opinion_edit)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("提交审批")
        cancel_btn = QPushButton("取消")
        ok_btn.clicked.connect(self._on_ok)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)

    def _load_data(self):
        if not self.approval_data:
            return
        
        order_no = self.approval_data.get("order_no", "")
        title = self.approval_data.get("order_title", "")
        anomaly_type = self.approval_data.get("anomaly_type", "")
        risk_level = self.approval_data.get("risk_level", "")
        assignee = self.approval_data.get("assignee", "")
        drip_point = f"{self.approval_data.get('drip_point_code', '')} - {self.approval_data.get('drip_point_name', '')}"
        
        work_order_id = self.approval_data.get("work_order_id")
        order = self.db.get_work_order(work_order_id)
        
        info = f"""
        <h3>工单详情</h3>
        <table cellpadding="6" style="border-collapse: collapse;">
        <tr><td><b>工单编号:</b></td><td>{order_no}</td>
            <td><b>优先级:</b></td><td>{order.get('priority', '-') if order else '-'}</td></tr>
        <tr><td><b>标题:</b></td><td colspan="3">{title}</td></tr>
        <tr><td><b>异常类型:</b></td><td>{anomaly_type}</td>
            <td><b>风险等级:</b></td><td>{risk_level}</td></tr>
        <tr><td><b>责任人:</b></td><td>{assignee or '未分配'}</td>
            <td><b>滴水点:</b></td><td>{drip_point}</td></tr>
        <tr><td><b>计划时间:</b></td><td colspan="3">{order.get('plan_inspect_time', '-') if order else '-'}</td></tr>
        </table>
        <h4>问题描述</h4>
        <p>{order.get('description', '-') if order else '-'}</p>
        """
        self.order_info.setHtml(info)
        
        step = self.approval_data.get("approval_step", 1)
        idx = self.step_combo.findData(step)
        if idx >= 0:
            self.step_combo.setCurrentIndex(idx)

    def _on_ok(self):
        approver = self.approver_edit.text().strip()
        if not approver:
            QMessageBox.warning(self, "提示", "请输入审批人姓名")
            return
        self.accept()

    def get_data(self) -> Dict:
        return {
            "approval_status": self.status_combo.currentData(),
            "approval_opinion": self.opinion_edit.toPlainText().strip(),
            "approver_name": self.approver_edit.text().strip(),
            "approval_step": self.step_combo.currentData(),
        }


class ApprovalPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.current_approval_id: Optional[int] = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        stats_group = QGroupBox("审批统计")
        stats_layout = QHBoxLayout(stats_group)

        self.pending_label = self._create_stat_card("待审批", "0", APPROVAL_STATUS_COLORS["pending"])
        self.approved_label = self._create_stat_card("已通过", "0", APPROVAL_STATUS_COLORS["approved"])
        self.rejected_label = self._create_stat_card("已驳回", "0", APPROVAL_STATUS_COLORS["rejected"])

        stats_layout.addWidget(self.pending_label)
        stats_layout.addWidget(self.approved_label)
        stats_layout.addWidget(self.rejected_label)
        stats_layout.addStretch()
        main_layout.addWidget(stats_group)

        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        for status in APPROVAL_STATUSES:
            self.status_filter.addItem(APPROVAL_STATUS_NAMES.get(status, status), status)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)

        self.step_filter = QComboBox()
        self.step_filter.addItem("全部步骤", None)
        for step, name in APPROVAL_STEPS.items():
            self.step_filter.addItem(name, step)
        self.step_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("步骤:"))
        filter_layout.addWidget(self.step_filter)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索工单号/标题")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_edit)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Horizontal)

        approval_group = QGroupBox("审批列表")
        approval_layout = QVBoxLayout(approval_group)

        btn_layout = QHBoxLayout()
        self.approve_btn = QPushButton("审批")
        self.approve_btn.clicked.connect(self._on_approve)
        self.approve_btn.setEnabled(False)
        self.view_order_btn = QPushButton("查看工单")
        self.view_order_btn.clicked.connect(self._on_view_order)
        self.view_order_btn.setEnabled(False)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.approve_btn)
        btn_layout.addWidget(self.view_order_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        approval_layout.addLayout(btn_layout)

        self.approval_table = QTableWidget()
        self.approval_table.setColumnCount(9)
        self.approval_table.setHorizontalHeaderLabels([
            "ID", "工单号", "标题", "异常类型", "风险等级", "责任人",
            "步骤", "状态", "申请时间"
        ])
        self.approval_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.approval_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.approval_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.approval_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.approval_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.approval_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.approval_table.itemSelectionChanged.connect(self._on_approval_selected)
        self.approval_table.itemDoubleClicked.connect(self._on_approve)
        approval_layout.addWidget(self.approval_table)

        splitter.addWidget(approval_group)

        detail_group = QGroupBox("审批详情")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_tabs = QTabWidget()

        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        info_layout.addWidget(self.detail_text)
        self.detail_tabs.addTab(info_tab, "工单信息")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.addWidget(QLabel("审批历史:"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "步骤", "审批人", "状态", "意见", "时间"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        history_layout.addWidget(self.history_table)
        self.detail_tabs.addTab(history_tab, "审批历史")

        detail_layout.addWidget(self.detail_tabs)
        splitter.addWidget(detail_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

    def _create_stat_card(self, title: str, value: str, color: str) -> QLabel:
        card = QLabel()
        card.setStyleSheet(f"""
            QLabel {{
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                min-width: 120px;
            }}
        """)
        card.setText(f'<div style="color: #666; font-size: 13px;">{title}</div>'
                     f'<div style="color: {color}; font-size: 28px; font-weight: bold; text-align: center;">{value}</div>')
        card.setTextFormat(Qt.RichText)
        card.setAlignment(Qt.AlignCenter)
        return card

    def _update_stat_card(self, card: QLabel, value: str):
        text = card.text()
        import re
        new_text = re.sub(r'(\d+)(</div>\s*$)', f'{value}\\2', text)
        card.setText(new_text)

    def refresh(self):
        status = self.status_filter.currentData()
        step = self.step_filter.currentData()
        search = self.search_edit.text().strip().lower()

        approvals = self.db.get_approval_records(approval_status=status)
        
        if step:
            approvals = [a for a in approvals if a.get("approval_step") == step]
        
        if search:
            approvals = [a for a in approvals 
                        if search in str(a.get("order_no", "")).lower()
                        or search in str(a.get("order_title", "")).lower()]

        self.approval_table.setRowCount(len(approvals))
        for row, approval in enumerate(approvals):
            self.approval_table.setItem(row, 0, QTableWidgetItem(str(approval["id"])))
            self.approval_table.setItem(row, 1, QTableWidgetItem(approval.get("order_no", "-")))
            self.approval_table.setItem(row, 2, QTableWidgetItem(approval.get("order_title", "-")))
            self.approval_table.setItem(row, 3, QTableWidgetItem(approval.get("anomaly_type", "-")))
            
            risk_item = QTableWidgetItem(approval.get("risk_level", "-"))
            risk_colors = {
                "低": QColor("#2ca02c"), "中": QColor("#ffbb78"),
                "高": QColor("#ff7f0e"), "极高": QColor("#d62728")
            }
            risk_color = risk_colors.get(approval.get("risk_level", ""), QColor("#000"))
            risk_item.setForeground(risk_color)
            self.approval_table.setItem(row, 4, risk_item)
            
            self.approval_table.setItem(row, 5, QTableWidgetItem(approval.get("assignee", "-") or "未分配"))
            
            step_val = approval.get("approval_step", 1)
            self.approval_table.setItem(row, 6, QTableWidgetItem(APPROVAL_STEPS.get(step_val, f"步骤{step_val}")))
            
            status_val = approval.get("approval_status", "pending")
            status_item = QTableWidgetItem(APPROVAL_STATUS_NAMES.get(status_val, status_val))
            status_color = QColor(APPROVAL_STATUS_COLORS.get(status_val, "#000"))
            status_item.setForeground(status_color)
            status_item.setBackground(QBrush(status_color.lighter(190)))
            self.approval_table.setItem(row, 7, status_item)
            
            self.approval_table.setItem(row, 8, QTableWidgetItem(approval.get("created_at", "-")))
            
            for col in range(9):
                item = self.approval_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self._refresh_stats()
        self._clear_details()

    def _refresh_stats(self):
        all_approvals = self.db.get_approval_records()
        pending = len([a for a in all_approvals if a.get("approval_status") == "pending"])
        approved = len([a for a in all_approvals if a.get("approval_status") == "approved"])
        rejected = len([a for a in all_approvals if a.get("approval_status") == "rejected"])
        
        self._update_stat_card(self.pending_label, str(pending))
        self._update_stat_card(self.approved_label, str(approved))
        self._update_stat_card(self.rejected_label, str(rejected))

    def _on_approval_selected(self):
        has = len(self.approval_table.selectedItems()) > 0
        self.approve_btn.setEnabled(has)
        self.view_order_btn.setEnabled(has)
        
        if has:
            row = self.approval_table.currentRow()
            self.current_approval_id = int(self.approval_table.item(row, 0).text())
            self._load_approval_details()
        else:
            self.current_approval_id = None
            self._clear_details()

    def _clear_details(self):
        self.detail_text.clear()
        self.history_table.setRowCount(0)

    def _load_approval_details(self):
        if not self.current_approval_id:
            return
        
        approvals = self.db.get_approval_records()
        approval = next((a for a in approvals if a["id"] == self.current_approval_id), None)
        if not approval:
            return

        work_order_id = approval.get("work_order_id")
        order = self.db.get_work_order(work_order_id) if work_order_id else None
        
        status_val = approval.get("approval_status", "pending")
        step_val = approval.get("approval_step", 1)
        
        info = f"""
        <h3>审批信息</h3>
        <table cellpadding="6" style="border-collapse: collapse;">
        <tr><td><b>工单编号:</b></td><td>{approval.get('order_no', '-')}</td>
            <td><b>审批状态:</b></td>
            <td><span style="color:{APPROVAL_STATUS_COLORS.get(status_val, '#000')}"><b>{APPROVAL_STATUS_NAMES.get(status_val, status_val)}</b></span></td></tr>
        <tr><td><b>工单标题:</b></td><td colspan="3">{approval.get('order_title', '-')}</td></tr>
        <tr><td><b>审批步骤:</b></td><td>{APPROVAL_STEPS.get(step_val, f'步骤{step_val}')}</td>
            <td><b>风险等级:</b></td><td>{approval.get('risk_level', '-')}</td></tr>
        <tr><td><b>异常类型:</b></td><td>{approval.get('anomaly_type', '-')}</td>
            <td><b>责任人:</b></td><td>{approval.get('assignee', '-') or '未分配'}</td></tr>
        <tr><td><b>申请时间:</b></td><td>{approval.get('created_at', '-')}</td>
            <td><b>审批时间:</b></td><td>{approval.get('approval_time', '-')}</td></tr>
        </table>
        """
        
        if order:
            info += f"""
            <h4>工单详情</h4>
            <table cellpadding="6" style="border-collapse: collapse;">
            <tr><td><b>优先级:</b></td><td>{order.get('priority', '-')}</td>
                <td><b>计划巡检:</b></td><td>{order.get('plan_inspect_time', '-')}</td></tr>
            <tr><td><b>滴水点:</b></td><td colspan="3">{order.get('drip_point_code', '-')} - {order.get('drip_point_name', '-')}</td></tr>
            </table>
            <h4>问题描述</h4>
            <p>{order.get('description', '-')}</p>
            <h4>巡检内容</h4>
            <p>{order.get('inspection_content', '-')}</p>
            """
        
        if approval.get("approval_opinion"):
            info += f"""
            <h4>审批意见</h4>
            <p style="background: #f5f5f5; padding: 10px; border-radius: 4px;">{approval.get('approval_opinion', '-')}</p>
            """
        
        self.detail_text.setHtml(info)
        
        if work_order_id:
            self._load_approval_history(work_order_id)

    def _load_approval_history(self, work_order_id: int):
        history = self.db.get_approval_records(work_order_id=work_order_id)
        self.history_table.setRowCount(len(history))
        for row, record in enumerate(history):
            step_val = record.get("approval_step", 1)
            self.history_table.setItem(row, 0, QTableWidgetItem(APPROVAL_STEPS.get(step_val, f"步骤{step_val}")))
            self.history_table.setItem(row, 1, QTableWidgetItem(record.get("approver_name", "-")))
            
            status_val = record.get("approval_status", "pending")
            status_item = QTableWidgetItem(APPROVAL_STATUS_NAMES.get(status_val, status_val))
            status_color = QColor(APPROVAL_STATUS_COLORS.get(status_val, "#000"))
            status_item.setForeground(status_color)
            self.history_table.setItem(row, 2, status_item)
            
            self.history_table.setItem(row, 3, QTableWidgetItem(record.get("approval_opinion", "-")))
            self.history_table.setItem(row, 4, QTableWidgetItem(record.get("approval_time", "-")))
            
            for col in range(5):
                item = self.history_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

    def _on_approve(self):
        if not self.current_approval_id:
            return
        
        approvals = self.db.get_approval_records()
        approval = next((a for a in approvals if a["id"] == self.current_approval_id), None)
        if not approval:
            return
        
        if approval.get("approval_status") != "pending":
            QMessageBox.information(self, "提示", "该审批已处理，无法重复审批")
            return
        
        dialog = ApprovalDialog(self, approval_data=approval)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg = self.db.update_approval_record(
                self.current_approval_id,
                approval_status=data["approval_status"],
                approval_opinion=data["approval_opinion"],
                approver_name=data["approver_name"]
            )
            
            if success and data["approval_status"] == "approved":
                work_order_id = approval.get("work_order_id")
                if work_order_id:
                    self.db.update_work_order_status(
                        work_order_id, "待处理", approval.get("assignee", "")
                    )
                    self.db.add_work_order_history(
                        work_order_id, "approval",
                        "", data["approval_status"],
                        data["approver_name"],
                        f"审批通过: {data['approval_opinion']}"
                    )
            elif success and data["approval_status"] == "rejected":
                work_order_id = approval.get("work_order_id")
                if work_order_id:
                    self.db.add_work_order_history(
                        work_order_id, "approval",
                        "", data["approval_status"],
                        data["approver_name"],
                        f"审批驳回: {data['approval_opinion']}"
                    )
            
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_view_order(self):
        if not self.current_approval_id:
            return
        
        approvals = self.db.get_approval_records()
        approval = next((a for a in approvals if a["id"] == self.current_approval_id), None)
        if not approval:
            return
        
        work_order_id = approval.get("work_order_id")
        if work_order_id:
            from ui.work_order_panel import WorkOrderDetailDialog
            dialog = WorkOrderDetailDialog(self, order_id=work_order_id)
            dialog.exec()

    def create_approval_for_work_order(self, work_order_id: int, priority: str = "普通") -> Tuple[bool, str]:
        return create_approval_for_work_order_impl(self.db, work_order_id, priority)
