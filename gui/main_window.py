import os

from PyQt6.QtCore import QThread, Signal, Slot
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit,
    QFileDialog, QTabWidget, QFormLayout, QComboBox, QDoubleSpinBox,
    QSpinBox, QTextEdit, QTableWidget, QHeaderView, QTableWidgetItem,
    QMessageBox
)

from .api_client import ApiClient


# --- 异步任务处理器 ---
class TaskWorker(QThread):
    """
    将 API 请求放在单独的线程中，避免 UI 阻塞。
    """
    # 定义信号：(任务ID, 任务类型, 状态, 消息)
    status_updated = Signal(str, str, str, str)
    task_completed = Signal(str, dict)
    task_failed = Signal(str, str)

    def __init__(self, api_client: ApiClient, task_id: str, task_type: str):
        super().__init__()
        self.api_client = api_client
        self.task_id = task_id
        self.task_type = task_type
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                status_data = self.api_client.get_task_status(self.task_id)
                status = status_data.get("status")
                message = status_data.get("message", "")

                self.status_updated.emit(self.task_id, self.task_type, status, message)

                if status == "completed":
                    self.task_completed.emit(self.task_id, status_data.get("result", {}))
                    break
                elif status == "failed":
                    self.task_failed.emit(self.task_id, message)
                    break

                self.sleep(5)  # 每 5 秒轮询一次
            except Exception as e:
                self.task_failed.emit(self.task_id, f"轮询状态时发生错误: {e}")
                break

    def stop(self):
        self.is_running = False


# --- 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self, api_client: ApiClient):
        super().__init__()
        self.api_client = api_client
        self.workers = {}  # 存储正在运行的 QThread worker
        self.task_row_map = {}  # 存储 task_id 到表格行的映射

        self.setWindowTitle("AutoVoiceCollation 客户端")
        self.setGeometry(100, 100, 800, 600)

        # --- 中心控件和布局 ---
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- 创建各个功能的 Tab ---
        self.create_bilibili_tab()
        self.create_local_file_tab()
        self.create_batch_tab()
        self.create_subtitle_tab()

        # --- 创建任务监控表格 ---
        self.create_task_monitor_table()

    def create_task_monitor_table(self):
        """创建一个集中的任务监控区域"""
        main_layout = self.centralWidget().layout()
        if not main_layout:
            main_layout = QVBoxLayout(self.centralWidget())

        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["任务 ID", "类型", "状态", "信息", "操作"])
        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.task_table.setEditTriggers(QTableWidget.NoEditTriggers)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.task_table)

        # 将任务监控表格添加到主窗口布局中
        if isinstance(self.centralWidget(), QTabWidget):
            # 如果是Tab布局，将其放在Tab下方
            vbox = QVBoxLayout()
            vbox.addWidget(self.tabs)
            vbox.addWidget(container)
            central_container = QWidget()
            central_container.setLayout(vbox)
            self.setCentralWidget(central_container)
        else:
            main_layout.addWidget(container)

    def add_task_to_table(self, task_id: str, task_type: str):
        """向监控表格中添加一个新任务"""
        row_position = self.task_table.rowCount()
        self.task_table.insertRow(row_position)
        self.task_table.setItem(row_position, 0, QTableWidgetItem(task_id))
        self.task_table.setItem(row_position, 1, QTableWidgetItem(task_type))
        self.task_table.setItem(row_position, 2, QTableWidgetItem("pending"))
        self.task_table.setItem(row_position, 3, QTableWidgetItem("已提交..."))
        self.task_row_map[task_id] = row_position

    @Slot(str, str, str, str)
    def update_task_status(self, task_id, task_type, status, message):
        """更新表格中的任务状态"""
        if task_id in self.task_row_map:
            row = self.task_row_map[task_id]
            self.task_table.setItem(row, 2, QTableWidgetItem(status))
            self.task_table.setItem(row, 3, QTableWidgetItem(message))

    @Slot(str, dict)
    def on_task_completed(self, task_id, result):
        """任务完成后的处理"""
        if task_id in self.task_row_map:
            row = self.task_row_map[task_id]
            self.task_table.setItem(row, 2, QTableWidgetItem("✅ completed"))
            download_btn = QPushButton("下载结果")
            download_btn.clicked.connect(lambda: self.download_result(task_id))
            self.task_table.setCellWidget(row, 4, download_btn)

    @Slot(str, str)
    def on_task_failed(self, task_id, error_message):
        """任务失败后的处理"""
        if task_id in self.task_row_map:
            row = self.task_row_map[task_id]
            self.task_table.setItem(row, 2, QTableWidgetItem("❌ failed"))
            self.task_table.setItem(row, 3, QTableWidgetItem(error_message))
            QMessageBox.critical(self, "任务失败", f"任务 {task_id} 失败: {error_message}")

    def download_result(self, task_id):
        save_path, _ = QFileDialog.getSaveFileName(self, "保存结果", f"{task_id}.zip", "ZIP Files (*.zip)")
        if save_path:
            try:
                self.api_client.download_result(task_id, save_path)
                QMessageBox.information(self, "下载完成", f"结果已保存到:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "下载失败", f"下载任务 {task_id} 的结果时出错: {e}")

    def _create_common_llm_options(self):
        """创建通用的 LLM 参数设置表单"""
        form_layout = QFormLayout()
        llm_api = QComboBox()
        llm_api.addItems(["deepseek-chat", "deepseek-reasoner", "gemini-2.0-flash", "qwen3-max"])

        temperature = QDoubleSpinBox()
        temperature.setRange(0.0, 2.0)
        temperature.setSingleStep(0.1)
        temperature.setValue(0.1)

        max_tokens = QSpinBox()
        max_tokens.setRange(1, 16000)
        max_tokens.setValue(6000)

        form_layout.addRow("LLM 模型:", llm_api)
        form_layout.addRow("Temperature:", temperature)
        form_layout.addRow("Max Tokens:", max_tokens)

        return form_layout, llm_api, temperature, max_tokens

    def create_bilibili_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.bili_url_input = QLineEdit()
        self.bili_url_input.setPlaceholderText("https://www.bilibili.com/video/BV...")

        form_layout, llm_api, temp, tokens = self._create_common_llm_options()

        submit_btn = QPushButton("提交 B 站视频处理任务")
        submit_btn.clicked.connect(lambda: self.submit_bilibili_task(
            self.bili_url_input.text(),
            llm_api.currentText(),
            temp.value(),
            tokens.value()
        ))

        layout.addWidget(self.bili_url_input)
        layout.addLayout(form_layout)
        layout.addWidget(submit_btn)
        layout.addStretch()
        self.tabs.addTab(tab, "B 站视频")

    def create_local_file_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 文件选择
        self.audio_path_input = QLineEdit()
        self.audio_path_input.setPlaceholderText("点击右侧按钮选择本地音频文件...")
        self.audio_path_input.setReadOnly(True)
        btn_select_audio = QPushButton("选择文件")
        btn_select_audio.clicked.connect(self.select_audio_file)

        form_layout, llm_api, temp, tokens = self._create_common_llm_options()

        submit_btn = QPushButton("提交音频文件处理任务")
        submit_btn.clicked.connect(lambda: self.submit_audio_task(
            self.audio_path_input.text(),
            llm_api.currentText(),
            temp.value(),
            tokens.value()
        ))

        file_layout = QFormLayout()
        file_layout.addRow(self.audio_path_input, btn_select_audio)

        layout.addLayout(file_layout)
        layout.addLayout(form_layout)
        layout.addWidget(submit_btn)
        layout.addStretch()
        self.tabs.addTab(tab, "本地音频")

    def create_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.batch_urls_input = QTextEdit()
        self.batch_urls_input.setPlaceholderText("每行一个 B 站视频链接...")

        form_layout, llm_api, temp, tokens = self._create_common_llm_options()

        submit_btn = QPushButton("提交批量处理任务")
        submit_btn.clicked.connect(lambda: self.submit_batch_task(
            self.batch_urls_input.toPlainText(),
            llm_api.currentText(),
            temp.value(),
            tokens.value()
        ))

        layout.addWidget(self.batch_urls_input)
        layout.addLayout(form_layout)
        layout.addWidget(submit_btn)
        self.tabs.addTab(tab, "批量处理")

    def create_subtitle_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.video_path_input = QLineEdit()
        self.video_path_input.setPlaceholderText("点击右侧按钮选择本地视频文件...")
        self.video_path_input.setReadOnly(True)
        btn_select_video = QPushButton("选择文件")
        btn_select_video.clicked.connect(self.select_video_file)

        submit_btn = QPushButton("开始生成字幕")
        submit_btn.clicked.connect(lambda: self.submit_subtitle_task(self.video_path_input.text()))

        file_layout = QFormLayout()
        file_layout.addRow(self.video_path_input, btn_select_video)

        layout.addLayout(file_layout)
        layout.addWidget(submit_btn)
        layout.addStretch()
        self.tabs.addTab(tab, "视频字幕")

    # --- 文件选择槽函数 ---
    def select_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.m4a *.flac)")
        if path:
            self.audio_path_input.setText(path)

    def select_video_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov)")
        if path:
            self.video_path_input.setText(path)

    # --- 任务提交槽函数 ---
    def _start_task_monitoring(self, task_id, task_type):
        """启动一个 worker 线程来监控任务"""
        self.add_task_to_table(task_id, task_type)
        worker = TaskWorker(self.api_client, task_id, task_type)
        worker.status_updated.connect(self.update_task_status)
        worker.task_completed.connect(self.on_task_completed)
        worker.task_failed.connect(self.on_task_failed)
        worker.finished.connect(lambda: self.workers.pop(task_id, None))  # 线程结束后清理
        self.workers[task_id] = worker
        worker.start()

    def submit_bilibili_task(self, url, llm, temp, tokens):
        if not url:
            QMessageBox.warning(self, "警告", "请输入 B 站视频链接！")
            return
        try:
            response = self.api_client.process_bilibili(url, llm, temp, tokens)
            task_id = response['task_id']
            self._start_task_monitoring(task_id, "B站视频")
        except Exception as e:
            QMessageBox.critical(self, "提交失败", f"请求失败: {e}")

    def submit_audio_task(self, file_path, llm, temp, tokens):
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择一个有效的音频文件！")
            return
        try:
            response = self.api_client.process_audio(file_path, llm, temp, tokens)
            task_id = response['task_id']
            self._start_task_monitoring(task_id, "本地音频")
        except Exception as e:
            QMessageBox.critical(self, "提交失败", f"请求失败: {e}")

    def submit_batch_task(self, urls_text, llm, temp, tokens):
        urls = [url.strip() for url in urls_text.splitlines() if url.strip()]
        if not urls:
            QMessageBox.warning(self, "警告", "请输入至少一个 B 站视频链接！")
            return
        try:
            response = self.api_client.process_batch(urls, llm, temp, tokens)
            task_id = response['task_id']
            self._start_task_monitoring(task_id, "批量处理")
        except Exception as e:
            QMessageBox.critical(self, "提交失败", f"请求失败: {e}")

    def submit_subtitle_task(self, file_path):
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "请选择一个有效的视频文件！")
            return
        try:
            response = self.api_client.process_subtitle(file_path)
            task_id = response['task_id']
            self._start_task_monitoring(task_id, "视频字幕")
        except Exception as e:
            QMessageBox.critical(self, "提交失败", f"请求失败: {e}")

    def closeEvent(self, event):
        """关闭窗口时停止所有正在运行的线程"""
        for worker in self.workers.values():
            worker.stop()
            worker.wait()  # 等待线程完全退出
        event.accept()
