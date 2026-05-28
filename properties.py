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