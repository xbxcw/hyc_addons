import bpy
import typing
import inspect
import pkgutil
import importlib
from pathlib import Path

# 模块导出的公共接口
__all__ = (
    "init",
    "register",
    "unregister",
)

# 获取当前Blender版本，用于后续兼容性判断
blender_version = bpy.app.version

# 全局变量：存储所有子模块，以及需要注册的类（按依赖顺序排列）
modules = None
ordered_classes = None


def init():
    """
    初始化函数：收集当前包下的所有子模块，并计算需要注册的类的顺序（拓扑排序）。
    通常由插件根目录的 __init__.py 在 register 之前调用。
    """
    global modules
    global ordered_classes

    # 获取当前文件所在目录下的所有子模块
    modules = get_all_submodules(Path(__file__).parent)
    # 计算需要注册的类的顺序（解决依赖关系）
    ordered_classes = get_ordered_classes_to_register(modules)
    # 打印顺序结果（调试用）
    print("="*50)
    for i in ordered_classes:
        print(i.__name__)
    print("*"*50)


def register():
    # 按顺序注册所有类，记录成功注册的类
    for cls in ordered_classes:
        try:
            bpy.utils.register_class(cls)
            if cls.__name__ == "HYC_Properties":
                bpy.types.Scene.hyc_props = bpy.props.PointerProperty(type=cls)
        except RuntimeError as e:
            # 如果注册失败，打印错误信息便于调试
            print(f"注册失败: {cls.__name__} - {e}")

    # 调用子模块register（原逻辑不变）
    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "register"):
            module.register()

def unregister():
    # 先删除自定义属性，避免依赖问题
    # if hasattr(bpy.types.Scene, "hyc_props"):
    #     del bpy.types.Scene.hyc_props
    
    # 逆序注销类，添加注册检查避免重复注销错误
    for cls in reversed(ordered_classes):
        # 检查类是否已注册（通过检查是否有 bl_rna 属性）
        if hasattr(cls, 'bl_rna'):
            try:
                bpy.utils.unregister_class(cls)
            except RuntimeError as e:
                print(f"注册失败: {cls.__name__} - {e}")
                # 如果注销失败（可能已经被注销），忽略错误
                pass

    # 调用子模块unregister（原逻辑不变）
    for module in modules:
        if module.__name__ == __name__:
            continue
        if hasattr(module, "unregister"):
            module.unregister()

# 模块发现相关函数
#################################################


def get_all_submodules(directory):
    """
    返回给定目录下所有子模块的列表。
    """
    return list(iter_submodules(directory, __package__))


def iter_submodules(path, package_name):
    """
    迭代器：遍历 path 目录下的所有子模块，逐个导入并返回。
    """
    for name in sorted(iter_submodule_names(path)):
        yield importlib.import_module("." + name, package_name)


def iter_submodule_names(path, root=""):
    """
    递归生成器：遍历 path 目录，返回所有模块的完整名称（相对于包）。
    root 用于嵌套包的前缀。
    """
    # 定义需要排除的文件夹名称（可根据需要修改）
    EXCLUDED_FOLDERS = {"tests", "dev", "exclude_me"}  # 例如排除 tests, dev 等

    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        if is_package:
            # 如果是包，先检查是否在排除列表中
            if module_name in EXCLUDED_FOLDERS:
                continue   # 跳过该文件夹及其所有子内容
            sub_path = path / module_name
            sub_root = root + module_name + "."
            yield from iter_submodule_names(sub_path, sub_root)
        else:
            # 普通模块，返回完整名称
            yield root + module_name

# 需要注册的类发现及依赖分析
#################################################


def get_ordered_classes_to_register(modules):
    """
    对 modules 中所有需要注册的类进行拓扑排序，返回排序后的列表。
    """
    return toposort(get_register_deps_dict(modules))


def get_register_deps_dict(modules):
    """
    构建依赖字典：键为需要注册的类，值为其依赖的其他类的集合。
    依赖关系通过类型注解或父面板ID（bl_parent_id）分析得到。
    """
    # 收集所有需要注册的类
    my_classes = set(iter_my_classes(modules))
    # 建立 bl_idname 到类的映射（仅对拥有 bl_idname 属性的类）
    my_classes_by_idname = {cls.bl_idname: cls for cls in my_classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        # 收集当前类的所有依赖项
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))
    return deps_dict


def iter_my_register_deps(cls, my_classes, my_classes_by_idname):
    """
    生成器：生成 cls 所依赖的其他注册类。
    依赖来源：1) 类型注解中的 Property 类型；2) 面板的 bl_parent_id。
    """
    yield from iter_my_deps_from_annotations(cls, my_classes)
    yield from iter_my_deps_from_parent_id(cls, my_classes_by_idname)


def iter_my_deps_from_annotations(cls, my_classes):
    """
    从类的类型注解中寻找依赖的类（例如 PointerProperty 或 CollectionProperty 的 type 参数）。
    """
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            if dependency in my_classes:
                yield dependency


def get_dependency_from_annotation(value):
    """
    根据注解值提取依赖的类类型。
    兼容 Blender 2.93 之前和之后的 API 差异。
    """
    if blender_version >= (2, 93):
        # 2.93 及之后：bpy.props._PropertyDeferred 对象
        if isinstance(value, bpy.props._PropertyDeferred):
            return value.keywords.get("type")
    else:
        # 旧版本：注解是元组 (prop_function, {"type": SomeClass})
        if isinstance(value, tuple) and len(value) == 2:
            if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
                return value[1]["type"]
    return None


def iter_my_deps_from_parent_id(cls, my_classes_by_idname):
    """
    对于面板类，如果指定了 bl_parent_id，则依赖对应的父面板类。
    """
    if issubclass(cls, bpy.types.Panel):
        parent_idname = getattr(cls, "bl_parent_id", None)
        if parent_idname is not None:
            parent_cls = my_classes_by_idname.get(parent_idname)
            if parent_cls is not None:
                yield parent_cls


def iter_my_classes(modules):
    """
    生成器：遍历 modules 中的所有类，筛选出需要注册到 Blender 的基类子类。
    基类包括 Panel, Operator, PropertyGroup 等。
    """
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        # 如果该类是某个可注册基类的子类，且未被标记为 is_registered（避免重复注册）
        if any(issubclass(cls, base) for base in base_types):
            if not getattr(cls, "is_registered", False):
                yield cls


def get_classes_in_modules(modules):
    """
    收集所有模块中定义的所有类，返回一个集合。
    """
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes


def iter_classes_in_module(module):
    """
    生成器：遍历模块的 __dict__，返回其中的类对象。
    """
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value


def get_register_base_types():
    """
    返回 Blender 中所有可注册的基类类型（如 bpy.types.Panel, bpy.types.Operator 等）。
    这些类的子类需要被注册到 Blender。
    """
    return set(
        getattr(bpy.types, name)
        for name in [
            "Panel",
            "Operator",
            "PropertyGroup",
            "AddonPreferences",
            "Header",
            "Menu",
            "Node",
            "NodeSocket",
            "NodeTree",
            "UIList",
            "RenderEngine",
            "Gizmo",
            "GizmoGroup",
            'FileHandler'
        ]
    )


# 拓扑排序算法（解决依赖顺序）
#################################################


def toposort(deps_dict):
    """
    对依赖字典进行拓扑排序，返回排序后的列表。
    依赖字典：{ 类: 它所依赖的类集合 }
    算法：反复取出没有依赖（或依赖已处理）的类，按 bl_order 属性排序后加入结果。
    """
    sorted_list = []          # 最终的排序结果
    sorted_values = set()     # 已经排序过的类集合
    while len(deps_dict) > 0:
        unsorted = []                     # 本次循环中尚未解决的类
        sorted_list_sub = []              # 本次循环中可立即排序的类
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                # 无依赖，可以加入结果
                sorted_list_sub.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        # 更新依赖字典：移除已经排序的类
        deps_dict = {value: deps_dict[value] - sorted_values for value in unsorted}
        # 按 bl_order 属性排序（面板专用，值越小越靠前）
        sorted_list_sub.sort(key=lambda cls: getattr(cls, "bl_order", 0))
        sorted_list.extend(sorted_list_sub)
    return sorted_list