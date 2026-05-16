import bpy
import json
import os


class HYC_Properties(bpy.types.PropertyGroup):

    metal_channel: bpy.props.EnumProperty(
        name="roughness",
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
        name="occlusion",
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
    workspaceDir: bpy.props.StringProperty(
        name="workspaceDir",
        default="",
        subtype="DIR_PATH",  # 显示为目录选择窗口
        description="选择工作目录",
    )  # type: ignore


class HYC_DragDrop_Json(bpy.types.Operator):
    """处理拖放JSON文件的操作符"""

    bl_idname = "hyc.drag_json_op"
    bl_label = "拖放导入JSON"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})  # type: ignore

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
        Albedo = "Albedo"
        Normals = "Normal"
        Mask = "Mask"
        semantic_map = {
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
            Mask: [
                "ORM",
                "Mix Map",
                "BaseORM",
            ],
        }

        possible_keys = semantic_map.get(semantic_name)
        if not possible_keys:  # 没有定义该语义
            return None

        for key in possible_keys:
            if key in data:
                return data[key]
        return None

    def execute(self, context):
        scene = context.scene
        self.props = scene.hyc_props

        if not self.filepath or not self.filepath.lower().endswith(".json"):
            self.report({"ERROR"}, "请拖放一个有效的 .json 文件")
            return {"CANCELLED"}

        for matName, texName in self.read_json().items():
            self.create_materials_node(matName)

            self.create_albedo(self.get_value_by_semantic(texName, "Albedo"))
            self.create_normal(self.get_value_by_semantic(texName, "Normal"))
            self.create_mask(self.get_value_by_semantic(texName, "Mask"))

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
        imgName: str = os.path.splitext(os.path.basename(imgPath))[0]
        image = bpy.data.images.get(imgName)
        if not image and os.path.exists(imgPath):
            image = bpy.data.images.load(imgPath)
        if sRGB is False:
            image.colorspace_settings.name = "Non-Color"

        image.alpha_mode = "CHANNEL_PACKED"
        return image, imgName

    def create_albedo(self, albedoImgPath):

        albedo, albedoName = self.create_image(albedoImgPath)
        self.albedoNode = self.create_textures_node("Albedo", albedo)
        self.links.new(self.albedoNode.outputs["Alpha"], self.matNode.inputs["Alpha"])
        if self.props.occlusion_channel == "0":
            self.links.new(
                self.albedoNode.outputs["Color"], self.matNode.inputs["Base Color"]
            )

    def create_mask(self, maskImgPath):

        mask, maskName = self.create_image(maskImgPath, False)
        maskNode = self.create_textures_node("Mask", mask)
        if "splitMask" in self.nodes:
            maskMapNode = self.nodes["splitMask"]
        else:
            maskMapNode = self.nodes.new(type="ShaderNodeSeparateColor")
            maskMapNode.name = "splitMask"
        self.links.new(maskNode.outputs["Color"], maskMapNode.inputs["Color"])

        if self.props.rough_channel != "0":
            self.links.new(
                maskMapNode.outputs[self.props.rough_channel],
                self.matNode.inputs["Roughness"],
            )
        if self.props.metal_channel != "0":
            self.links.new(
                maskMapNode.outputs[self.props.metal_channel],
                self.matNode.inputs["Metallic"],
            )
        if self.props.occlusion_channel != "0":
            if "blend" in self.nodes:
                blendNode = self.nodes["blend"]
            else:
                blendNode = self.nodes.new("ShaderNodeMixRGB")
                blendNode.name = "blend"
            self.links.new(
                maskMapNode.outputs[self.props.occlusion_channel], blendNode.inputs[1]
            )
            self.links.new(self.albedoNode.outputs["Color"], blendNode.inputs[2])
            blendNode.blend_type = "MULTIPLY"
            blendNode.inputs[0].default_value = 1
            self.links.new(
                blendNode.outputs["Color"], self.matNode.inputs["Base Color"]
            )

    def create_normal(self, normalImgPath, dx=False):

        normal, normalName = self.create_image(normalImgPath, False)
        normalNode = self.create_textures_node("Normal", normal)
        if "Normalmap" in self.nodes:
            normalMapNode = self.nodes["Normalmap"]
        else:
            normalMapNode = self.nodes.new(type="ShaderNodeNormalMap")
            normalMapNode.name = "Normalmap"
        self.links.new(normalNode.outputs["Color"], normalMapNode.inputs["Color"])
        self.links.new(normalMapNode.outputs["Normal"], self.matNode.inputs["Normal"])
        if self.props.directX:
            normalMapNode.convention = "DIRECTX"


class HYC_Create_LOD(bpy.types.Operator):
    """创建LOD操作符"""

    bl_idname = "hyc.create_lod_op"
    bl_label = "创建LOD"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.area.type == "VIEW_3D"

    def create_empty(self, name: str) -> bpy.types.Object:
        """创建空物体并设置属性

        如果场景中已存在同名物体则直接使用，不存在则创建新的空物体
        确保物体有 fbx_type 属性
        """
        # 检查场景中是否已存在同名物体
        existing_obj = bpy.data.objects.get(name)

        if existing_obj:
            # 如果存在，检查是否有fbx_type属性，没有则添加
            if "fbx_type" not in existing_obj:
                existing_obj["fbx_type"] = "LodGroup"
            return existing_obj

        # 不存在则创建新的空物体
        bpy.ops.object.empty_add(
            type="PLAIN_AXES",  # 纯轴显示
            location=(0, 0, 0),  # 位置设为原点，可按需修改
        )
        empty_obj = bpy.context.active_object
        empty_obj["fbx_type"] = "LodGroup"
        empty_obj.name = name
        return empty_obj

    def extract_base_name(self, obj_name: str) -> str:
        """从物体名称中提取基础名称

        支持的模式：
        - name_LOD0, name_LOD1 → 返回 name
        - UCX_name_01, UCX_name_02 → 返回 name

        Args:
            obj_name: 物体名称

        Returns:
            提取的基础名称，如果无法提取则返回原名称
        """
        # 如果有 UCX_ 前缀，先去掉
        if obj_name.startswith("UCX_"):
            obj_name = obj_name[4:]

        # 处理 _LOD 后缀的情况
        if "_LOD" in obj_name:
            return obj_name.split("_LOD")[0]

        return obj_name

    def create_parent_set(
        self, parent_obj: bpy.types.Object, lod_name: str, match_pattern: str
    ) -> int:
        """将场景中匹配模式的物体设置为父级的子级

        Args:
            parent_obj: 父级物体
            lod_name: LOD名称前缀
            match_pattern: 匹配模式（"LOD" 或 "UCX"）

        Returns:
            关联的物体数量
        """
        child_objects = []
        for obj in bpy.context.scene.objects:
            # 排除空物体和相机、灯光等非网格物体
            if obj.type != "MESH":
                continue

            if match_pattern == "LOD":
                # 匹配 name_LOD0, name_LOD1, ... 模式
                if obj.name.startswith(lod_name + "_LOD"):
                    suffix = obj.name[len(lod_name) + 4 :]
                    if suffix.isdigit():
                        child_objects.append(obj)
            elif match_pattern == "UCX":
                # 匹配 UCX_name_LOD0_01, UCX_name_LOD1_02, ... 模式
                ucx_prefix = "UCX_" + lod_name + "_LOD"
                if obj.name.startswith(ucx_prefix):
                    # 提取 LOD 后的部分
                    remaining = obj.name[len(ucx_prefix) :]
                    # 格式应该是数字_数字，如 "0_01"
                    if "_" in remaining:
                        parts = remaining.split("_", 1)
                        if parts[0].isdigit() and parts[1].isdigit():
                            child_objects.append(obj)

        for obj in child_objects:
            obj.parent = parent_obj
            obj.matrix_parent_inverse = parent_obj.matrix_world.inverted()

        return len(child_objects)

    def execute(self, context):
        # 获取用户选择的物体
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({"WARNING"}, "请先选择物体")
            return {"CANCELLED"}

        # 从选中物体中提取基础名称
        base_names = set()
        for obj in selected_objects:
            base_name = self.extract_base_name(obj.name)
            base_names.add(base_name)

        total_count = 0
        for base_name in base_names:
            # 创建 name 空物体（最顶层父级）
            main_empty = bpy.data.objects.get(base_name)
            if not main_empty:
                bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
                main_empty = bpy.context.active_object
                main_empty.name = base_name

            # 创建 name_LOD 空物体（带 fbx_type 属性）
            lod_empty = self.create_empty(base_name + "_LOD")
            # 将 name_LOD 设置为 name 的子级
            lod_empty.parent = main_empty
            lod_empty.matrix_parent_inverse = main_empty.matrix_world.inverted()

            # 将 LOD 物体关联到 name_LOD
            lod_count = self.create_parent_set(lod_empty, base_name, "LOD")

            # 将 UCX 物体关联到 name
            ucx_count = self.create_parent_set(main_empty, base_name, "UCX")

            total_count += lod_count + ucx_count

            self.report(
                {"INFO"},
                f"已创建层级结构: {base_name} -> {base_name}_LOD (关联 {lod_count} 个LOD), UCX (关联 {ucx_count} 个)",
            )

        if total_count > 0:
            self.report({"INFO"}, f"共处理 {total_count} 个物体")
        else:
            self.report({"INFO"}, "未找到匹配的 LOD 或 UCX 物体")

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
