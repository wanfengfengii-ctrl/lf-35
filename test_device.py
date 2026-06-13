import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

print('Testing DevicePanel...')
try:
    from ui.device_panel import DevicePanel
    panel = DevicePanel()
    print('DevicePanel created successfully!')

    print('\nCalling refresh()...')
    try:
        panel.refresh()
        print('refresh() succeeded!')
    except Exception as e:
        import traceback
        print(f'refresh() ERROR: {e}')
        traceback.print_exc()

    print('\nDone.')
except Exception as e:
    import traceback
    print(f'Create ERROR: {e}')
    traceback.print_exc()
