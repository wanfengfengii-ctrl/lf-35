from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QMessageBox, QHeaderView,
    QLabel, QGroupBox, QComboBox, QAbstractItemView, QSplitter,
    QTabWidget, QListWidget, QListWidgetItem, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.anomaly_detector import (
    USER_ROLES, USER_ROLE_COLORS, USER_ROLE_PERMISSIONS
)


class UserDialog(QDialog):
    def __init__(self, parent=None, user_data: Optional[Dict] = None):
        super().__init__(parent)
        self.user_data = user_data
        self.db = get_db()
        self.setWindowTitle("编辑用户" if user_data else "新建用户")
        self.setMinimumWidth(500)
        self._init_ui()
        if user_data:
            self._load_data()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QFormLayout(content)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("登录用户名")
        layout.addRow("用户名 *:", self.username_edit)

        self.real_name_edit = QLineEdit()
        self.real_name_edit.setPlaceholderText("真实姓名")
        layout.addRow("真实姓名 *:", self.real_name_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("登录密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("密码 *:", self.password_edit)

        self.role_combo = QComboBox()
        for role_key, role_name in USER_ROLES.items():
            self.role_combo.addItem(role_name, role_key)
        layout.addRow("角色 *:", self.role_combo)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("联系电话")
        layout.addRow("联系电话:", self.phone_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("电子邮箱")
        layout.addRow("电子邮箱:", self.email_edit)

        self.department_edit = QLineEdit()
        self.department_edit.setPlaceholderText("所属部门")
        layout.addRow("所属部门:", self.department_edit)

        self.status_combo = QComboBox()
        self.status_combo.addItem("正常", "active")
        self.status_combo.addItem("禁用", "inactive")
        layout.addRow("状态:", self.status_combo)

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

    def _load_data(self):
        if not self.user_data:
            return
        self.username_edit.setText(self.user_data.get("username", ""))
        self.username_edit.setEnabled(False)
        self.real_name_edit.setText(self.user_data.get("real_name", ""))
        self.password_edit.setPlaceholderText("不修改请留空")
        
        role = self.user_data.get("role", "")
        idx = self.role_combo.findData(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        
        self.phone_edit.setText(self.user_data.get("phone", ""))
        self.email_edit.setText(self.user_data.get("email", ""))
        self.department_edit.setText(self.user_data.get("department", ""))
        
        status = self.user_data.get("status", "active")
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

    def _on_ok(self):
        username = self.username_edit.text().strip()
        real_name = self.real_name_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username:
            QMessageBox.warning(self, "提示", "请输入用户名")
            return
        if not real_name:
            QMessageBox.warning(self, "提示", "请输入真实姓名")
            return
        if not self.user_data and not password:
            QMessageBox.warning(self, "提示", "请输入密码")
            return
        
        self.accept()

    def get_data(self) -> Dict:
        data = {
            "username": self.username_edit.text().strip(),
            "real_name": self.real_name_edit.text().strip(),
            "role": self.role_combo.currentData(),
            "phone": self.phone_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "department": self.department_edit.text().strip(),
            "status": self.status_combo.currentData(),
        }
        password = self.password_edit.text().strip()
        if password:
            data["password"] = password
        return data


class UserPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.current_user_id: Optional[int] = None
        self._init_ui()
        self.refresh()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        filter_group = QGroupBox("筛选条件")
        filter_layout = QHBoxLayout(filter_group)

        self.role_filter = QComboBox()
        self.role_filter.addItem("全部角色", None)
        for role_key, role_name in USER_ROLES.items():
            self.role_filter.addItem(role_name, role_key)
        self.role_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("角色:"))
        filter_layout.addWidget(self.role_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        self.status_filter.addItem("正常", "active")
        self.status_filter.addItem("禁用", "inactive")
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索用户名/姓名")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_edit)

        filter_layout.addStretch()
        main_layout.addWidget(filter_group)

        splitter = QSplitter(Qt.Horizontal)

        user_group = QGroupBox("用户列表")
        user_layout = QVBoxLayout(user_group)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("新建用户")
        self.add_btn.clicked.connect(self._on_add_user)
        self.edit_btn = QPushButton("编辑用户")
        self.edit_btn.clicked.connect(self._on_edit_user)
        self.edit_btn.setEnabled(False)
        self.delete_btn = QPushButton("删除用户")
        self.delete_btn.clicked.connect(self._on_delete_user)
        self.delete_btn.setEnabled(False)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        user_layout.addLayout(btn_layout)

        self.user_table = QTableWidget()
        self.user_table.setColumnCount(8)
        self.user_table.setHorizontalHeaderLabels([
            "ID", "用户名", "真实姓名", "角色", "部门", "电话", "状态", "最后登录"
        ])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.user_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.user_table.itemSelectionChanged.connect(self._on_user_selected)
        self.user_table.itemDoubleClicked.connect(self._on_edit_user)
        user_layout.addWidget(self.user_table)

        splitter.addWidget(user_group)

        detail_group = QGroupBox("用户详情与权限")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_tabs = QTabWidget()

        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        self.detail_tabs.addTab(info_tab, "基本信息")

        perm_tab = QWidget()
        perm_layout = QVBoxLayout(perm_tab)

        perm_btn_layout = QHBoxLayout()
        perm_btn_layout.addWidget(QLabel("权限列表:"))
        self.save_perm_btn = QPushButton("保存权限")
        self.save_perm_btn.clicked.connect(self._on_save_permissions)
        self.save_perm_btn.setEnabled(False)
        perm_btn_layout.addStretch()
        perm_btn_layout.addWidget(self.save_perm_btn)
        perm_layout.addLayout(perm_btn_layout)

        self.perm_list = QListWidget()
        self.perm_list.setSelectionMode(QAbstractItemView.NoSelection)
        perm_layout.addWidget(self.perm_list)

        self.detail_tabs.addTab(perm_tab, "权限配置")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.addWidget(QLabel("该用户相关工单统计:"))
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        history_layout.addWidget(self.stats_text)
        self.detail_tabs.addTab(history_tab, "工作统计")

        detail_layout.addWidget(self.detail_tabs)
        splitter.addWidget(detail_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        role = self.role_filter.currentData()
        status = self.status_filter.currentData()
        search = self.search_edit.text().strip().lower()

        users = self.db.get_all_users(role=role, status=status)
        
        if search:
            users = [u for u in users if search in u.get("username", "").lower() 
                     or search in u.get("real_name", "").lower()]

        self.user_table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.user_table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
            self.user_table.setItem(row, 1, QTableWidgetItem(user.get("username", "-")))
            self.user_table.setItem(row, 2, QTableWidgetItem(user.get("real_name", "-")))
            
            role_key = user.get("role", "")
            role_name = USER_ROLES.get(role_key, role_key)
            role_item = QTableWidgetItem(role_name)
            role_color = QColor(USER_ROLE_COLORS.get(role_key, "#000"))
            role_item.setForeground(role_color)
            self.user_table.setItem(row, 3, role_item)
            
            self.user_table.setItem(row, 4, QTableWidgetItem(user.get("department", "-")))
            self.user_table.setItem(row, 5, QTableWidgetItem(user.get("phone", "-")))
            
            status_val = user.get("status", "active")
            status_text = "正常" if status_val == "active" else "禁用"
            status_item = QTableWidgetItem(status_text)
            if status_val == "inactive":
                status_item.setForeground(QColor("#d62728"))
            self.user_table.setItem(row, 6, status_item)
            
            self.user_table.setItem(row, 7, QTableWidgetItem(user.get("last_login", "-")))
            
            for col in range(8):
                item = self.user_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        self._clear_details()

    def _on_user_selected(self):
        has = len(self.user_table.selectedItems()) > 0
        self.edit_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)
        self.save_perm_btn.setEnabled(has)
        
        if has:
            row = self.user_table.currentRow()
            self.current_user_id = int(self.user_table.item(row, 0).text())
            self._load_user_details()
        else:
            self.current_user_id = None
            self._clear_details()

    def _clear_details(self):
        self.info_text.clear()
        self.perm_list.clear()
        self.stats_text.clear()

    def _load_user_details(self):
        if not self.current_user_id:
            return
        
        user = self.db.get_user(self.current_user_id)
        if not user:
            return

        role_key = user.get("role", "")
        role_name = USER_ROLES.get(role_key, role_key)
        status_text = "正常" if user.get("status") == "active" else "禁用"

        info = f"""
        <h3>用户信息</h3>
        <table cellpadding="6" style="border-collapse: collapse;">
        <tr><td><b>用户名:</b></td><td>{user.get('username', '-')}</td>
            <td><b>真实姓名:</b></td><td>{user.get('real_name', '-')}</td></tr>
        <tr><td><b>角色:</b></td><td><span style="color:{USER_ROLE_COLORS.get(role_key, '#000')}"><b>{role_name}</b></span></td>
            <td><b>状态:</b></td><td>{status_text}</td></tr>
        <tr><td><b>部门:</b></td><td>{user.get('department', '-')}</td>
            <td><b>电话:</b></td><td>{user.get('phone', '-')}</td></tr>
        <tr><td><b>邮箱:</b></td><td>{user.get('email', '-')}</td>
            <td><b>创建时间:</b></td><td>{user.get('created_at', '-')}</td></tr>
        <tr><td><b>最后登录:</b></td><td>{user.get('last_login', '-')}</td></tr>
        </table>
        <h4>角色说明</h4>
        <p>{self._get_role_description(role_key)}</p>
        """
        self.info_text.setHtml(info)

        self._load_permissions(user)
        self._load_user_stats(user)

    def _get_role_description(self, role_key: str) -> str:
        descriptions = {
            "manager": "管理人员：拥有系统全部权限，可管理用户、分配工单、审批流程、查看所有统计数据。",
            "researcher": "研究人员：可查看所有数据、创建工单、导出报告、进行统计分析，但无用户管理和审批权限。",
            "inspector": "现场巡检人员：仅能查看分配给自己的工单，进行现场巡检、提交巡检记录和上传附件。",
        }
        return descriptions.get(role_key, "未定义角色")

    def _load_permissions(self, user: Dict):
        self.perm_list.clear()
        role_key = user.get("role", "")
        role_perms = USER_ROLE_PERMISSIONS.get(role_key, [])
        user_perms = self.db.get_user_permissions(self.current_user_id)
        
        all_perms = set(role_perms) | set(user_perms)
        
        perm_descriptions = {
            "view_all": "查看所有数据",
            "view_assigned": "查看分配给自己的工单",
            "create_work_order": "创建工单",
            "edit_work_order": "编辑所有工单",
            "edit_own_work_order": "编辑自己创建的工单",
            "delete_work_order": "删除工单",
            "assign_work_order": "分配工单",
            "batch_assign": "批量派单",
            "approve_work_order": "审批工单",
            "create_user": "创建用户",
            "edit_user": "编辑用户",
            "delete_user": "删除用户",
            "manage_permissions": "管理权限",
            "create_route": "创建巡检路线",
            "edit_route": "编辑巡检路线",
            "delete_route": "删除巡检路线",
            "assign_route": "分配巡检路线",
            "view_route": "查看巡检路线",
            "view_statistics": "查看统计数据",
            "export_report": "导出报告",
            "escalate_work_order": "工单升级",
            "view_history": "查看历史记录",
            "view_own_history": "查看自己的历史记录",
            "view_anomaly_data": "查看异常数据",
            "import_data": "导入数据",
            "update_work_order_status": "更新工单状态",
            "add_inspection_record": "添加巡检记录",
            "upload_attachment": "上传附件",
            "manage_system": "系统管理",
        }
        
        for perm in sorted(all_perms):
            desc = perm_descriptions.get(perm, perm)
            item = QListWidgetItem(f"☐ {desc}")
            item.setData(Qt.UserRole, perm)
            
            if perm in role_perms:
                item.setCheckState(Qt.Checked)
                item.setText(f"☑ {desc} (角色默认)")
            elif perm in user_perms:
                item.setCheckState(Qt.Checked)
                item.setText(f"☑ {desc}")
            else:
                item.setCheckState(Qt.Unchecked)
            
            if perm in role_perms:
                item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                item.setForeground(QColor("#666"))
            
            self.perm_list.addItem(item)

    def _load_user_stats(self, user: Dict):
        real_name = user.get("real_name", "")
        assignee = real_name
        
        orders = self.db.get_work_orders(assignee=assignee)
        total = len(orders)
        completed = len([o for o in orders if o.get("status") in ("已完成", "已关闭")])
        pending = len([o for o in orders if o.get("status") in ("待处理", "处理中")])
        
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        overdue = len([o for o in orders if o.get("status") in ("待处理", "处理中") 
                        and o.get("plan_inspect_time") 
                        and o["plan_inspect_time"] < now_str])
        
        completion_rate = f"{(completed/total*100):.1f}%" if total > 0 else "-"
        
        stats = f"""
        <h3>工作统计 - {real_name}</h3>
        <table cellpadding="6" style="border-collapse: collapse;">
        <tr><td><b>总工单数:</b></td><td>{total}</td>
            <td><b>已完成:</b></td><td>{completed}</td></tr>
        <tr><td><b>待处理:</b></td><td>{pending}</td>
            <td><b>已超期:</b></td><td>{overdue}</td></tr>
        <tr><td><b>完成率:</b></td><td>{completion_rate}</td></tr>
        </table>
        """
        self.stats_text.setHtml(stats)

    def _on_add_user(self):
        dialog = UserDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            success, msg, _ = self.db.add_user(**data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_edit_user(self):
        if not self.current_user_id:
            return
        user = self.db.get_user(self.current_user_id)
        if not user:
            return
        
        dialog = UserDialog(self, user_data=user)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            password = data.pop("password", None)
            if not password:
                data.pop("password", None)
            success, msg = self.db.update_user(self.current_user_id, **data)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_delete_user(self):
        if not self.current_user_id:
            return
        user = self.db.get_user(self.current_user_id)
        if not user:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除用户 [{user.get('real_name', user.get('username', ''))}] 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success, msg = self.db.delete_user(self.current_user_id)
            if success:
                QMessageBox.information(self, "成功", msg)
                self.refresh()
                self.data_changed.emit()
            else:
                QMessageBox.warning(self, "失败", msg)

    def _on_save_permissions(self):
        if not self.current_user_id:
            return
        
        role = self.db.get_user(self.current_user_id).get("role", "")
        role_perms = set(USER_ROLE_PERMISSIONS.get(role, []))
        
        for i in range(self.perm_list.count()):
            item = self.perm_list.item(i)
            perm = item.data(Qt.UserRole)
            if perm in role_perms:
                continue
            
            if item.checkState() == Qt.Checked:
                self.db.add_user_permission(self.current_user_id, perm)
            else:
                self.db.delete_user_permission(self.current_user_id, perm)
        
        QMessageBox.information(self, "成功", "权限已保存")
        user = self.db.get_user(self.current_user_id)
        self._load_permissions(user)
