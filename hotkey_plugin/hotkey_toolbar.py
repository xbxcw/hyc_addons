"""
Simple Toolbar for Hotkey Plugin
"""

from PySide6 import QtWidgets
from PySide6.QtGui import QAction


class HotkeyToolbar(QtWidgets.QToolBar):
    """简单的toolbar类，用于承载action"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions = {}
    
    def add_action(self, name: str, action: QAction):
        """添加action到toolbar"""
        self.addAction(action)
        self._actions[name] = action
