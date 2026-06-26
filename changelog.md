# Changelog

## 2026-06-26

### 新增：布尔参数复选框支持

- **`utils/sbsar_utils.py`**：新增 `is_checkbox_param()` 函数，用于判断参数是否应显示为复选框（名称以 `is_` 开头且类型为 `INTEGER1`）
- **`UI/main_window.py`**：
  - 新增"布尔参数"分组框，动态创建 `QCheckBox` 控件
  - 获取参数时自动识别 `is_` + `INTEGER1` 参数并生成复选框，根据默认值预选
  - 导出贴图时，复选框值通过 `--set-value {name}@{0|1}` 传入 `sbsrender` 命令
  - 清空操作时同步清除所有复选框