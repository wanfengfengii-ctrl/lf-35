from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QLabel, QGroupBox, QHeaderView, QAbstractItemView, QFileDialog,
    QMessageBox, QProgressBar, QSplitter, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from database.db_manager import get_db
from core.data_import import DataImporter, DataQualityChecker, QualityCheckResult


SEVERITY_COLORS = {
    "critical": QColor("#d62728"),
    "error": QColor("#d62728"),
    "warning": QColor("#ff7f0e"),
    "info": QColor("#1f77b4"),
}

CHECK_TYPE_NAMES = {
    "range_check": "范围检查",
    "duplicate_check": "重复检查",
    "time_order_check": "时间顺序检查",
    "time_gap_check": "时间间隔检查",
    "outlier_check": "异常值检查",
    "missing_check": "缺失值检查",
}


class QCPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.checker = DataQualityChecker()
        self.current_qc_result: Optional[QualityCheckResult] = None
        self.current_file_path: Optional[str] = None
        self.current_parsed_data = None
        self._init_ui()
        self.refresh_points()
        self._refresh_history()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_group = QGroupBox("数据质量检查")
        top_layout = QVBoxLayout(top_group)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("滴水点:"))
        self.point_combo = QComboBox()
        self.point_combo.setMinimumWidth(300)
        control_layout.addWidget(self.point_combo)

        control_layout.addWidget(QLabel("CSV文件:"))
        self.file_label = QLabel("未选择文件")
        self.file_label.setMinimumWidth(200)
        self.file_label.setStyleSheet("color: #666;")
        control_layout.addWidget(self.file_label, stretch=1)

        self.browse_btn = QPushButton("选择文件")
        self.browse_btn.clicked.connect(self._on_browse)
        control_layout.addWidget(self.browse_btn)

        top_layout.addLayout(control_layout)

        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("运行质量检查")
        self.run_btn.clicked.connect(self._on_run_check)
        self.save_btn = QPushButton("保存QC记录")
        self.save_btn.clicked.connect(self._on_save)
        self.save_btn.setEnabled(False)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self._refresh_history)
        btn_layout.addWidget(self.run_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        top_layout.addLayout(btn_layout)

        summary_layout = QHBoxLayout()
        self.score_label = QLabel("质量评分: --")
        self.score_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self.score_label)

        self.pass_label = QLabel("状态: --")
        self.pass_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        summary_layout.addWidget(self.pass_label)

        self.rows_label = QLabel("总行数: --")
        summary_layout.addWidget(self.rows_label)

        self.error_label = QLabel("错误: --")
        self.error_label.setStyleSheet("color: #d62728;")
        summary_layout.addWidget(self.error_label)

        self.warning_label = QLabel("警告: --")
        self.warning_label.setStyleSheet("color: #ff7f0e;")
        summary_layout.addWidget(self.warning_label)

        self.info_label_qc = QLabel("信息: --")
        self.info_label_qc.setStyleSheet("color: #1f77b4;")
        summary_layout.addWidget(self.info_label_qc)

        summary_layout.addStretch()
        top_layout.addLayout(summary_layout)

        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setValue(0)
        self.score_bar.setFormat("质量评分: %v%")
        self.score_bar.setTextVisible(True)
        top_layout.addWidget(self.score_bar)

        main_layout.addWidget(top_group)

        splitter = QSplitter(Qt.Vertical)

        issue_group = QGroupBox("质量问题详情")
        issue_layout = QVBoxLayout(issue_group)
        self.issue_table = QTableWidget()
        self.issue_table.setColumnCount(6)
        self.issue_table.setHorizontalHeaderLabels([
            "检查类型", "行号", "字段", "原始值", "问题描述", "严重程度"
        ])
        self.issue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.issue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.issue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.issue_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.issue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.issue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        issue_layout.addWidget(self.issue_table)
        splitter.addWidget(issue_group)

        bottom_splitter = QSplitter(Qt.Horizontal)

        suggest_group = QGroupBox("建议")
        suggest_layout = QVBoxLayout(suggest_group)
        self.suggest_text = QTextEdit()
        self.suggest_text.setReadOnly(True)
        self.suggest_text.setMaximumHeight(150)
        suggest_layout.addWidget(self.suggest_text)
        bottom_splitter.addWidget(suggest_group)

        history_group = QGroupBox("QC历史记录")
        history_layout = QVBoxLayout(history_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "滴水点", "检查类型", "行号", "问题描述", "严重程度", "创建时间"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        history_layout.addWidget(self.history_table)
        bottom_splitter.addWidget(history_group)

        bottom_splitter.setStretchFactor(0, 1)
        bottom_splitter.setStretchFactor(1, 2)
        splitter.addWidget(bottom_splitter)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

    def refresh(self):
        self.refresh_points()
        self._refresh_history()

    def refresh_points(self):
        current_data = self.point_combo.currentData() if self.point_combo.count() > 0 else None
        self.point_combo.blockSignals(True)
        self.point_combo.clear()
        self.point_combo.addItem("请选择滴水点", None)
        points = self.db.get_all_drip_points()
        for point in points:
            display = f"{point['code']} - {point['name']}"
            self.point_combo.addItem(display, point["id"])
        if current_data is not None:
            index = self.point_combo.findData(current_data)
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

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", "", "CSV文件 (*.csv);;所有文件 (*)"
        )
        if file_path:
            self.current_file_path = file_path
            self.file_label.setText(file_path)
            self.file_label.setStyleSheet("color: #000;")

    def _on_run_check(self):
        point_id = self.point_combo.currentData()
        if point_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个滴水点")
            return

        if not self.current_file_path:
            QMessageBox.warning(self, "提示", "请先选择CSV文件")
            return

        success, error, parsed_data, parse_errors = DataImporter.import_csv(self.current_file_path)
        if not success:
            QMessageBox.warning(self, "导入失败", error)
            return

        if parse_errors:
            msg = "文件解析存在以下问题：\n" + "\n".join(parse_errors[:10])
            if len(parse_errors) > 10:
                msg += f"\n... 共 {len(parse_errors)} 个问题"
            QMessageBox.warning(self, "解析警告", msg)

        self.current_parsed_data = parsed_data
        self.current_qc_result = self.checker.run_quality_check(parsed_data)
        self._display_result(self.current_qc_result)
        self.save_btn.setEnabled(True)

    def _display_result(self, result: QualityCheckResult):
        self.score_label.setText(f"质量评分: {result.quality_score:.1f}")
        self.rows_label.setText(f"总行数: {result.total_rows}")
        self.error_label.setText(f"错误: {result.error_count}")
        self.warning_label.setText(f"警告: {result.warning_count}")
        self.info_label_qc.setText(f"信息: {result.info_count}")

        self.score_bar.setValue(int(result.quality_score))
        if result.quality_score >= 80:
            self.score_bar.setStyleSheet("QProgressBar::chunk { background-color: #2ca02c; }")
        elif result.quality_score >= 60:
            self.score_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff7f0e; }")
        else:
            self.score_bar.setStyleSheet("QProgressBar::chunk { background-color: #d62728; }")

        if result.passed:
            self.pass_label.setText("状态: 通过 ✓")
            self.pass_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2ca02c;")
        else:
            self.pass_label.setText("状态: 未通过 ✗")
            self.pass_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #d62728;")

        self.issue_table.setRowCount(len(result.issues))
        for row, issue in enumerate(result.issues):
            check_name = CHECK_TYPE_NAMES.get(issue["check_type"], issue["check_type"])
            self.issue_table.setItem(row, 0, QTableWidgetItem(check_name))
            self.issue_table.setItem(row, 1, QTableWidgetItem(str(issue.get("row_num", "-"))))
            self.issue_table.setItem(row, 2, QTableWidgetItem(issue.get("field_name", "-")))
            self.issue_table.setItem(row, 3, QTableWidgetItem(str(issue.get("original_value", "-"))))
            self.issue_table.setItem(row, 4, QTableWidgetItem(issue.get("issue_description", "-")))

            severity = issue.get("severity", "info")
            severity_item = QTableWidgetItem(severity)
            color = SEVERITY_COLORS.get(severity, QColor("#000000"))
            severity_item.setForeground(color)
            severity_item.setBackground(QBrush(color.lighter(180)))
            self.issue_table.setItem(row, 5, severity_item)

            for col in range(6):
                item = self.issue_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        if result.suggestions:
            self.suggest_text.setPlainText("\n".join(result.suggestions))
        else:
            self.suggest_text.setPlainText("数据质量良好，无特别建议。")

    def _on_save(self):
        if not self.current_qc_result:
            return

        point_id = self.point_combo.currentData()
        if point_id is None:
            QMessageBox.warning(self, "提示", "请先选择一个滴水点")
            return

        reply = QMessageBox.question(
            self, "确认保存",
            f"确定要保存质量检查记录吗？\n共 {len(self.current_qc_result.issues)} 个问题",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self.checker.save_qc_records_to_db(
            self.db, self.current_qc_result, drip_point_id=point_id
        )

        QMessageBox.information(self, "保存成功", f"已保存 {len(self.current_qc_result.issues)} 条QC记录")
        self.save_btn.setEnabled(False)
        self.data_changed.emit()
        self._refresh_history()

    def _refresh_history(self):
        point_id = self.point_combo.currentData() if self.point_combo.count() > 0 else None
        records = self.db.get_qc_records(drip_point_id=point_id)

        self.history_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.history_table.setItem(row, 0, QTableWidgetItem(str(rec["id"])))

            point_text = "-"
            if rec.get("drip_point_code"):
                point_text = f"{rec['drip_point_code']} - {rec['drip_point_name']}"
            self.history_table.setItem(row, 1, QTableWidgetItem(point_text))

            check_name = CHECK_TYPE_NAMES.get(rec.get("check_type", ""), rec.get("check_type", "-"))
            self.history_table.setItem(row, 2, QTableWidgetItem(check_name))
            self.history_table.setItem(row, 3, QTableWidgetItem(
                str(rec["row_num"]) if rec.get("row_num") is not None else "-"
            ))
            self.history_table.setItem(row, 4, QTableWidgetItem(rec.get("issue_description", "-")))

            severity = rec.get("severity", "info")
            severity_item = QTableWidgetItem(severity)
            color = SEVERITY_COLORS.get(severity, QColor("#000000"))
            severity_item.setForeground(color)
            severity_item.setBackground(QBrush(color.lighter(180)))
            self.history_table.setItem(row, 5, severity_item)

            self.history_table.setItem(row, 6, QTableWidgetItem(rec.get("created_at", "-")))

            for col in range(7):
                item = self.history_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
