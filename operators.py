import bpy
import json
import os

class HYC_Properties(bpy.types.PropertyGroup):
    metal_channel = bpy.props.EnumProperty(
    name='roughness',
    items=(('R','R','R'),('G','G','G'),('B','B','B'),('A','A','A')),
    default='G'
    )
    rough_channel = bpy.props.EnumProperty(
        name='roughness',
        items=(('R','R','R'),('G','G','G'),('B','B','B'),('A','A','A')),
        default='G'
    )

class HYC_DragDrop_Json(bpy.types.Operator):
    """处理拖放JSON文件的操作符"""

    bl_idname = "hyc.drag_json_op"
    bl_label = "拖放导入JSON"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})  # type: ignore
    Albedo = "Albedo"
    Normals = "Normal"
    Mask = "Mask"
    SEMANTIC_KEYS = {
        Albedo: [
            "D",
            "Albedo",
            "D/DA",
            "WindowBase",
            "BaseAlbedo (A:Height)",
            "DA",
            "ColorOpacity",
        ],
        Normals: [
            "Normal",
            "Normal Map",
            "WindowNR",
            "BaseNormal",
            "NormalMask",
            "NormalMap",
        ],
        Mask: ["ORM", "Mix Map", "BaseORM"],
    }

    def get_value_by_semantic(self, data, semantic_name, semantic_map=None):
        """
        根据语义名称从字典中获取第一个存在的 key 对应的值。

        参数:
            data: dict, 原始字典
            semantic_name: str, 语义名（如 "Albedo"）
            semantic_map: dict, 语义到 key 列表的映射（可选，默认使用全局 SEMANTIC_KEYS）

        返回:
            对应的值；如果都不存在则返回 None
        """
        if semantic_map is None:
            semantic_map = self.SEMANTIC_KEYS

        possible_keys = semantic_map.get(semantic_name)
        if not possible_keys:  # 没有定义该语义
            return None

        for key in possible_keys:
            if key in data:
                return data[key]
        return None

    def execute(self, context):
        if not self.filepath or not self.filepath.lower().endswith(".json"):
            self.report({"ERROR"}, "请拖放一个有效的 .json 文件")
            return {"CANCELLED"}

        self.read_json()
        return {"CANCELLED"}

    def read_json(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        return json_data

    def create_materials_node(self, matName: str):
        mat = bpy.data.materials.get(matName)
        if not mat:
            mat = bpy.data.materials.new(name=matName)
        mat.use_nodes = True

        self.nodes = mat.node_tree.nodes
        self.links = mat.node_tree.links
        self.matNode = self.nodes["Principled BSDF"]

    def create_textures_node(self, texName, imgae):
        if texName in self.nodes:

            texNode: bpy.types.ShaderNodeTexImage = self.nodes[texName]
        else:

            texNode: bpy.types.ShaderNodeTexImage = self.nodes.new(
                type="ShaderNodeTexImage"
            )

        texNode.name = texName
        texNode.label = texName
        texNode.image = imgae
        return texNode

    def create_image(self, imgPath, sRGB=True):
        imgName: str = os.path.splitext(os.path.basename(imgPath))
        image = bpy.data.images.get(imgName)
        if not image and os.path.exists(imgPath):
            image = bpy.data.images.load(imgPath)
        if sRGB is False:
            image.colorspace_settings.name = "Non-Color"

        image.alpha_mode = "CHANNEL_PACKED"
        return image, imgName

    def create_albedo(self, albedoImgPath):

        albedo, albedoName = self.create_image(albedoImgPath)
        albedoNode = self.create_textures_node(albedoName, albedo)

    def create_mask(self, maskImgPath):

        mask, maskName = self.create_image(maskImgPath, False)
        maskNode = self.create_textures_node(maskName, mask)
        maskMapNode = self.nodes.new(type="ShaderNodeSeparateColor")
        self.links.new(maskNode["Color"], maskMapNode["Color"])

    def create_normal(self, normalImgPath, dx=False):

        normal, normalName = self.create_image(normalImgPath, False)
        normalNode = self.create_textures_node(normalName, normal)
        normalMapNode = self.nodes.new(type="ShaderNodeNormalMap")
        self.links.new(normalNode.outputs["Color"], normalMapNode.inputs["Color"])
        self.links.new(normalMapNode.outputs["Normal"], self.matNode.inputs["Normal"])
        if dx:
            normalMapNode.convention = "DIRECTX"


class HYC_Create_LOD(bpy.types.Operator):
    """创建LOD操作符"""

    bl_idname = "hyc.create_lod_op"
    bl_label = "创建LOD"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.area.type == "VIEW_3D"

    def execute(self, context):
        bpy.ops.object.empty_add(
            type="PLAIN_AXES",  # 纯轴显示
            location=(0, 0, 0),  # 位置设为原点，可按需修改
        )

        # 获取新创建的空物体（刚创建后会自动成为活动对象）
        empty_obj = bpy.context.active_object

        # 设置自定义属性（Blender 中直接赋值即可，类型自动推断为字符串）
        empty_obj["fbx_type"] = "LodGroup"

        # 可选：重命名物体，方便识别
        empty_obj.name = "LodGroup_Empty"
        return {"FINISHED"}


class HYC_FH_DragJson(bpy.types.FileHandler):
    """用于在3D视图中拖放 .json 文件的文件处理器"""

    bl_idname = "HYC_FH_DragJson"
    bl_label = "拖放导入 JSON 文件"
    bl_import_operator = "hyc.drag_json_op"
    bl_file_extensions = ".json"

    @classmethod
    def poll_drop(cls, context):
        return context.area.type == "VIEW_3D"
