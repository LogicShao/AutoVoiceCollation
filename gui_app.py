import sys

from PyQt6.QtWidgets import QApplication, QMessageBox
from qt_material import apply_stylesheet

from gui.api_client import ApiClient
from gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 启动前检查后端服务是否在线
    api_client = ApiClient()
    if not api_client.check_health():
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Critical)
        error_box.setText("无法连接到后端 API 服务！")
        error_box.setInformativeText("请确保您已经通过 `python api.py` 启动了后端服务。")
        error_box.setWindowTitle("连接错误")
        error_box.exec()
        sys.exit(1)

    # 应用 Material Design 样式
    apply_stylesheet(app, theme='dark_teal.xml')

    window = MainWindow(api_client)
    window.show()

    sys.exit(app.exec())
