import sys
import os
import json
import math
import subprocess

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'hyc_sd', 'utils'))

from PySide6.QtWidgets import (
    QApplication,
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
    QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal

try:
    from SbsarToos import get_sbsar_exposed_params
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class WorkerThread(QThread):
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, sbsrender_exe, sbsar_file):
        super().__init__()
        self.sbsrender_exe = sbsrender_exe
        self.sbsar_file = sbsar_file

    def run(self):
        try:
            self.progress.emit(50)
            params = get_sbsar_exposed_params(self.sbsrender_exe, self.sbsar_file)
            self.progress.emit(100)
            self.finished.emit(params)
        except Exception as e:
            self.error.emit(str(e))


def get_image_dimensions(image_path):
    from PIL import Image
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        print(f"读取图片尺寸失败: {e}")
        return None


def get_power_exponent(pixel_size):
    if pixel_size <= 0:
        return 8
    exponent = round(math.log2(pixel_size))
    return max(8, min(exponent, 11))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_params = []  # 存储IMAGE类型的参数名称
        self.matched_files = []  # 存储匹配到的贴图文件
        self.config_file = os.path.join(os.path.dirname(__file__), 'sbsar_config.json')
        self.output_format = 'tga'
        self.init_ui()
        self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'sd_dir' in config:
                        self.sd_dir_input.setText(config['sd_dir'])
                    if 'sbsar_file' in config:
                        self.sbsar_input.setText(config['sbsar_file'])
                    if 'input_folder' in config:
                        self.input_folder_input.setText(config['input_folder'])
                    if 'output_folder' in config:
                        self.output_folder_input.setText(config['output_folder'])
                self.log(f'配置已加载: {self.config_file}')
            except Exception as e:
                self.log(f'加载配置失败: {e}')
    
    def save_config(self):
        config = {
            'sd_dir': self.sd_dir_input.text().strip(),
            'sbsar_file': self.sbsar_input.text().strip(),
            'input_folder': self.input_folder_input.text().strip(),
            'output_folder': self.output_folder_input.text().strip()
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.log(f'配置已保存: {self.config_file}')
        except Exception as e:
            self.log(f'保存配置失败: {e}')

    def init_ui(self):
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

        if not IMPORT_SUCCESS:
            error_label = QLabel(f'<span style="color: red;">模块导入失败: {IMPORT_ERROR}</span>')
            error_label.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(error_label)
            return

        sd_group = QGroupBox('SD安装目录')
        sd_layout = QHBoxLayout()
        sd_group.setLayout(sd_layout)
        sd_label = QLabel('SD目录:')
        self.sd_dir_input = QLineEdit()
        self.sd_dir_input.setPlaceholderText('例如: C:/Program Files/Adobe/Adobe Substance 3D Designer')
        sd_browse_btn = QPushButton('浏览')
        sd_browse_btn.clicked.connect(self.browse_sd_dir)
        sd_layout.addWidget(sd_label)
        sd_layout.addWidget(self.sd_dir_input)
        sd_layout.addWidget(sd_browse_btn)
        main_layout.addWidget(sd_group)

        sbsar_group = QGroupBox('SBSAR文件')
        sbsar_layout = QHBoxLayout()
        sbsar_group.setLayout(sbsar_layout)
        sbsar_label = QLabel('文件:')
        self.sbsar_input = QLineEdit()
        self.sbsar_input.setPlaceholderText('例如: C:/materials/MyMaterial.sbsar')
        sbsar_browse_btn = QPushButton('浏览')
        sbsar_browse_btn.clicked.connect(self.browse_sbsar_file)
        sbsar_layout.addWidget(sbsar_label)
        sbsar_layout.addWidget(self.sbsar_input)
        sbsar_layout.addWidget(sbsar_browse_btn)
        main_layout.addWidget(sbsar_group)

        input_group = QGroupBox('输入目录')
        input_layout = QHBoxLayout()
        input_group.setLayout(input_layout)
        input_label = QLabel('路径:')
        self.input_folder_input = QLineEdit()
        self.input_folder_input.setPlaceholderText('例如: C:/textures/input')
        input_browse_btn = QPushButton('浏览')
        input_browse_btn.clicked.connect(self.browse_input_folder)
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_folder_input)
        input_layout.addWidget(input_browse_btn)
        main_layout.addWidget(input_group)

        output_group = QGroupBox('输出目录')
        output_layout = QHBoxLayout()
        output_group.setLayout(output_layout)
        output_label = QLabel('路径:')
        self.output_folder_input = QLineEdit()
        self.output_folder_input.setPlaceholderText('例如: C:/textures/output')
        output_browse_btn = QPushButton('浏览')
        output_browse_btn.clicked.connect(self.browse_output_folder)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_folder_input)
        output_layout.addWidget(output_browse_btn)
        main_layout.addWidget(output_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        button_layout = QHBoxLayout()
        
        self.run_btn = QPushButton('获取参数')
        self.run_btn.clicked.connect(self.on_run)
        button_layout.addWidget(self.run_btn)

        self.find_textures_btn = QPushButton('查找贴图')
        self.find_textures_btn.clicked.connect(self.on_find_textures)
        self.find_textures_btn.setEnabled(False)
        button_layout.addWidget(self.find_textures_btn)

        self.export_btn = QPushButton('导出贴图')
        self.export_btn.clicked.connect(self.on_export_textures)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton('清空')
        self.clear_btn.clicked.connect(self.on_clear)
        button_layout.addWidget(self.clear_btn)

        main_layout.addLayout(button_layout)

        log_group = QGroupBox('日志输出')
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet('background-color: #f5f5f5;')
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)

        result_group = QGroupBox('参数结果')
        result_layout = QVBoxLayout()
        result_group.setLayout(result_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        main_layout.addWidget(result_group)

        self.log('初始化完成，准备获取SBSAR参数...')

    def browse_sd_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择SD安装目录')
        if dir_path:
            self.sd_dir_input.setText(dir_path)
            sbsrender_path = os.path.join(dir_path, 'sbsrender.exe')
            self.log(f'SD目录已选择: {dir_path}')
            if os.path.exists(sbsrender_path):
                self.log(f'sbsrender.exe 路径: {sbsrender_path}')
            else:
                self.log(f'警告: sbsrender.exe 不存在于该目录')
            self.save_config()

    def browse_sbsar_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, '选择SBSAR文件', '', 'SBSAR Files (*.sbsar)'
        )
        if file_path:
            self.sbsar_input.setText(file_path)
            self.log(f'SBSAR文件已选择: {file_path}')
            self.save_config()

    def browse_input_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择输入目录')
        if dir_path:
            self.input_folder_input.setText(dir_path)
            self.log(f'输入目录已选择: {dir_path}')
            self.save_config()

    def browse_output_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if dir_path:
            self.output_folder_input.setText(dir_path)
            self.log(f'输出目录已选择: {dir_path}')
            self.save_config()

    def log(self, message):
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f'[{timestamp}] {message}')

    def on_run(self):
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
        self.progress_bar.setValue(value)

    def on_finished(self, params):
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
            
            result = '参数列表:\n'
            result += '=' * 50 + '\n'
            for i, param in enumerate(params, 1):
                param_type = param.get('type', '')
                result += f"{i}. 名称: {param.get('name', '')}\n"
                result += f"   类型: {param_type}"
                if param_type == 'IMAGE':
                    result += ' (贴图参数)'
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
        input_folder = self.input_folder_input.text().strip()
        
        if not input_folder:
            self.log('错误: 请选择输入目录')
            return
        
        if not os.path.exists(input_folder):
            self.log(f'错误: 输入目录不存在: {input_folder}')
            return
        
        if not self.image_params:
            self.log('错误: 未找到IMAGE类型参数，请先获取参数')
            return
        
        self.log(f'开始在 {input_folder} 中查找贴图...')
        self.log(f'搜索后缀: {", ".join(self.image_params)}')
        
        self.matched_files = []
        
        for root, dirs, files in os.walk(input_folder):
            for filename in files:
                for param_name in self.image_params:
                    if filename.endswith(f'_{param_name}.tga') or filename.endswith(f'_{param_name}.png') or filename.endswith(f'_{param_name}.jpg'):
                        base_name = filename.rsplit(f'_{param_name}', 1)[0]
                        full_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(root, input_folder)
                        self.matched_files.append({
                            'base_name': base_name,
                            'param_name': param_name,
                            'filename': filename,
                            'full_path': full_path,
                            'relative_path': relative_path if relative_path != '.' else ''
                        })
        
        if self.matched_files:
            self.log(f'找到 {len(self.matched_files)} 个匹配的贴图文件')
            
            result = '匹配的贴图文件:\n'
            result += '=' * 60 + '\n'
            
            grouped_files = {}
            for f in self.matched_files:
                if f['base_name'] not in grouped_files:
                    grouped_files[f['base_name']] = []
                grouped_files[f['base_name']].append(f)
            
            for base_name, files in grouped_files.items():
                result += f"基础名称: {base_name}\n"
                for f in files:
                    if f['relative_path']:
                        result += f"  - {f['filename']} ({f['param_name']}) [路径: {f['relative_path']}]\n"
                    else:
                        result += f"  - {f['filename']} ({f['param_name']})\n"
                result += '-' * 60 + '\n'
            
            self.result_text.setPlainText(result)
            self.export_btn.setEnabled(True)
        else:
            self.log('未找到匹配的贴图文件')
            self.result_text.setPlainText('未找到匹配的贴图文件')
            self.export_btn.setEnabled(False)
    
    def on_export_textures(self):
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
        
        self.log(f'开始使用 sbsrender 渲染贴图...')
        
        grouped_files = {}
        for f in self.matched_files:
            if f['base_name'] not in grouped_files:
                grouped_files[f['base_name']] = {}
            grouped_files[f['base_name']][f['param_name']] = f
        
        success_count = 0
        
        for base_name, params in grouped_files.items():
            self.log(f'处理: {base_name}')
            
            ref_image_path = None
            for param_name, file_info in params.items():
                if file_info['filename'].lower().endswith('.tga') or file_info['filename'].lower().endswith('.png') or file_info['filename'].lower().endswith('.jpg'):
                    ref_image_path = file_info['full_path']
                    break
            
            width_exp = 11
            height_exp = 11
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
            
            cmd = [
                sbsrender_exe,
                'render',
                '--input', sbsar_file,
                '--output-path', output_folder,
                '--output-name', f'{base_name}_{{outputNodeName}}'
            ]
            
            for param_name, file_info in params.items():
                cmd.extend(['--set-entry', f'{param_name}@{file_info["full_path"]}'])
            
            cmd.extend(['--set-value', f'$outputsize@{width_exp},{height_exp}'])
            cmd.extend(['--output-format', 'tga'])
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
                
                if result.stderr:
                    self.log(f'  警告: {result.stderr.strip()}')
                
                if result.returncode == 0:
                    success_count += 1
                    self.log(f'  ✓ 渲染成功')
                else:
                    self.log(f'  ✗ 渲染失败: {result.stderr}')
            except Exception as e:
                self.log(f'  ✗ 执行失败: {e}')
        
        self.log(f'渲染完成，成功 {success_count} 个，失败 {len(grouped_files) - success_count} 个')

    def on_error(self, error_msg):
        self.log(f'错误: {error_msg}')
        self.run_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_clear(self):
        self.sd_dir_input.clear()
        self.sbsar_input.clear()
        self.input_folder_input.clear()
        self.output_folder_input.clear()
        self.log_text.clear()
        self.result_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.image_params = []
        self.matched_files = []
        self.find_textures_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.log('已清空所有内容')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())