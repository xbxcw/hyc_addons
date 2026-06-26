import os
import json
import subprocess
import datetime

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QProgressBar,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QAbstractItemView,
    QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from utils.sbsar_utils import (
    get_sbsar_exposed_params,
    get_image_dimensions,
    get_power_exponent,
    is_checkbox_param,
)


class DropFolderListWidget(QListWidget):
    """支持拖拽文件夹的列表控件，用于管理多个输入目录。

    信号:
        folders_dropped(list): 当新文件夹被拖入时触发，参数为新增的文件夹路径列表。
    """
    folders_dropped = Signal(list)

    def __init__(self, parent=None):
        """初始化拖拽文件夹列表控件。

        参数:
            parent: 父级控件。
        """
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setMinimumHeight(80)
        self.setPlaceholderText('拖拽文件夹到此处，或点击"添加"按钮')

    def setPlaceholderText(self, text):
        """设置占位提示文本（当前未在UI中展示）。"""
        self._placeholder = text

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件：仅接受文件/文件夹 URL 拖拽。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件：仅接受文件/文件夹 URL 拖拽。"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件：提取文件夹路径并添加到列表（自动去重）。"""
        new_folders = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path) and path not in self.get_all_folders():
                self.add_folder(path)
                new_folders.append(path)
        if new_folders:
            self.folders_dropped.emit(new_folders)
        event.acceptProposedAction()

    def add_folder(self, path):
        """向列表中添加一个文件夹路径。

        参数:
            path: 文件夹的绝对路径。
        """
        item = QListWidgetItem(path)
        item.setToolTip(path)
        self.addItem(item)

    def get_all_folders(self):
        """获取当前列表中所有文件夹路径。

        返回:
            list[str]: 文件夹路径列表。
        """
        return [self.item(i).text() for i in range(self.count())]

    def remove_selected(self):
        """移除当前选中的文件夹条目。"""
        for item in self.selectedItems():
            self.takeItem(self.row(item))


class WorkerThread(QThread):
    """后台工作线程，用于异步获取 SBSAR 文件的暴露参数。

    信号:
        finished(list): 参数获取完成，携带参数列表。
        error(str): 发生错误时触发，携带错误信息。
        progress(int): 进度更新，值为 0-100。
    """
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, sbsrender_exe, sbsar_file):
        """初始化工作线程。

        参数:
            sbsrender_exe: sbsrender.exe 的完整路径。
            sbsar_file: SBSAR 文件的完整路径。
        """
        super().__init__()
        self.sbsrender_exe = sbsrender_exe
        self.sbsar_file = sbsar_file

    def run(self):
        """线程执行入口：调用 sbsrender 获取参数并发送结果信号。"""
        try:
            self.progress.emit(50)
            params = get_sbsar_exposed_params(self.sbsrender_exe, self.sbsar_file)
            self.progress.emit(100)
            self.finished.emit(params)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """SBSAR 参数查看器主窗口。

    提供 SBSAR 参数解析、多目录贴图匹配、sbsrender 批量渲染等功能。
    """

    def __init__(self):
        """初始化主窗口，设置 UI 并加载配置。"""
        super().__init__()
        self.image_params = []
        self.matched_files = []
        self.checkbox_widgets = {}
        self.config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),'cfg','sbsar_config.json')
        self.init_ui()
        self.load_config()

    def init_ui(self):
        """初始化所有 UI 组件并布局。"""
        self.setWindowTitle('SBSAR 参数查看器')
        self.setGeometry(100, 100, 700, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        title_label = QLabel('SBSAR Exposed Parameters Viewer')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet('font-size: 18px; font-weight: bold; color: #333; margin-bottom: 15px;')
        main_layout.addWidget(title_label)

        self._build_sd_group(main_layout)
        self._build_sbsar_group(main_layout)
        self._build_input_group(main_layout)
        self._build_output_group(main_layout)

        self._build_bool_group(main_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self._build_buttons(main_layout)
        self._build_log_group(main_layout)
        self._build_result_group(main_layout)

        self.log('初始化完成，准备获取SBSAR参数...')

    def _build_sd_group(self, parent):
        """构建 SD 安装目录选择区域。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('SD安装目录')
        layout = QHBoxLayout()
        group.setLayout(layout)

        self.sd_dir_input = QLineEdit()
        self.sd_dir_input.setPlaceholderText('例如: C:/Program Files/Adobe/Adobe Substance 3D Designer')
        browse_btn = QPushButton('浏览')
        browse_btn.clicked.connect(self.browse_sd_dir)

        layout.addWidget(QLabel('SD目录:'))
        layout.addWidget(self.sd_dir_input)
        layout.addWidget(browse_btn)
        parent.addWidget(group)

    def _build_sbsar_group(self, parent):
        """构建 SBSAR 文件选择区域。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('SBSAR文件')
        layout = QHBoxLayout()
        group.setLayout(layout)

        self.sbsar_input = QLineEdit()
        self.sbsar_input.setPlaceholderText('例如: C:/materials/MyMaterial.sbsar')
        browse_btn = QPushButton('浏览')
        browse_btn.clicked.connect(self.browse_sbsar_file)

        layout.addWidget(QLabel('文件:'))
        layout.addWidget(self.sbsar_input)
        layout.addWidget(browse_btn)
        parent.addWidget(group)

    def _build_input_group(self, parent):
        """构建输入目录区域，包含拖拽列表和添加/移除按钮。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('输入目录（支持多文件夹拖拽）')
        main_layout = QVBoxLayout()
        group.setLayout(main_layout)

        self.input_folder_list = DropFolderListWidget()
        self.input_folder_list.folders_dropped.connect(self._on_folders_changed)
        main_layout.addWidget(self.input_folder_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton('添加')
        add_btn.clicked.connect(self.browse_input_folder)
        remove_btn = QPushButton('移除选中')
        remove_btn.clicked.connect(self.remove_input_folder)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        parent.addWidget(group)

    def _build_output_group(self, parent):
        """构建输出目录选择区域。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('输出目录')
        layout = QHBoxLayout()
        group.setLayout(layout)

        self.output_folder_input = QLineEdit()
        self.output_folder_input.setPlaceholderText('例如: C:/textures/output')
        browse_btn = QPushButton('浏览')
        browse_btn.clicked.connect(self.browse_output_folder)

        layout.addWidget(QLabel('路径:'))
        layout.addWidget(self.output_folder_input)
        layout.addWidget(browse_btn)
        parent.addWidget(group)

    def _build_bool_group(self, parent):
        """构建布尔参数复选框区域。

        参数:
            parent: 父级布局。
        """
        self.bool_group = QGroupBox('布尔参数（is_ 开头的 INTEGER1 参数）')
        self.bool_layout = QHBoxLayout()
        self.bool_group.setLayout(self.bool_layout)
        self.bool_group.setVisible(False)
        parent.addWidget(self.bool_group)

    def _populate_checkboxes(self, params):
        """根据参数列表创建复选框。

        清除旧复选框，为 is_ 开头且类型为 INTEGER1 的参数创建 QCheckBox。

        参数:
            params: 参数列表。
        """
        for i in reversed(range(self.bool_layout.count())):
            widget = self.bool_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.checkbox_widgets.clear()

        checkbox_params = [p for p in params if is_checkbox_param(p)]
        if checkbox_params:
            for param in checkbox_params:
                name = param['name']
                default_val = param.get('default', '0')
                cb = QCheckBox(name)
                cb.setChecked(default_val in ('1', 'true', 'True'))
                self.bool_layout.addWidget(cb)
                self.checkbox_widgets[name] = cb
            self.bool_group.setVisible(True)
            self.log(f'找到 {len(checkbox_params)} 个布尔参数')
        else:
            self.bool_group.setVisible(False)

    def _build_buttons(self, parent):
        """构建操作按钮区域（获取参数、查找贴图、导出贴图、清空）。

        参数:
            parent: 父级布局。
        """
        layout = QHBoxLayout()

        self.run_btn = QPushButton('获取参数')
        self.run_btn.clicked.connect(self.on_run)
        layout.addWidget(self.run_btn)

        self.find_textures_btn = QPushButton('查找贴图')
        self.find_textures_btn.clicked.connect(self.on_find_textures)
        self.find_textures_btn.setEnabled(False)
        layout.addWidget(self.find_textures_btn)

        self.export_btn = QPushButton('导出贴图')
        self.export_btn.clicked.connect(self.on_export_textures)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton('清空')
        self.clear_btn.clicked.connect(self.on_clear)
        layout.addWidget(self.clear_btn)

        parent.addLayout(layout)

    def _build_log_group(self, parent):
        """构建日志输出区域。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('日志输出')
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet('background-color: #f5f5f5;')
        layout.addWidget(self.log_text)
        parent.addWidget(group)

    def _build_result_group(self, parent):
        """构建参数结果展示区域。

        参数:
            parent: 父级布局。
        """
        group = QGroupBox('参数结果')
        layout = QVBoxLayout()
        group.setLayout(layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        parent.addWidget(group)

    def load_config(self):
        """从 JSON 配置文件加载上次保存的设置。"""
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.sd_dir_input.setText(config.get('sd_dir', ''))
            self.sbsar_input.setText(config.get('sbsar_file', ''))
            self.output_folder_input.setText(config.get('output_folder', ''))

            input_folders = config.get('input_folders', [])
            if not input_folders:
                old_folder = config.get('input_folder', '')
                if old_folder:
                    input_folders = [old_folder]
            for folder in input_folders:
                if os.path.isdir(folder):
                    self.input_folder_list.add_folder(folder)

            self.log(f'配置已加载: {self.config_file}')
        except Exception as e:
            self.log(f'加载配置失败: {e}')

    def save_config(self):
        """将当前设置保存到 JSON 配置文件。"""
        config = {
            'sd_dir': self.sd_dir_input.text().strip(),
            'sbsar_file': self.sbsar_input.text().strip(),
            'input_folders': self.input_folder_list.get_all_folders(),
            'output_folder': self.output_folder_input.text().strip(),
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.log(f'配置已保存: {self.config_file}')
        except Exception as e:
            self.log(f'保存配置失败: {e}')

    def log(self, message):
        """向日志区域追加一条带时间戳的消息。

        参数:
            message: 日志消息内容。
        """
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f'[{timestamp}] {message}')

    def browse_sd_dir(self):
        """浏览并选择 SD 安装目录，自动检测 sbsrender.exe。"""
        dir_path = QFileDialog.getExistingDirectory(self, '选择SD安装目录')
        if not dir_path:
            return
        self.sd_dir_input.setText(dir_path)
        sbsrender_path = os.path.join(dir_path, 'sbsrender.exe')
        self.log(f'SD目录已选择: {dir_path}')
        if os.path.exists(sbsrender_path):
            self.log(f'sbsrender.exe 路径: {sbsrender_path}')
        else:
            self.log(f'警告: sbsrender.exe 不存在于该目录')
        self.save_config()

    def browse_sbsar_file(self):
        """浏览并选择 SBSAR 文件。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择SBSAR文件', '', 'SBSAR Files (*.sbsar)'
        )
        if file_path:
            self.sbsar_input.setText(file_path)
            self.log(f'SBSAR文件已选择: {file_path}')
            self.save_config()

    def browse_input_folder(self):
        """浏览并添加输入目录（自动去重）。"""
        dir_path = QFileDialog.getExistingDirectory(self, '选择输入目录')
        if not dir_path:
            return
        if dir_path in self.input_folder_list.get_all_folders():
            self.log(f'目录已存在: {dir_path}')
            return
        self.input_folder_list.add_folder(dir_path)
        self.log(f'输入目录已添加: {dir_path}')
        self.save_config()

    def remove_input_folder(self):
        """移除选中的输入目录。"""
        self.input_folder_list.remove_selected()
        self.save_config()

    def _on_folders_changed(self, folders):
        """拖拽文件夹后的回调：保存配置并记录日志。

        参数:
            folders: 新增的文件夹路径列表。
        """
        self.save_config()
        self.log(f'已拖入 {len(folders)} 个目录')

    def browse_output_folder(self):
        """浏览并选择输出目录。"""
        dir_path = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if dir_path:
            self.output_folder_input.setText(dir_path)
            self.log(f'输出目录已选择: {dir_path}')
            self.save_config()

    def on_run(self):
        """点击"获取参数"按钮：启动后台线程获取 SBSAR 暴露参数。"""
        sd_dir = self.sd_dir_input.text().strip()
        sbsar_file = self.sbsar_input.text().strip()

        if not sd_dir:
            self.log('错误: 请选择SD安装目录')
            return
        sbsrender_exe = os.path.join(sd_dir, 'sbsrender.exe')
        if not sbsar_file:
            self.log('错误: 请选择SBSAR文件')
            return
        if not os.path.exists(sbsrender_exe):
            self.log(f'错误: sbsrender.exe 不存在: {sbsrender_exe}')
            return
        if not os.path.exists(sbsar_file):
            self.log(f'错误: SBSAR 文件不存在: {sbsar_file}')
            return

        self.log(f'开始获取参数: {sbsar_file}')
        self.run_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_text.clear()

        self.worker = WorkerThread(sbsrender_exe, sbsar_file)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.progress.connect(self.on_progress)
        self.worker.start()

    def on_progress(self, value):
        """更新进度条数值。

        参数:
            value: 进度值 (0-100)。
        """
        self.progress_bar.setValue(value)

    def on_finished(self, params):
        """参数获取完成回调：解析参数并显示结果。

        参数:
            params: 从 sbsrender 获取的参数列表。
        """
        self.progress_bar.setValue(100)
        self.run_btn.setEnabled(True)

        if params:
            self.log(f'成功获取到 {len(params)} 个参数')
            self.image_params = [p['name'] for p in params if p.get('type') == 'IMAGE']

            if self.image_params:
                self.log(f'找到 {len(self.image_params)} 个IMAGE类型参数: {", ".join(self.image_params)}')
                self.find_textures_btn.setEnabled(True)
            else:
                self.log('未找到IMAGE类型的参数')
                self.find_textures_btn.setEnabled(False)

            self._populate_checkboxes(params)

            result = '参数列表:\n'
            result += '=' * 50 + '\n'
            for i, param in enumerate(params, 1):
                param_type = param.get('type', '')
                result += f"{i}. 名称: {param.get('name', '')}\n"
                result += f"   类型: {param_type}"
                if param_type == 'IMAGE':
                    result += ' (贴图参数)'
                if is_checkbox_param(param):
                    result += ' (布尔参数)'
                result += '\n'
                result += f"   默认值: {param.get('default', '')}\n"
                result += '-' * 50 + '\n'
            self.result_text.setPlainText(result)
        else:
            self.log('未找到任何暴露的参数')
            self.result_text.setPlainText('未找到任何暴露的参数')
            self.image_params = []
            self.find_textures_btn.setEnabled(False)

        self.progress_bar.setVisible(False)

    def on_find_textures(self):
        """点击"查找贴图"按钮：在所有输入目录中搜索匹配的贴图文件。"""
        input_folders = self.input_folder_list.get_all_folders()

        if not input_folders:
            self.log('错误: 请添加输入目录')
            return
        for folder in input_folders:
            if not os.path.exists(folder):
                self.log(f'错误: 输入目录不存在: {folder}')
                return
        if not self.image_params:
            self.log('错误: 未找到IMAGE类型参数，请先获取参数')
            return

        self.log(f'开始在 {len(input_folders)} 个目录中查找贴图...')
        self.log(f'搜索后缀: {", ".join(self.image_params)}')

        self.matched_files = []
        extensions = ('.tga', '.png', '.jpg')

        for input_folder in input_folders:
            self.log(f'  扫描目录: {input_folder}')
            for root, dirs, files in os.walk(input_folder):
                for filename in files:
                    for param_name in self.image_params:
                        for ext in extensions:
                            suffix = f'_{param_name}{ext}'
                            if filename.endswith(suffix):
                                break
                        else:
                            continue

                        base_name = filename.rsplit(f'_{param_name}', 1)[0]
                        if not base_name.startswith('T_'):
                            continue
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(root, input_folder)
                        self.matched_files.append({
                            'base_name': base_name,
                            'param_name': param_name,
                            'filename': filename,
                            'full_path': full_path,
                            'relative_path': relative_path if relative_path != '.' else '',
                            'source_folder': input_folder,
                        })

        if self.matched_files:
            self.log(f'找到 {len(self.matched_files)} 个匹配的贴图文件')
            result = self._format_matched_result()
            self.result_text.setPlainText(result)
            self.export_btn.setEnabled(True)
        else:
            self.log('未找到匹配的贴图文件')
            self.result_text.setPlainText('未找到匹配的贴图文件')
            self.export_btn.setEnabled(False)

    def _format_matched_result(self):
        """格式化匹配的贴图文件结果为可读文本。

        返回:
            str: 格式化后的匹配结果文本。
        """
        grouped = {}
        for f in self.matched_files:
            grouped.setdefault(f['base_name'], []).append(f)

        result = '匹配的贴图文件:\n'
        result += '=' * 60 + '\n'
        for base_name, files in grouped.items():
            result += f"基础名称: {base_name}\n"
            for f in files:
                path_info = f" [路径: {f['relative_path']}]" if f['relative_path'] else ''
                source_info = f" [来源: {f.get('source_folder', '')}]" if f.get('source_folder') else ''
                result += f"  - {f['filename']} ({f['param_name']}){path_info}{source_info}\n"
            result += '-' * 60 + '\n'
        return result

    def on_export_textures(self):
        """点击"导出贴图"按钮：使用 sbsrender 批量渲染贴图到输出目录。"""
        sd_dir = self.sd_dir_input.text().strip()
        sbsar_file = self.sbsar_input.text().strip()
        output_folder = self.output_folder_input.text().strip()

        if not sd_dir:
            self.log('错误: 请选择SD安装目录')
            return
        sbsrender_exe = os.path.join(sd_dir, 'sbsrender.exe')
        if not os.path.exists(sbsrender_exe):
            self.log(f'错误: sbsrender.exe 不存在: {sbsrender_exe}')
            return
        if not sbsar_file:
            self.log('错误: 请选择SBSAR文件')
            return
        if not output_folder:
            self.log('错误: 请选择输出目录')
            return
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            self.log(f'创建输出目录: {output_folder}')
        if not self.matched_files:
            self.log('错误: 没有可导出的贴图文件')
            return

        self.log('开始使用 sbsrender 渲染贴图...')
        grouped = self._group_matched_by_base()
        success_count = 0
        export_results = []

        for base_name, params in grouped.items():
            self.log(f'处理: {base_name}')
            ref_image = self._find_ref_image(params)
            width_exp, height_exp = self._calc_output_size(ref_image)

            cmd = [
                sbsrender_exe, 'render',
                '--input', sbsar_file,
                '--output-path', output_folder,
                '--output-name', f'{base_name}_{{outputNodeName}}',
            ]
            for param_name, file_info in params.items():
                cmd.extend(['--set-entry', f'{param_name}@{file_info["full_path"]}'])
            for cb_name, cb in self.checkbox_widgets.items():
                cmd.extend(['--set-value', f'{cb_name}@{1 if cb.isChecked() else 0}'])
            cmd.extend(['--set-value', f'$outputsize@{width_exp},{height_exp}'])
            cmd.extend(['--output-format', 'tga'])

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
                if result.stderr:
                    self.log(f'  警告: {result.stderr.strip()}')
                if result.returncode == 0:
                    success_count += 1
                    output_path = f'{output_folder}/{base_name}_*.tga'
                    export_results.append({'base_name': base_name, 'output_path': output_path, 'status': '✓ 成功'})
                    self.log('  ✓ 渲染成功')
                else:
                    export_results.append({'base_name': base_name, 'output_path': '', 'status': '✗ 失败'})
                    self.log(f'  ✗ 渲染失败: {result.stderr}')
            except Exception as e:
                export_results.append({'base_name': base_name, 'output_path': '', 'status': f'✗ {e}'})
                self.log(f'  ✗ 执行失败: {e}')

        total = len(grouped)
        self.log(f'渲染完成，成功 {success_count} 个，失败 {total - success_count} 个')

        export_text = '\n导出结果:\n'
        export_text += '=' * 60 + '\n'
        for r in export_results:
            export_text += f"基础名称: {r['base_name']}  {r['status']}\n"
            if r['output_path']:
                export_text += f"  输出路径: {r['output_path']}\n"
            export_text += '-' * 60 + '\n'
        self.result_text.append(export_text)

        reply = QMessageBox.question(
            self,
            '导出完成',
            f'渲染完成，成功 {success_count} 个，失败 {total - success_count} 个。\n是否打开输出目录？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply == QMessageBox.Yes:
            try:
                output_folder = self.output_folder_input.text().strip()
                if os.path.isdir(output_folder):
                    os.startfile(output_folder)
                else:
                    QMessageBox.warning(self, '打开失败', f'输出目录不存在: {output_folder}')
            except Exception as e:
                QMessageBox.warning(self, '打开失败', f'无法打开输出目录: {e}')

    def _group_matched_by_base(self):
        """将匹配的文件按 base_name 分组，每组包含各参数对应的文件信息。

        返回:
            dict: {base_name: {param_name: file_info}}。
        """
        grouped = {}
        for f in self.matched_files:
            grouped.setdefault(f['base_name'], {})[f['param_name']] = f
        return grouped

    def _find_ref_image(self, params):
        """从参数文件列表中查找第一个图片文件作为参考。

        参数:
            params: {param_name: file_info} 字典。

        返回:
            str 或 None: 参考图片的完整路径。
        """
        for param_name, file_info in params.items():
            if file_info['filename'].lower().endswith(('.tga', '.png', '.jpg')):
                return file_info['full_path']
        return None

    def _calc_output_size(self, ref_image_path):
        """根据参考图片尺寸计算输出尺寸的 2 的幂指数。

        参数:
            ref_image_path: 参考图片的完整路径。

        返回:
            tuple: (width_exponent, height_exponent)，范围 8-11。
        """
        width_exp = height_exp = 11
        if ref_image_path and os.path.exists(ref_image_path):
            dimensions = get_image_dimensions(ref_image_path)
            if dimensions:
                src_width, src_height = dimensions
                width_exp = get_power_exponent(src_width)
                height_exp = get_power_exponent(src_height)
                output_width = 2 ** width_exp
                output_height = 2 ** height_exp
                self.log(f'  输入尺寸: {src_width}x{src_height}, 输出尺寸: {output_width}x{output_height}')
            else:
                self.log(f'  无法读取输入尺寸，使用默认指数: {width_exp},{height_exp}')
        else:
            self.log(f'  使用默认输出尺寸指数: {width_exp},{height_exp}')
        return width_exp, height_exp

    def on_error(self, error_msg):
        """工作线程错误回调：记录错误日志并恢复按钮状态。

        参数:
            error_msg: 错误信息字符串。
        """
        self.log(f'错误: {error_msg}')
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_clear(self):
        """清空所有输入框、列表和结果，恢复初始状态。"""
        self.sd_dir_input.clear()
        self.sbsar_input.clear()
        self.input_folder_list.clear()
        self.output_folder_input.clear()
        self.log_text.clear()
        self.result_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.image_params = []
        self.matched_files = []
        self._populate_checkboxes([])
        self.find_textures_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.log('已清空所有内容')