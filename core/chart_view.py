import matplotlib
matplotlib.use("QtAgg")
import matplotlib.font_manager as fm

_FONT_CANDIDATES = [
    "PingFang SC", "Heiti SC", "STHeiti", "SimHei", "Microsoft YaHei",
    "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Arial Unicode MS",
]

def _find_chinese_font():
    available = {f.name for f in fm.fontManager.ttflist}
    for name in _FONT_CANDIDATES:
        if name in available:
            return name
    return None

_CHINESE_FONT = _find_chinese_font()
if _CHINESE_FONT:
    matplotlib.rcParams["font.sans-serif"] = [_CHINESE_FONT] + matplotlib.rcParams["font.sans-serif"]
matplotlib.rcParams["axes.unicode_minus"] = False

from datetime import datetime
from typing import List, Dict, Optional, Tuple
import numpy as np

from matplotlib.figure import Figure
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.dates import DateFormatter, AutoDateLocator
import matplotlib.patches as mpatches

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QCheckBox, QGroupBox
from PySide6.QtCore import Qt

from .anomaly_detector import AnomalyDetector, DetectionResult, AnomalySegment, SEASONS, ANOMALY_TYPES


COLORS = {
    "interval": "#1f77b4",
    "temperature": "#ff7f0e",
    "humidity": "#2ca02c",
    "salinity": "#d62728",
    "baseline": "#7f7f7f",
    "anomaly_blockage": "#d62728",
    "anomaly_seepage": "#9467bd",
    "anomaly_sudden": "#ff7f0e",
    "anomaly_fluctuation": "#ffbb78",
    "gap": "#c4c4c4",
}

SEASON_COLORS = {
    "春季": "#98df8a",
    "夏季": "#ff9896",
    "秋季": "#ffbb78",
    "冬季": "#aec7e8",
}


class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.data: List[Dict] = []
        self.anomalies: List[AnomalySegment] = []
        self.baseline_mean = 0.0
        self.baseline_std = 0.0
        self.fig.tight_layout()

    def clear_figure(self):
        self.fig.clear()
        self.draw()

    def _parse_dates(self, data: List[Dict]) -> List[datetime]:
        return [datetime.strptime(d["record_time"], "%Y-%m-%d %H:%M:%S") for d in data]

    def _plot_anomaly_regions(self, ax, anomalies: List[AnomalySegment], dates: List[datetime], y_min: float, y_max: float):
        for seg in anomalies:
            if seg.start_idx >= len(dates) or seg.end_idx >= len(dates):
                continue
            
            start_date = dates[seg.start_idx]
            end_date = dates[seg.end_idx]
            
            color = COLORS["anomaly_fluctuation"]
            if seg.anomaly_type == "blockage":
                color = COLORS["anomaly_blockage"]
            elif seg.anomaly_type == "increased_seepage":
                color = COLORS["anomaly_seepage"]
            elif seg.anomaly_type == "sudden_change":
                color = COLORS["anomaly_sudden"]
            elif seg.anomaly_type == "data_gap":
                color = COLORS["gap"]
            
            ax.axvspan(start_date, end_date, alpha=0.2, color=color, zorder=0)

    def plot_rhythm_curve(self, data: List[Dict], detection_result: Optional[DetectionResult] = None,
                          show_temp: bool = True, show_humidity: bool = True, show_salinity: bool = True):
        self.fig.clear()
        self.data = data
        self.anomalies = detection_result.segments if detection_result else []
        self.baseline_mean = detection_result.baseline_mean if detection_result else 0.0
        self.baseline_std = detection_result.baseline_std if detection_result else 0.0
        
        if not data:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "暂无数据", transform=ax.transAxes, 
                    ha="center", va="center", fontsize=14, color="gray")
            self.draw()
            return
        
        dates = self._parse_dates(data)
        intervals = [d["drip_interval"] for d in data]
        temps = [d["temperature"] for d in data]
        hums = [d["humidity"] for d in data]
        sals = [d["salinity"] for d in data]
        
        ax1 = self.fig.add_subplot(111)
        
        if detection_result:
            self._plot_anomaly_regions(ax1, detection_result.segments, dates, min(intervals), max(intervals))
        
        line1, = ax1.plot(dates, intervals, color=COLORS["interval"], linewidth=1.5, label="滴水间隔")
        ax1.set_ylabel("滴水间隔 (秒)", color=COLORS["interval"], fontsize=10)
        ax1.tick_params(axis="y", labelcolor=COLORS["interval"])
        ax1.set_xlabel("时间", fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        if self.baseline_mean > 0:
            ax1.axhline(y=self.baseline_mean, color=COLORS["baseline"], linestyle="--", 
                       linewidth=1, label=f"基线 ({self.baseline_mean:.1f}s)")
            ax1.fill_between(dates, 
                           self.baseline_mean - self.baseline_std,
                           self.baseline_mean + self.baseline_std,
                           color=COLORS["baseline"], alpha=0.1, label="±1σ")
        
        ax2 = None
        lines = [line1]
        labels = ["滴水间隔"]
        
        if show_temp and any(t is not None for t in temps):
            if ax2 is None:
                ax2 = ax1.twinx()
            valid_indices = [i for i, t in enumerate(temps) if t is not None]
            if valid_indices:
                valid_dates = [dates[i] for i in valid_indices]
                valid_temps = [temps[i] for i in valid_indices]
                line2, = ax2.plot(valid_dates, valid_temps, color=COLORS["temperature"], 
                                 linewidth=1, alpha=0.7, label="温度")
                lines.append(line2)
                labels.append("温度 (℃)")
                ax2.set_ylabel("温度 (℃) / 湿度 (%) / 盐度 (‰)", fontsize=10)
        
        if show_humidity and any(h is not None for h in hums):
            if ax2 is None:
                ax2 = ax1.twinx()
            valid_indices = [i for i, h in enumerate(hums) if h is not None]
            if valid_indices:
                valid_dates = [dates[i] for i in valid_indices]
                valid_hums = [hums[i] for i in valid_indices]
                line3, = ax2.plot(valid_dates, valid_hums, color=COLORS["humidity"], 
                                 linewidth=1, alpha=0.7, label="湿度")
                lines.append(line3)
                labels.append("湿度 (%)")
        
        if show_salinity and any(s is not None for s in sals):
            if ax2 is None:
                ax2 = ax1.twinx()
            valid_indices = [i for i, s in enumerate(sals) if s is not None]
            if valid_indices:
                valid_dates = [dates[i] for i in valid_indices]
                valid_sals = [sals[i] for i in valid_indices]
                line4, = ax2.plot(valid_dates, valid_sals, color=COLORS["salinity"], 
                                 linewidth=1, alpha=0.7, label="盐度")
                lines.append(line4)
                labels.append("盐度 (‰)")
        
        ax1.legend(lines, labels, loc="upper left", fontsize=9)
        
        if detection_result and detection_result.segments:
            legend_patches = []
            type_names = set()
            for seg in detection_result.segments:
                type_names.add(seg.anomaly_type)
            for atype in type_names:
                color = COLORS.get(f"anomaly_{atype}", COLORS["anomaly_fluctuation"])
                name = ANOMALY_TYPES.get(atype, atype)
                patch = mpatches.Patch(color=color, alpha=0.3, label=name)
                legend_patches.append(patch)
            if legend_patches:
                ax1.legend(handles=legend_patches, loc="upper right", fontsize=9, title="异常类型")
        
        locator = AutoDateLocator()
        formatter = DateFormatter("%m-%d %H:%M")
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate()
        
        ax1.set_title("滴水节律曲线", fontsize=12, pad=10)
        self.fig.tight_layout()
        self.draw()

    def plot_season_comparison(self, data: List[Dict], comparison: Dict[str, Dict]):
        self.fig.clear()
        self.data = data
        
        if not data or not comparison:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "暂无季节数据", transform=ax.transAxes, 
                    ha="center", va="center", fontsize=14, color="gray")
            self.draw()
            return
        
        gs = self.fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        ax1 = self.fig.add_subplot(gs[0, 0])
        seasons = list(comparison.keys())
        means = [comparison[s]["interval_mean"] for s in seasons]
        stds = [comparison[s]["interval_std"] for s in seasons]
        colors = [SEASON_COLORS.get(s, "#888888") for s in seasons]
        
        bars = ax1.bar(seasons, means, yerr=stds, capsize=5, color=colors, alpha=0.7, edgecolor="black")
        ax1.set_ylabel("平均滴水间隔 (秒)", fontsize=10)
        ax1.set_title("各季节平均滴水间隔", fontsize=11)
        ax1.grid(True, alpha=0.3, axis="y")
        
        for bar, mean in zip(bars, means):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f"{mean:.1f}", ha="center", va="bottom", fontsize=9)
        
        ax2 = self.fig.add_subplot(gs[0, 1])
        counts = [comparison[s]["count"] for s in seasons]
        ax2.pie(counts, labels=seasons, colors=colors, autopct="%1.1f%%", 
                startangle=90, textprops={"fontsize": 9})
        ax2.set_title("数据量分布", fontsize=11)
        
        ax3 = self.fig.add_subplot(gs[1, :])
        for season_name in seasons:
            season_data = AnomalyDetector.get_season_data(data, season_name)
            if season_data:
                dates = self._parse_dates(season_data)
                intervals = [d["drip_interval"] for d in season_data]
                color = SEASON_COLORS.get(season_name, "#888888")
                ax3.plot(dates, intervals, color=color, linewidth=1.2, label=season_name, alpha=0.8)
        
        ax3.set_ylabel("滴水间隔 (秒)", fontsize=10)
        ax3.set_xlabel("时间", fontsize=10)
        ax3.set_title("各季节滴水间隔对比", fontsize=11)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.3)
        
        locator = AutoDateLocator()
        formatter = DateFormatter("%m-%d")
        ax3.xaxis.set_major_locator(locator)
        ax3.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate()
        
        self.fig.tight_layout()
        self.draw()

    def plot_anomaly_statistics(self, detection_result: DetectionResult):
        self.fig.clear()
        
        if not detection_result.segments:
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, "未检测到异常", transform=ax.transAxes, 
                    ha="center", va="center", fontsize=14, color="gray")
            self.draw()
            return
        
        gs = self.fig.add_gridspec(1, 2, wspace=0.3)
        
        ax1 = self.fig.add_subplot(gs[0])
        type_counts: Dict[str, int] = {}
        for seg in detection_result.segments:
            atype = ANOMALY_TYPES.get(seg.anomaly_type, seg.anomaly_type)
            type_counts[atype] = type_counts.get(atype, 0) + 1
        
        types = list(type_counts.keys())
        counts = list(type_counts.values())
        colors = [COLORS.get(f"anomaly_{t}", COLORS["anomaly_fluctuation"]) for t in types]
        
        bars = ax1.bar(types, counts, color=colors, alpha=0.7, edgecolor="black")
        ax1.set_ylabel("异常段数量", fontsize=10)
        ax1.set_title("异常类型分布", fontsize=11)
        ax1.grid(True, alpha=0.3, axis="y")
        ax1.tick_params(axis="x", rotation=30)
        
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    str(count), ha="center", va="bottom", fontsize=9)
        
        ax2 = self.fig.add_subplot(gs[1])
        risk_counts: Dict[str, int] = {}
        for seg in detection_result.segments:
            risk_counts[seg.risk_level] = risk_counts.get(seg.risk_level, 0) + 1
        
        risk_order = ["低", "中", "高", "极高"]
        risks = [r for r in risk_order if r in risk_counts]
        counts = [risk_counts[r] for r in risks]
        risk_colors = {"低": "#2ca02c", "中": "#ffbb78", "高": "#ff7f0e", "极高": "#d62728"}
        colors = [risk_colors.get(r, "#888888") for r in risks]
        
        ax2.pie(counts, labels=risks, colors=colors, autopct="%1.1f%%", 
                startangle=90, textprops={"fontsize": 10})
        ax2.set_title("风险等级分布", fontsize=11)
        
        self.fig.tight_layout()
        self.draw()


class ChartViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chart_canvas = ChartCanvas(self, width=10, height=6)
        self.toolbar = NavigationToolbar(self.chart_canvas, self)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        
        control_group = QGroupBox("显示选项")
        control_layout = QHBoxLayout(control_group)
        
        self.chk_temp = QCheckBox("温度")
        self.chk_temp.setChecked(True)
        self.chk_humidity = QCheckBox("湿度")
        self.chk_humidity.setChecked(True)
        self.chk_salinity = QCheckBox("盐度")
        self.chk_salinity.setChecked(True)
        
        self.chk_temp.stateChanged.connect(self._on_display_changed)
        self.chk_humidity.stateChanged.connect(self._on_display_changed)
        self.chk_salinity.stateChanged.connect(self._on_display_changed)
        
        control_layout.addWidget(QLabel("叠加显示:"))
        control_layout.addWidget(self.chk_temp)
        control_layout.addWidget(self.chk_humidity)
        control_layout.addWidget(self.chk_salinity)
        control_layout.addStretch()
        
        layout.addWidget(control_group)
        layout.addWidget(self.chart_canvas, stretch=1)
        
        self.current_data = []
        self.current_result = None
        self.current_comparison = None
        self.current_mode = "rhythm"

    def _on_display_changed(self):
        if self.current_mode == "rhythm" and self.current_data:
            self.plot_rhythm(self.current_data, self.current_result)

    def plot_rhythm(self, data: List[Dict], detection_result: Optional[DetectionResult] = None):
        self.current_mode = "rhythm"
        self.current_data = data
        self.current_result = detection_result
        self.chart_canvas.plot_rhythm_curve(
            data, detection_result,
            show_temp=self.chk_temp.isChecked(),
            show_humidity=self.chk_humidity.isChecked(),
            show_salinity=self.chk_salinity.isChecked()
        )

    def plot_season(self, data: List[Dict], comparison: Dict[str, Dict]):
        self.current_mode = "season"
        self.current_data = data
        self.current_comparison = comparison
        self.chart_canvas.plot_season_comparison(data, comparison)

    def plot_anomaly(self, detection_result: DetectionResult):
        self.current_mode = "anomaly"
        self.current_result = detection_result
        self.chart_canvas.plot_anomaly_statistics(detection_result)

    def clear(self):
        self.current_data = []
        self.current_result = None
        self.current_comparison = None
        self.chart_canvas.clear_figure()
