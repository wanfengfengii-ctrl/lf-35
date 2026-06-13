from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QHeaderView, QLabel, QGroupBox, QComboBox,
    QAbstractItemView, QTextEdit, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor

from database.db_manager import get_db
from core.data_import import DataImporter


class ImportWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str, int, int, list)

    def __init__(self, point_id: int, file_path: str):
        super().__init__()
        self.point_id = point_id
        self.file_path = file_path
        self.db = get_db()

    def run(self):
        try:
            self.progress.emit(10, 100)
            success, error, data, parse_errors = DataImporter.import_csv(self.file_path)
            
            if not success:
                self.finished.emit(False, error, 0, 0, parse_errors)
                return
            
            self.progress.emit(50, 100)
            
            success, error, success_count, skip_count = self.db.batch_add_monitoring_data(
                self.point_id, data
            )
            
            self.progress.emit(100, 100)
            self.finished.emit(success, error, success_count, skip_count, parse_errors)
            
        except Exception as e:
            self.finished.emit(False, str(e), 0, 0, [])


class DataImportPanel(QWidget):
    data_imported = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.current_file_path = ""
        self.preview_header: List[str] = []
        self.preview_data: List[Dict] = []
        self.worker: Optional[ImportWorker] = None
        self._init_ui()
        self.refresh_points()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_group = QGroupBox("导入设置")
        top_layout = QVBoxLayout(top_group)

        point_layout = QHBoxLayout()
        point_layout.addWidget(QLabel("选择滴水点:"))
        self.point_combo = QComboBox()
        self.point_combo.setMinimumWidth(300)
        point_layout.addWidget(self.point_combo)
        point_layout.addStretch()
        top_layout.addLayout(point_layout)

        file_layout = QHBoxLayout()
        self.file_path_edit = QComboBox()
        self.file_path_edit.setEditable(True)
        self.file_path_edit.setPlaceholderText("选择要导入的 CSV 文件...")
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(self.file_path_edit, stretch=1)
        file_layout.addWidget(self.browse_btn)
        top_layout.addLayout(file_layout)

        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("预览数据")
        self.preview_btn.clicked.connect(self._on_preview)
        self.import_btn = QPushButton("开始导入")
        self.import_btn.clicked.connect(self._on_import)
        self.generate_btn = QPushButton("生成示例文件")
        self.generate_btn.clicked.connect(self._on_generate_sample)

        self.preview_btn.setEnabled(False)
        self.import_btn.setEnabled(False)

        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.generate_btn)
        top_layout.addLayout(btn_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        top_layout.addWidget(self.progress_bar)

        main_layout.addWidget(top_group)

        splitter = QSplitter(Qt.Vertical)

        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.preview_table)
        splitter.addWidget(preview_group)

        log_group = QGroupBox("导入日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        splitter.addWidget(log_group)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=1)

    def refresh_points(self):
        current_id = self.point_combo.currentData() if self.point_combo.count() > 0 else None
        self.point_combo.clear()

        points = self.db.get_all_drip_points()
        for point in points:
            display = f"{point['code']} - {point['name']}"
            self.point_combo.addItem(display, point["id"])

        if current_id is not None:
            index = self.point_combo.findData(current_id)
            if index >= 0:
                self.point_combo.setCurrentIndex(index)

        has_points = self.point_combo.count() > 0
        self.browse_btn.setEnabled(has_points)
        if not has_points:
            self._append_log("请先在【滴水点管理】中创建滴水点")

    def _on_browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 CSV 文件", "", "CSV 文件 (*.csv)"
        )
        if file_path:
            self.current_file_path = file_path
            self.file_path_edit.addItem(file_path)
            self.file_path_edit.setCurrentText(file_path)
            self.preview_btn.setEnabled(True)
            self.import_btn.setEnabled(False)
            self._append_log(f"已选择文件: {file_path}")

    def _on_preview(self):
        file_path = self.file_path_edit.currentText().strip()
        if not file_path:
            QMessageBox.warning(self, "提示", "请先选择文件")
            return

        success, error, header, preview_data = DataImporter.validate_csv_file(file_path)
        if not success:
            QMessageBox.warning(self, "验证失败", error)
            self._append_log(f"验证失败: {error}")
            return

        self.preview_header = header
        self.preview_data = preview_data
        self._show_preview(header, preview_data)
        self.import_btn.setEnabled(True)
        self._append_log(f"文件验证通过，共找到 {len(header)} 列数据")

    def _show_preview(self, header: List[str], data: List[Dict]):
        self.preview_table.clear()
        self.preview_table.setColumnCount(len(header))
        self.preview_table.setHorizontalHeaderLabels(header)
        self.preview_table.setRowCount(len(data))

        for row, item in enumerate(data):
            for col, field in enumerate(["record_time", "drip_interval", "temperature", "humidity", "salinity"]):
                if col < len(header):
                    value = item.get(field, "")
                    table_item = QTableWidgetItem(str(value))
                    if field == "drip_interval":
                        try:
                            val = float(value)
                            if val <= 0:
                                table_item.setForeground(QColor("#d62728"))
                        except (ValueError, TypeError):
                            table_item.setForeground(QColor("#d62728"))
                    self.preview_table.setItem(row, col, table_item)

        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _on_import(self):
        if self.point_combo.count() == 0:
            QMessageBox.warning(self, "提示", "请先创建滴水点")
            return

        point_id = self.point_combo.currentData()
        file_path = self.file_path_edit.currentText().strip()

        if not file_path:
            QMessageBox.warning(self, "提示", "请选择要导入的文件")
            return

        reply = QMessageBox.question(
            self, "确认导入",
            f"确定要将数据导入到 [{self.point_combo.currentText()}] 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        self._set_busy(True)
        self._append_log("开始导入...")

        self.worker = ImportWorker(point_id, file_path)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_import_finished)
        self.worker.start()

    def _on_progress(self, value: int, maximum: int):
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def _on_import_finished(self, success: bool, error: str, success_count: int, skip_count: int, parse_errors: list):
        self._set_busy(False)

        if parse_errors:
            self._append_log("解析错误:")
            for err in parse_errors[:20]:
                self._append_log(f"  {err}")
            if len(parse_errors) > 20:
                self._append_log(f"  ... 还有 {len(parse_errors) - 20} 条错误")

        if not success:
            QMessageBox.critical(self, "导入失败", error)
            self._append_log(f"导入失败: {error}")
            return

        msg = f"导入完成：成功 {success_count} 条，跳过 {skip_count} 条"
        if error:
            self._append_log(f"警告: {error}")
        self._append_log(msg)

        QMessageBox.information(self, "导入完成", msg)
        self.data_imported.emit()

    def _on_generate_sample(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存示例文件", "sample_drip_data.csv", "CSV 文件 (*.csv)"
        )
        if file_path:
            try:
                DataImporter.generate_sample_csv(file_path)
                QMessageBox.information(self, "成功", f"示例文件已生成: {file_path}")
                self._append_log(f"已生成示例文件: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "失败", f"生成失败: {str(e)}")

    def _set_busy(self, busy: bool):
        self.browse_btn.setEnabled(not busy)
        self.preview_btn.setEnabled(not busy and bool(self.current_file_path))
        self.import_btn.setEnabled(not busy and bool(self.current_file_path))
        self.generate_btn.setEnabled(not busy)
        self.point_combo.setEnabled(not busy)
        self.progress_bar.setVisible(busy)

    def _append_log(self, message: str):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
