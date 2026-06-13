import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

print('=== Testing Main Window ===')
try:
    from ui.main_window import MainWindow
    window = MainWindow()
    print('MainWindow created successfully!')

    print('\nTesting tab switch to each tab...')
    tab_widget = window.tab_widget
    for i in range(tab_widget.count()):
        tab_name = tab_widget.tabText(i)
        try:
            tab_widget.setCurrentIndex(i)
            print(f'  Tab {i} [{tab_name}]: OK')
        except Exception as e:
            import traceback
            print(f'  Tab {i} [{tab_name}]: ERROR - {e}')
            traceback.print_exc()

    print('\nTesting chart refresh...')
    try:
        window._on_refresh_chart()
        print('Chart refresh: OK')
    except Exception as e:
        import traceback
        print(f'Chart refresh: ERROR - {e}')
        traceback.print_exc()

    print('\nMain window test passed!')
except Exception as e:
    import traceback
    print(f'MainWindow: ERROR - {e}')
    traceback.print_exc()

print('\nAll tests done!')
