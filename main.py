import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase

from ui.main_window import MainWindow


def _pick_app_font() -> QFont:
    db = QFontDatabase()
    families = db.families()
    for name in ["PingFang SC", "Heiti SC", "STHeiti", "Microsoft YaHei",
                  "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]:
        if name in families:
            return QFont(name, 10)
    return QFont()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("海蚀洞滴水监测数据管理系统")
    app.setOrganizationName("Geology Research")
    app.setFont(_pick_app_font())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
