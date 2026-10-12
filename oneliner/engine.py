"""OneLiner 核心规则引擎 — 从 Maya C++ 移植到 Blender Python

规则解析、对象收集、重命名执行等全部逻辑。
"""
import fnmatch
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import bpy


# ---------------------------------------------------------------------------
# 注册 / 注销 — 用于持久化偏好设置
# ---------------------------------------------------------------------------

def register():
    """注册 addon 级别的偏好属性。"""
    pass


def unregister():
    """注销 addon 级别的偏好属性。"""
    pass


# ---------------------------------------------------------------------------
# 偏好设置键名（存储在场景中，跟随 .blend 文件）
# ---------------------------------------------------------------------------

_PREVIEW_ENABLED_KEY = "oneLiner_preview_enabled"
_AUTO_CLOSE_KEY = "oneLiner_auto_close"
_WILDCARD_INCLUDE_CHILDREN_KEY = "oneLiner_wildcard_include_children"
_INPUT_HISTORY_KEY = "oneLiner_input_history"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class ScopeMode:
    SELECTED = "SELECTED"
    HIERARCHY = "HIERARCHY"
    ALL = "ALL"


@dataclass
class RenameTarget:
    """单个重命名目标。"""
    obj: bpy.types.Object = None
    path: str = ""              # 完整层级路径，如 "root|child|leaf"
    current_name: str = ""      # 短名称
    is_hierarchy: bool = False   # 是否属于 DAG 层级对象


@dataclass
class RenameOperation:
    """单次重命名操作。"""
    obj: bpy.types.Object = None
    old_name: str = ""
    new_name: str = ""
    is_hierarchy: bool = False


@dataclass
class PreviewItem:
    """预览列表中的一项。"""
    display_text: str = ""
    raw_text: str = ""
    name: str = ""
    type_name: str = ""
    path: str = ""
    parent_path: str = ""
    is_hierarchy: bool = False


@dataclass
class PreviewResult:
    """预览结果。"""
    items: List[str] = field(default_factory=list)
    raw_items: List[str] = field(default_factory=list)
    preview_items: List[PreviewItem] = field(default_factory=list)
    selection_only: bool = False


@dataclass
class ExecutePlan:
    """重命名执行计划。"""
    selection_targets: List[RenameTarget] = field(default_factory=list)
    rename_operations: List[RenameOperation] = field(default_factory=list)
    selection_only: bool = False
    noop: bool = False


@dataclass
class ParsedRule:
    """解析后的规则。"""
    original_rule: str = ""
    raw_rule: str = ""
    clean_rule: str = ""
    scope_mode: str = ScopeMode.SELECTED
    wildcard_pattern: str = ""
    type_filters: List[str] = field(default_factory=list)
    wildcard_selection: bool = False
    flags_mode: bool = False
    include_hierarchy: bool = False
    include_children: bool = False    # Blender 中等价于 Maya 的 includeShapes
    selection_only: bool = False


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _normalize_rule(text: str) -> str:
    """全角符号 → 半角符号转换。"""
    replacements = {
        '\uff01': '!', '\uff1f': '?', '\uff03': '#', '\uff20': '@',
        '\uff0a': '*', '\uff1e': '>', '\uff0f': '/', '\uff0c': ',',
        '\u3000': ' ',
    }
    for full, half in replacements.items():
        text = text.replace(full, half)
    return text


def _short_name(name: str) -> str:
    """从完整路径中取最后一段名称。"""
    idx = name.rfind('|')
    return name[idx + 1:] if idx >= 0 else name


def _path_is_ancestor(parent_path: str, child_path: str) -> bool:
    if not parent_path or not child_path or parent_path == child_path:
        return False
    return child_path.startswith(parent_path + '|')


def _dag_depth(path: str) -> int:
    return path.count('|')


def _split_replacement_terms(text: str) -> List[str]:
    """按空格、英文逗号、中文逗号切分。"""
    return re.split(r'[\s,，]+', text.strip())


def _is_numeric_trim_rule(rule: str) -> bool:
    return bool(re.match(r'^--?\d+$', rule))


def _is_flags_rule(rule: str) -> bool:
    if not rule.startswith('-'):
        return False
    tokens = rule.split()
    if not tokens:
        return False
    return tokens[0] in ('-h', '-s', '-type')


# ---------------------------------------------------------------------------
# 字母编号
# ---------------------------------------------------------------------------

def _index_to_letters(index: int, lower: bool = False) -> str:
    """单 @ 模式：A, B, ..., Z, AA, AB, ..."""
    result = []
    value = max(0, index)
    base = ord('a') if lower else ord('A')
    while True:
        remainder = value % 26
        result.append(chr(base + remainder))
        value = value // 26 - 1
        if value < 0:
            break
    return ''.join(reversed(result))


def _letters_to_index(letters: str) -> int:
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch.upper()) - ord('A'))
    return max(0, value)


def _fixed_width_letters(index: int, pattern: str) -> str:
    """多 @ 模式：@@, @@@ 固定宽度。"""
    if not pattern:
        return _index_to_letters(index)
    result = list(pattern)
    value = max(0, index)
    for i in range(len(pattern) - 1, -1, -1):
        remainder = value % 26
        lower = pattern[i].islower()
        result[i] = chr((ord('a') if lower else ord('A')) + remainder)
        value //= 26
    return ''.join(result)


# ---------------------------------------------------------------------------
# 序列模式解析 (# 和 @)
# ---------------------------------------------------------------------------

def _apply_sequence_patterns(text: str, index: int) -> str:
    """处理 # 数字编号 和 @ 字母编号。"""
    result = []
    cursor = 0
    while cursor < len(text):
        ch = text[cursor]
        if ch == '#':
            marker_end = cursor
            while marker_end < len(text) and text[marker_end] == '#':
                marker_end += 1
            start_value = 1
            consume_end = marker_end
            if marker_end < len(text) and text[marker_end] in ('/', '\\'):
                digit_end = marker_end + 1
                while digit_end < len(text) and text[digit_end].isdigit():
                    digit_end += 1
                if digit_end > marker_end + 1:
                    start_value = int(text[marker_end + 1:digit_end])
                    consume_end = digit_end
                else:
                    consume_end = marker_end + 1
            padding = marker_end - cursor
            number = index + start_value
            result.append(f"{number:0{padding}d}")
            cursor = consume_end
            continue

        if ch == '@':
            marker_end = cursor
            while marker_end < len(text) and text[marker_end] == '@':
                marker_end += 1
            marker_count = marker_end - cursor
            start_pattern = 'A' * marker_count
            consume_end = marker_end
            if marker_end < len(text) and text[marker_end] in ('/', '\\'):
                pattern_start = marker_end + 1
                pattern_end = pattern_start + marker_count
                valid = pattern_end <= len(text)
                if valid:
                    for i in range(pattern_start, pattern_end):
                        if not text[i].isalpha():
                            valid = False
                            break
                if valid:
                    start_pattern = text[pattern_start:pattern_end]
                    consume_end = pattern_end
                else:
                    consume_end = marker_end + 1

            if marker_count == 1:
                start_idx = max(0, ord(start_pattern[0].upper()) - ord('A'))
                lower = start_pattern[0].islower()
                result.append(_index_to_letters(start_idx + index, lower))
            else:
                start_idx = _letters_to_index(start_pattern)
                result.append(_fixed_width_letters(start_idx + index, start_pattern))
            cursor = consume_end
            continue

        result.append(ch)
        cursor += 1
    return ''.join(result)


# ---------------------------------------------------------------------------
# 替换规则
# ---------------------------------------------------------------------------

def _replacement_pairs(rule: str, index: int) -> List[Tuple[str, str]]:
    """解析 old>new 替换对。"""
    normalized = _normalize_rule(rule).strip()
    if '>' not in normalized:
        return []

    tokens = _split_replacement_terms(normalized)
    all_pairs = all('>' in t for t in tokens) if tokens else False

    if all_pairs:
        pairs = []
        for token in tokens:
            si = token.index('>')
            old = token[:si].strip()
            new = _apply_sequence_patterns(token[si + 1:].strip(), index)
            if old:
                pairs.append((old, new))
        return pairs

    si = normalized.index('>')
    old_words = _split_replacement_terms(normalized[:si])
    new_words = _split_replacement_terms(normalized[si + 1:])
    pairs = []
    for ow, nw in zip(old_words, new_words):
        ow = ow.strip()
        nw = _apply_sequence_patterns(nw.strip(), index)
        if ow:
            pairs.append((ow, nw))
    return pairs


# ---------------------------------------------------------------------------
# 规则解析
# ---------------------------------------------------------------------------

def parse_rule(rule: str, forced_mode: str = ScopeMode.SELECTED,
               use_forced_mode: bool = False) -> ParsedRule:
    parsed = ParsedRule()
    parsed.original_rule = rule
    parsed.raw_rule = _normalize_rule(rule).strip()
    parsed.clean_rule = parsed.raw_rule

    if _is_flags_rule(parsed.raw_rule) and not _is_numeric_trim_rule(parsed.raw_rule):
        parsed.flags_mode = True
        parsed.clean_rule = ''
        tokens = parsed.raw_rule.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == '-h':
                parsed.include_hierarchy = True
            elif token == '-s':
                parsed.include_children = True
            elif token == '-type':
                i += 1
                while i < len(tokens) and not tokens[i].startswith('-'):
                    parsed.type_filters.append(tokens[i])
                    i += 1
                continue
            i += 1
    elif '*' in parsed.raw_rule or '?' in parsed.raw_rule:
        parsed.wildcard_selection = True
        parsed.selection_only = True
        # 检查通配符前是否有有效搜索文本
        candidate = parsed.raw_rule.replace('*', '').replace('?', '')
        parsed.wildcard_pattern = parsed.raw_rule if candidate.strip() else ''
        parsed.clean_rule = ''
    else:
        parsed.clean_rule = parsed.clean_rule.strip()

    if use_forced_mode:
        parsed.scope_mode = forced_mode
    return parsed


# ---------------------------------------------------------------------------
# 对象收集
# ---------------------------------------------------------------------------

def _get_object_path(obj: bpy.types.Object) -> str:
    """构建层级路径: root|child|leaf。"""
    parts = []
    current = obj
    while current:
        parts.append(current.name)
        current = current.parent
    return '|'.join(reversed(parts))


def _collect_selection() -> List[RenameTarget]:
    targets = []
    seen = set()
    for obj in bpy.context.selected_objects:
        path = _get_object_path(obj)
        if path in seen:
            continue
        seen.add(path)
        targets.append(RenameTarget(
            obj=obj,
            path=path,
            current_name=obj.name,
            is_hierarchy=True,
        ))
    return targets


def _collect_hierarchy(include_children: bool = False) -> List[RenameTarget]:
    """收集选中对象及其所有子级。"""
    selection = _collect_selection()
    # 过滤掉是其他选中项子级的对象（保留根节点）
    roots = []
    for candidate in selection:
        is_child = False
        for other in selection:
            if candidate.path == other.path:
                continue
            if _path_is_ancestor(other.path, candidate.path):
                is_child = True
                break
        if not is_child:
            roots.append(candidate)

    targets = []
    seen = set()

    def _add_descendants(obj: bpy.types.Object):
        path = _get_object_path(obj)
        if path not in seen:
            seen.add(path)
            targets.append(RenameTarget(
                obj=obj,
                path=path,
                current_name=obj.name,
                is_hierarchy=True,
            ))
        for child in obj.children:
            _add_descendants(child)

    for root in roots:
        _add_descendants(root.obj)

    return targets


def _collect_all() -> List[RenameTarget]:
    targets = []
    seen = set()
    for obj in bpy.data.objects:
        path = _get_object_path(obj)
        if path not in seen:
            seen.add(path)
            targets.append(RenameTarget(
                obj=obj,
                path=path,
                current_name=obj.name,
                is_hierarchy=True,
            ))
    return targets


def _collect_wildcard(pattern: str) -> List[RenameTarget]:
    """通配符匹配收集对象。"""
    if not pattern.strip():
        return []

    targets = []
    seen = set()
    for obj in bpy.data.objects:
        if fnmatch.fnmatch(obj.name, pattern):
            path = _get_object_path(obj)
            if path not in seen:
                seen.add(path)
                targets.append(RenameTarget(
                    obj=obj,
                    path=path,
                    current_name=obj.name,
                    is_hierarchy=True,
                ))

    return targets


def _filter_by_type(targets: List[RenameTarget], type_filters: List[str]) -> List[RenameTarget]:
    if not type_filters:
        return targets
    allowed = {t.upper() for t in type_filters}
    return [t for t in targets if t.obj.type.upper() in allowed]


def _collect_targets_for_parsed(parsed: ParsedRule) -> List[RenameTarget]:
    if parsed.include_hierarchy:
        targets = _collect_hierarchy(parsed.include_children)
    elif parsed.scope_mode == ScopeMode.HIERARCHY:
        targets = _collect_hierarchy()
    elif parsed.scope_mode == ScopeMode.ALL:
        targets = _collect_all()
    else:
        targets = _collect_selection()

    # 如果按类型过滤没找到，回退到全局搜索
    if not targets and not parsed.include_hierarchy and parsed.type_filters:
        targets = _collect_all()

    if parsed.type_filters:
        targets = _filter_by_type(targets, parsed.type_filters)

    return targets


# ---------------------------------------------------------------------------
# 重名检查
# ---------------------------------------------------------------------------

def _name_exists(name: str) -> bool:
    return name in bpy.data.objects


def _name_match_count(name: str) -> int:
    """返回场景中匹配该名称的对象数量（Blender 中为 0 或 1）。"""
    return 1 if name in bpy.data.objects else 0


def _unique_name(name: str) -> str:
    """如果名称已存在，追加数字后缀。"""
    if not _name_exists(name):
        return name
    # 提取末尾数字
    base = name
    digit = 0
    while base and base[-1].isdigit():
        digit += int(base[-1])
        base = base[:-1]
    if _name_exists(base):
        counter = digit
        while _name_exists(base + str(counter)):
            counter += 1
        return base + str(counter + 1)
    return base + str(digit)


# ---------------------------------------------------------------------------
# 预览排序
# ---------------------------------------------------------------------------

def _sort_preview_entries(targets: List[RenameTarget], display_names: List[str],
                          raw_names: Optional[List[str]] = None):
    """按层级树结构排序预览条目。"""
    if len(targets) != len(display_names):
        return
    if raw_names is not None and len(raw_names) != len(display_names):
        return

    class Entry:
        __slots__ = ('target', 'display_name', 'raw_name')
        def __init__(self, t, d, r):
            self.target = t
            self.display_name = d
            self.raw_name = r

    entries = [Entry(targets[i], display_names[i],
                     raw_names[i] if raw_names else display_names[i])
               for i in range(len(targets))]

    # 构建父子关系
    parent_idx = [-1] * len(entries)
    children = [[] for _ in range(len(entries))]
    dag_roots = []
    non_dag = []

    for i, e in enumerate(entries):
        if not e.target.is_hierarchy:
            non_dag.append(i)
            continue
        nearest = -1
        nearest_depth = -1
        for j, other in enumerate(entries):
            if j == i or not other.target.is_hierarchy:
                continue
            if _path_is_ancestor(other.target.path, e.target.path):
                d = _dag_depth(other.target.path)
                if d > nearest_depth:
                    nearest_depth = d
                    nearest = j
        parent_idx[i] = nearest
        if nearest >= 0:
            children[nearest].append(i)
        else:
            dag_roots.append(i)

    # DFS 遍历
    ordered = []

    def _append_subtree(idx):
        ordered.append(entries[idx])
        for child_idx in children[idx]:
            _append_subtree(child_idx)

    for root_idx in dag_roots:
        _append_subtree(root_idx)
    for idx in non_dag:
        ordered.append(entries[idx])

    if len(ordered) != len(entries):
        return

    for i, e in enumerate(ordered):
        targets[i] = e.target
        display_names[i] = e.display_name
        if raw_names is not None:
            raw_names[i] = e.raw_name


def _preview_label_for_target(target: RenameTarget, display_name: str,
                               base_dag_depth: int) -> str:
    """层级缩进显示。"""
    if not target.is_hierarchy:
        return display_name
    relative_depth = max(0, _dag_depth(target.path) - base_dag_depth)
    if relative_depth <= 0:
        return display_name
    return '  ' * relative_depth + display_name


# ---------------------------------------------------------------------------
# 构建重命名结果
# ---------------------------------------------------------------------------

def _apply_rule_to_name(parsed: ParsedRule, index: int, current: str) -> str:
    """对单个名称应用规则，返回新名称。"""
    if '>' in parsed.clean_rule:
        next_name = current
        pairs = _replacement_pairs(parsed.clean_rule, index)
        if not pairs:
            return current
        for old, new in pairs:
            next_name = next_name.replace(old, new)
        return next_name
    elif parsed.clean_rule.startswith('-'):
        rule = parsed.clean_rule
        if rule == '-' or rule == '--':
            return current
        try:
            n = int(rule[1:])
            if n >= 0:
                return current[:max(0, len(current) - n)]
            else:
                return current[:min(len(current), -n)]
        except ValueError:
            return current
    elif parsed.clean_rule.startswith('+'):
        if len(parsed.clean_rule) == 1:
            return current
        try:
            n = int(parsed.clean_rule[1:])
            return current[max(0, n):]
        except ValueError:
            return current
    else:
        next_name = _apply_sequence_patterns(parsed.clean_rule, index)
        return next_name.replace('!', current)


def _build_renamed_items(parsed: ParsedRule, targets: List[RenameTarget],
                         reverse_for_rename: bool = True,
                         starting_names: Optional[List[str]] = None) -> List[str]:
    """对目标列表应用规则，生成新名称列表。"""
    if parsed.clean_rule == '':
        base = starting_names if starting_names else [t.current_name for t in targets]
        return list(base)

    renamed = []
    for i, target in enumerate(targets):
        current = starting_names[i] if starting_names else target.current_name
        renamed.append(_apply_rule_to_name(parsed, i, current))

    # 处理 '/'
    base_check = starting_names if starting_names else [t.current_name for t in targets]
    renamed = [base_check[i] if r == '/' else r for i, r in enumerate(renamed)]

    # 重名处理：如果新名称与场景中已有对象冲突（且不是自身），则追加数字后缀
    original_names = [t.current_name for t in targets]
    for i in range(len(renamed)):
        r = renamed[i]
        if r != original_names[i] and _name_exists(r):
            renamed[i] = _unique_name(r)

    # 层级模式需要反转顺序（从叶子到根）
    needs_reverse = any('|' in t.path for t in targets)
    if not needs_reverse:
        needs_reverse = any('|' in n for n in renamed)

    if needs_reverse and reverse_for_rename:
        renamed.reverse()
        targets.reverse()

    return renamed


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def preview(rule: str, forced_mode: str = ScopeMode.SELECTED,
            use_forced_mode: bool = False) -> PreviewResult:
    """预览规则结果。"""
    parsed = parse_rule(rule, forced_mode, use_forced_mode)
    result = PreviewResult()
    result.selection_only = parsed.selection_only

    if parsed.selection_only:
        targets = _collect_wildcard(parsed.wildcard_pattern)
        names = [t.current_name for t in targets]
        raw = list(names)
        _sort_preview_entries(targets, names, raw)
        result.items = names
        result.raw_items = raw
    else:
        targets = _collect_targets_for_parsed(parsed)
        renamed = _build_renamed_items(parsed, targets, reverse_for_rename=False)
        raw = list(renamed)
        _sort_preview_entries(targets, renamed, raw)
        result.items = renamed
        result.raw_items = raw

    _fill_preview_items(result, targets)
    return result


def preview_chain(chain_rules: List[str], current_rule: str,
                  forced_mode: str = ScopeMode.SELECTED,
                  use_forced_mode: bool = False) -> PreviewResult:
    """链式预览：先应用链中所有规则，再应用当前输入规则。"""
    parsed = parse_rule(current_rule, forced_mode, use_forced_mode)
    result = PreviewResult()
    result.selection_only = parsed.selection_only

    if parsed.selection_only:
        targets = _collect_wildcard(parsed.wildcard_pattern)
        names = [t.current_name for t in targets]
        raw = list(names)
        _sort_preview_entries(targets, names, raw)
        result.items = names
        result.raw_items = raw
        _fill_preview_items(result, targets)
        return result

    targets = _collect_targets_for_parsed(parsed)
    if not targets:
        return result

    # 从原始名称开始，依次应用链中每条规则
    virtual_names = [t.current_name for t in targets]
    for chain_rule in chain_rules:
        chain_parsed = parse_rule(chain_rule, forced_mode, use_forced_mode)
        if chain_parsed.clean_rule:
            virtual_names = _build_renamed_items(
                chain_parsed, targets, reverse_for_rename=False,
                starting_names=virtual_names,
            )

    # 应用当前输入规则
    if parsed.clean_rule:
        renamed = _build_renamed_items(
            parsed, targets, reverse_for_rename=False,
            starting_names=virtual_names,
        )
    else:
        renamed = list(virtual_names)

    raw = list(renamed)
    _sort_preview_entries(targets, renamed, raw)
    result.items = renamed
    result.raw_items = raw
    _fill_preview_items(result, targets)
    return result


def _fill_preview_items(result: PreviewResult, targets: List[RenameTarget]):
    """填充 PreviewResult 的 preview_items 列表。"""
    base_depth = min((_dag_depth(t.path) for t in targets if t.is_hierarchy), default=0)
    result.preview_items = []
    for i, name in enumerate(result.items):
        t = targets[i] if i < len(targets) else targets[-1]
        parent_path = t.path.rsplit('|', 1)[0] if '|' in t.path else ''
        result.preview_items.append(PreviewItem(
            display_text=_preview_label_for_target(t, name, base_depth),
            raw_text=result.raw_items[i] if i < len(result.raw_items) else name,
            name=name,
            type_name=t.obj.type if t.obj else '',
            path=t.path,
            parent_path=parent_path,
            is_hierarchy=t.is_hierarchy,
        ))


def build_execute_plan(rule: str, forced_mode: str = ScopeMode.SELECTED,
                       use_forced_mode: bool = False) -> ExecutePlan:
    """构建执行计划。"""
    parsed = parse_rule(rule, forced_mode, use_forced_mode)
    plan = ExecutePlan()

    if parsed.raw_rule == '' or parsed.raw_rule == '/':
        plan.noop = True
        return plan

    if parsed.selection_only:
        targets = _collect_wildcard(parsed.wildcard_pattern)
        plan.selection_only = True
        plan.selection_targets = targets
        return plan

    if parsed.flags_mode and not parsed.clean_rule:
        targets = _collect_targets_for_parsed(parsed)
        plan.selection_only = True
        plan.selection_targets = targets
        return plan

    targets = _collect_targets_for_parsed(parsed)
    renamed = _build_renamed_items(parsed, targets, reverse_for_rename=True)

    if len(targets) != len(renamed):
        return plan

    for i, target in enumerate(targets):
        new_name = renamed[i].strip()
        if new_name and target.current_name != new_name:
            plan.rename_operations.append(RenameOperation(
                obj=target.obj,
                old_name=target.current_name,
                new_name=new_name,
                is_hierarchy=target.is_hierarchy,
            ))

    return plan


def execute(rule: str, forced_mode: str = ScopeMode.SELECTED,
            use_forced_mode: bool = False) -> bool:
    """执行重命名。"""
    plan = build_execute_plan(rule, forced_mode, use_forced_mode)
    if plan.noop:
        return True

    if plan.selection_only:
        # 通配符模式：选中匹配对象
        bpy.ops.object.select_all(action='DESELECT')
        for t in plan.selection_targets:
            t.obj.select_set(True)
        if plan.selection_targets:
            bpy.context.view_layer.objects.active = plan.selection_targets[0].obj
        return True

    if not plan.rename_operations:
        return True

    for op in plan.rename_operations:
        try:
            op.obj.name = op.new_name
        except Exception:
            return False
    return True


def execute_chain(chain_rules: List[str], current_rule: str,
                  forced_mode: str = ScopeMode.SELECTED,
                  use_forced_mode: bool = False) -> bool:
    """链式执行：依次应用链中所有规则和当前规则，最终重命名。"""
    if not chain_rules and not current_rule.strip():
        return True

    parsed = parse_rule(current_rule, forced_mode, use_forced_mode)

    if parsed.selection_only:
        return execute(current_rule, forced_mode, use_forced_mode)

    targets = _collect_targets_for_parsed(parsed)
    if not targets:
        return True

    # 从原始名称开始，依次应用链中每条规则
    virtual_names = [t.current_name for t in targets]
    for chain_rule in chain_rules:
        chain_parsed = parse_rule(chain_rule, forced_mode, use_forced_mode)
        if chain_parsed.clean_rule:
            virtual_names = _build_renamed_items(
                chain_parsed, targets, reverse_for_rename=False,
                starting_names=virtual_names,
            )

    # 应用当前规则
    if parsed.clean_rule:
        final_names = _build_renamed_items(
            parsed, targets, reverse_for_rename=True,
            starting_names=virtual_names,
        )
    else:
        final_names = list(virtual_names)

    if len(final_names) != len(targets):
        return False

    for i, target in enumerate(targets):
        new_name = final_names[i].strip()
        if new_name and target.current_name != new_name:
            try:
                target.obj.name = new_name
            except Exception:
                return False
    return True


def clear_pasted_prefix() -> bool:
    """清除 pasted__ 前缀（兼容 Maya 版功能）。"""
    prefix = 'pasted__'
    for obj in bpy.data.objects:
        if obj.name.startswith(prefix):
            try:
                obj.name = obj.name[len(prefix):]
            except Exception:
                return False
    return True


def select_targets(targets: List[RenameTarget]) -> bool:
    """选中给定目标。"""
    bpy.ops.object.select_all(action='DESELECT')
    for t in targets:
        if t.obj:
            t.obj.select_set(True)
    if targets:
        bpy.context.view_layer.objects.active = targets[0].obj
    return True


# ---------------------------------------------------------------------------
# 输入历史管理
# ---------------------------------------------------------------------------

_history: List[str] = []
_history_limit = 50


def add_history(text: str):
    global _history
    if not text.strip():
        return
    if text in _history:
        _history.remove(text)
    _history.append(text)
    while len(_history) > _history_limit:
        _history.pop(0)


def get_history() -> List[str]:
    return list(_history)