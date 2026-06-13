from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QGroupBox, QHeaderView, QAbstractItemView, QMessageBox, QTextEdit,
    QComboBox, QSpinBox, QSplitter, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from database.db_manager import get_db
from core.report_generator import ReportGenerator


class ReportPanel(QWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = get_db()
        self.generator = ReportGenerator()
        self.current_report_data: Optional[Dict] = None
        self._init_ui()
        self._refresh_report_types()
        self._refresh_drip_points()
        self._refresh_cave_areas()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        config_group = QGroupBox("报告配置")
        config_layout = QVBoxLayout(config_group)

        type_layout = QHBoxLayout()
        type_label = QLabel("报告类型:")
        self.type_combo = QComboBox()
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo, 1)
        config_layout.addLayout(type_layout)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666; font-style: italic; padding: 4px 0;")
        config_layout.addWidget(self.desc_label)

        param_layout = QHBoxLayout()

        self.point_label = QLabel("滴水点:")
        self.point_combo = QComboBox()
        self.point_combo.currentIndexChanged.connect(self._on_point_changed)
        param_layout.addWidget(self.point_label)
        param_layout.addWidget(self.point_combo, 1)

        self.year_label = QLabel("年份:")
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.year_spin.setValue(2024)
        param_layout.addWidget(self.year_label)
        param_layout.addWidget(self.year_spin)

        self.month_label = QLabel("月份:")
        self.month_spin = QSpinBox()
        self.month_spin.setRange(1, 12)
        self.month_spin.setValue(1)
        param_layout.addWidget(self.month_label)
        param_layout.addWidget(self.month_spin)

        self.area_label = QLabel("洞区:")
        self.area_combo = QComboBox()
        param_layout.addWidget(self.area_label)
        param_layout.addWidget(self.area_combo, 1)

        config_layout.addLayout(param_layout)

        btn_layout = QHBoxLayout()
        self.generate_btn = QPushButton("生成报告")
        self.export_csv_btn = QPushButton("导出CSV")
        self.export_text_btn = QPushButton("导出文本")
        self.generate_btn.clicked.connect(self._on_generate)
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        self.export_text_btn.clicked.connect(self._on_export_text)
        self.export_csv_btn.setEnabled(False)
        self.export_text_btn.setEnabled(False)
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addWidget(self.export_csv_btn)
        btn_layout.addWidget(self.export_text_btn)
        btn_layout.addStretch()
        config_layout.addLayout(btn_layout)

        splitter.addWidget(config_group)

        types_group = QGroupBox("可用报告类型")
        types_layout = QVBoxLayout(types_group)
        self.types_table = QTableWidget()
        self.types_table.setColumnCount(3)
        self.types_table.setHorizontalHeaderLabels(["类型", "名称", "说明"])
        self.types_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.types_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.types_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.types_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.types_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.types_table.setMaximumHeight(120)
        types_layout.addWidget(self.types_table)
        splitter.addWidget(types_group)

        preview_group = QGroupBox("报告预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("点击\"生成报告\"以预览报告内容")
        preview_layout.addWidget(self.preview_text)
        splitter.addWidget(preview_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setStretchFactor(2, 2)
        main_layout.addWidget(splitter)

    def refresh(self):
        self._refresh_drip_points()
        self._refresh_cave_areas()

    def _refresh_report_types(self):
        types = self.generator.get_available_report_types()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for t in types:
            self.type_combo.addItem(t["name"], t["key"])
        self.type_combo.blockSignals(False)

        self.types_table.setRowCount(len(types))
        for row, t in enumerate(types):
            self.types_table.setItem(row, 0, QTableWidgetItem(t.get("key", "-")))
            self.types_table.setItem(row, 1, QTableWidgetItem(t.get("name", "-")))
            self.types_table.setItem(row, 2, QTableWidgetItem(t.get("description", "-")))
            for col in range(3):
                item = self.types_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)

        if types:
            self._on_type_changed(0)

    def _refresh_drip_points(self):
        self.point_combo.blockSignals(True)
        self.point_combo.clear()
        points = self.db.get_all_drip_points()
        for p in points:
            self.point_combo.addItem(f"{p['code']} - {p['name']}", p["id"])
        self.point_combo.blockSignals(False)
        self._on_point_changed()

    def _refresh_cave_areas(self):
        self.area_combo.blockSignals(True)
        self.area_combo.clear()
        self.area_combo.addItem("全部", None)
        areas = self.db.get_all_cave_areas()
        for a in areas:
            self.area_combo.addItem(f"{a['code']} - {a['name']}", a["id"])
        self.area_combo.blockSignals(False)

    def _on_type_changed(self, index):
        key = self.type_combo.currentData()
        types = self.generator.get_available_report_types()
        desc = ""
        for t in types:
            if t["key"] == key:
                desc = t.get("description", "")
                break
        self.desc_label.setText(desc)

        is_monthly = key == "monthly"
        is_anomaly = key == "anomaly"
        is_joint = key == "joint"

        self.point_label.setVisible(is_monthly)
        self.point_combo.setVisible(is_monthly)
        self.year_label.setVisible(is_monthly)
        self.year_spin.setVisible(is_monthly)
        self.month_label.setVisible(is_monthly)
        self.month_spin.setVisible(is_monthly)

        self.area_label.setVisible(is_anomaly or is_joint)
        self.area_combo.setVisible(is_anomaly or is_joint)

        if is_anomaly:
            self.area_combo.setEnabled(True)
            idx = self.area_combo.findData(None)
            if idx >= 0:
                self.area_combo.setCurrentIndex(idx)

        if is_joint:
            for i in range(self.area_combo.count()):
                if self.area_combo.itemData(i) is None:
                    self.area_combo.removeItem(i)
                    break
            self.area_combo.setEnabled(True)

        if is_monthly:
            self._on_point_changed()

    def _on_point_changed(self):
        point_id = self.point_combo.currentData()
        if point_id is None:
            return
        try:
            year_range = self.db.get_data_year_range(point_id)
            if year_range:
                min_year = year_range[0] if year_range[0] else 2000
                max_year = year_range[1] if year_range[1] else 2100
                self.year_spin.setRange(min_year, max_year)
                self.year_spin.setValue(max_year)
        except Exception:
            pass

    def _on_generate(self):
        key = self.type_combo.currentData()
        report_data = None

        if key == "monthly":
            point_id = self.point_combo.currentData()
            if point_id is None:
                QMessageBox.warning(self, "提示", "请选择滴水点")
                return
            year = self.year_spin.value()
            month = self.month_spin.value()
            report_data = self.generator.generate_monthly_report(self.db, point_id, year, month)

        elif key == "anomaly":
            area_id = self.area_combo.currentData()
            report_data = self.generator.generate_anomaly_report(self.db, area_id=area_id)

        elif key == "joint":
            area_id = self.area_combo.currentData()
            if area_id is None:
                QMessageBox.warning(self, "提示", "请选择洞区（联合分析报告需要指定洞区且至少包含2个滴水点）")
                return
            report_data = self.generator.generate_joint_analysis_report(self.db, area_id)

        if report_data is None:
            QMessageBox.warning(self, "失败", "报告生成失败，请检查参数后重试")
            return

        self.current_report_data = report_data
        self._display_report(report_data)
        self.export_csv_btn.setEnabled(True)
        self.export_text_btn.setEnabled(True)
        self.data_changed.emit()

    def _display_report(self, report_data: Dict):
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"  {report_data.get('title', '监测报告')}")
        lines.append(f"{'=' * 60}")
        lines.append("")

        if report_data.get("generated_at"):
            lines.append(f"生成时间: {report_data['generated_at']}")
        if report_data.get("report_type"):
            lines.append(f"报告类型: {report_data['report_type']}")
        lines.append("")

        summary = report_data.get("summary")
        if summary:
            lines.append(f"--- 摘要 ---")
            if isinstance(summary, dict):
                for k, v in summary.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {summary}")
            lines.append("")

        data = report_data.get("data", [])
        if data:
            lines.append(f"--- 数据详情 ({len(data)} 条) ---")
            if data:
                headers = list(data[0].keys())
                lines.append("  " + " | ".join(headers))
                lines.append("  " + "-" * (len(" | ".join(headers))))
                for row in data:
                    values = [str(row.get(h, "-")) for h in headers]
                    lines.append("  " + " | ".join(values))
            lines.append("")

        stats = report_data.get("statistics")
        if stats:
            lines.append(f"--- 统计信息 ---")
            if isinstance(stats, dict):
                for k, v in stats.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {stats}")
            lines.append("")

        notes = report_data.get("notes")
        if notes:
            lines.append(f"--- 备注 ---")
            lines.append(f"  {notes}")

        lines.append(f"{'=' * 60}")
        self.preview_text.setPlainText("\n".join(lines))

    def _on_export_csv(self):
        if self.current_report_data is None:
            QMessageBox.warning(self, "提示", "请先生成报告")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出CSV", "", "CSV文件 (*.csv)"
        )
        if not file_path:
            return
        if not file_path.endswith(".csv"):
            file_path += ".csv"
        success, msg = self.generator.export_to_csv(self.current_report_data, file_path)
        if success:
            QMessageBox.information(self, "成功", f"报告已导出到: {msg}")
        else:
            QMessageBox.warning(self, "失败", msg)

    def _on_export_text(self):
        if self.current_report_data is None:
            QMessageBox.warning(self, "提示", "请先生成报告")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出文本", "", "文本文件 (*.txt)"
        )
        if not file_path:
            return
        if not file_path.endswith(".txt"):
            file_path += ".txt"
        success, msg = self.generator.export_to_text(self.current_report_data, file_path)
        if success:
            QMessageBox.information(self, "成功", f"报告已导出到: {msg}")
        else:
            QMessageBox.warning(self, "失败", msg)
