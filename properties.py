import bpy


class HYC_Properties(bpy.types.PropertyGroup):

    metal_channel: bpy.props.EnumProperty(
        name="Metallic",
        items=(
            ("Red", "R", "Red"),
            ("Green", "G", "Green"),
            ("Blue", "B", "Blue"),
            ("Alpha", "A", "A"),
            ("0", "off", "Off"),
        ),
        default="Blue",
    )  # type: ignore
    rough_channel: bpy.props.EnumProperty(
        name="roughness",
        items=(
            ("Red", "R", "Red"),
            ("Green", "G", "Green"),
            ("Blue", "B", "Blue"),
            ("Alpha", "A", "A"),
            ("0", "off", "Off"),
        ),
        default="Green",
    )  # type: ignore
    occlusion_channel: bpy.props.EnumProperty(
        name="AO",
        items=(
            ("Red", "R", "Red"),
            ("Green", "G", "Green"),
            ("Blue", "B", "Blue"),
            ("Alpha", "A", "A"),
            ("0", "off", "Off"),
        ),
        default="Red",
    )  # type: ignore
    directX: bpy.props.BoolProperty(
        name="directX",
        default=True,
        description="是否使用DirectX渲染",
    )  # type: ignore
    export_mode: bpy.props.EnumProperty(
        name="导出模式",
        items=(
            ("ue", "UE", "导出到 Fbx 文件夹"),
            ("bake", "Bake", "导出到 bake/当前blend文件名/ 文件夹"),
        ),
        default="ue",
        description="选择导出目标文件夹",
    )  # type: ignore
    workspaceDir: bpy.props.StringProperty(
        name="工作目录",
        default="",
        subtype="DIR_PATH",
        description="选择工作目录",
    )  # type: ignore