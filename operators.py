import bpy
import json
import os
from pathlib import Path


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
    workspaceDir: bpy.props.StringProperty(
        name="workspaceDir",
        default="",
        subtype="DIR_PATH",  # 显示为目录选择窗口
        description="选择工作目录",
    )  # type: ignore


# ============================================
# JSON读取器类 - 负责读取和验证JSON文件
# ============================================
class HYC_JsonReader:
    """JSON文件读取器 - 支持按材质名单独的JSON文件"""
    
    # 语义名称映射
    SEMANTIC_MAP = {
        "Albedo": ["D", "Albedo", "D/DA", "WindowBase", "BaseAlbedo (A:Height)", "DA", "ColorOpacity", "Base Color"],
        "Normal": ["Normal", "NormalMap", "N", "NR", "NormalMask", "Normal Map"],
        "Mask": ["M", "Mask", "Mix Map", "AO", "Roughness", "Metallic", "ORM"],
    }
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def read_json(self) -> dict:
        """读取JSON文件并返回数据"""
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def validate_textures(self, json_data: dict, mat_name: str = "") -> list:
        """验证JSON中引用的纹理文件是否存在
        
        参数:
            json_data: dict, 材质的纹理数据
            mat_name: str, 材质名称（用于警告信息）
            
        返回:
            缺失文件的警告信息列表
        """
        warnings = []
        for tex_key, tex_path in json_data.items():
            if tex_path and not os.path.exists(tex_path):
                warnings.append(f"材质 {mat_name} 的纹理 {tex_key} 不存在: {tex_path}")
        return warnings
    
    @classmethod
    def get_value_by_semantic(cls, data: dict, semantic_name: str) -> str | None:
        """
        根据语义名称从字典中获取第一个存在的 key 对应的值。

        参数:
            data: dict, 原始字典
            semantic_name: str, 语义名（如 "Albedo"）

        返回:
            对应的值；如果都不存在则返回 None
        """
        possible_keys = cls.SEMANTIC_MAP.get(semantic_name, [])
        for key in possible_keys:
            if key in data:
                return data[key]
        return None
    
    @classmethod
    def load_materials_from_folder(cls, json_folder: str) -> dict:
        """
        从JSON文件夹加载所有材质JSON文件
        
        参数:
            json_folder: str, JSON文件夹路径
            
        返回:
            dict, 材质名 -> 纹理数据的字典，结构: {"文件名": {参数名: 路径}}
        """
        materials_data = {}
        
        if not os.path.exists(json_folder):
            print(f"JSON文件夹不存在: {json_folder}")
            return materials_data
        
        # 遍历文件夹中的所有json文件
        for filename in os.listdir(json_folder):
            if filename.endswith(".json"):
                mat_name = filename[:-5]  # 去掉 .json 后缀
                json_path = os.path.join(json_folder, filename)
                try:
                    reader = cls(json_path)
                    mat_data = reader.read_json()
                    
                    # 确保返回结构是 {"文件名": {参数名: 路径}}
                    if isinstance(mat_data, dict):
                        # 如果是字典，直接使用
                        materials_data[mat_name] = mat_data
                    elif isinstance(mat_data, str):
                        # 如果是字符串（可能是路径），包装成字典
                        materials_data[mat_name] = {"path": mat_data}
                    else:
                        # 其他类型，记录错误
                        materials_data[mat_name] = {}
                        print(f"警告: {filename} 内容格式不支持")
                        
                except Exception as e:
                    print(f"读取JSON文件失败 {filename}: {e}")
        
        return materials_data


# ============================================
# 材质创建器类 - 负责创建材质球和纹理节点
# ============================================
class HYC_MaterialCreator:
    """材质球创建器"""
    
    def __init__(self, props):
        self.props = props
        self.nodes = None
        self.links = None
        self.matNode = None
        self.albedoNode = None
    
    def create_materials_node(self, matName: str):
        """创建或获取材质，并初始化节点树"""
        mat = bpy.data.materials.get(matName)
        if not mat:
            mat = bpy.data.materials.new(name=matName)
        mat.use_nodes = True

        self.nodes = mat.node_tree.nodes
        self.links = mat.node_tree.links
        self.matNode = self.nodes["Principled BSDF"]
    
    def create_textures_node(self, texName: str, image) -> bpy.types.ShaderNodeTexImage:
        """创建或获取纹理节点"""
        if texName in self.nodes:
            texNode = self.nodes[texName]
        else:
            texNode = self.nodes.new(type="ShaderNodeTexImage")

        texNode.name = texName
        texNode.label = texName
        texNode.image = image
        return texNode
    
    def create_image(self, imgPath: str, sRGB: bool = True) -> tuple:
        """创建或获取图像对象"""
        imgName = Path(imgPath).stem
        image = bpy.data.images.get(imgName)
        if not image and os.path.exists(imgPath):
            image = bpy.data.images.load(imgPath)
        if sRGB is False and image:
            image.colorspace_settings.name = "Non-Color"
        if image:
            image.alpha_mode = "CHANNEL_PACKED"
        return image, imgName
    
    def create_albedo(self, albedoImgPath: str):
        """创建Albedo纹理节点"""
        albedo, albedoName = self.create_image(albedoImgPath)
        self.albedoNode = self.create_textures_node("Albedo", albedo)
        self.links.new(self.albedoNode.outputs["Alpha"], self.matNode.inputs["Alpha"])
        if self.props.occlusion_channel == "0":
            self.links.new(
                self.albedoNode.outputs["Color"], self.matNode.inputs["Base Color"]
            )
    
    def create_mask(self, maskImgPath: str):
        """创建Mask纹理节点"""
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
    
    def create_normal(self, normalImgPath: str):
        """创建Normal纹理节点"""
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


# ============================================
# 操作符类 - 协调JSON读取和材质创建
# ============================================
class HYC_DragDrop_Json(bpy.types.Operator):
    """处理拖放JSON文件、多个JSON文件或JSON文件夹的操作符"""

    bl_idname = "hyc.drag_json_op"
    bl_label = "拖放导入JSON"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})  # type: ignore
    directory: bpy.props.StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE', 'HIDDEN'})  # type: ignore
    files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={'SKIP_SAVE', 'HIDDEN'})  # type: ignore

    def load_single_json(self, json_path: str) -> dict:
        """加载单个JSON文件并返回 {材质名: {参数: 路径}} 结构"""
        result = {}
        try:
            json_reader = HYC_JsonReader(json_path)
            mat_data = json_reader.read_json()
            # 获取文件名（不带扩展名）作为材质名
            mat_name = os.path.basename(json_path)[:-5]  # 去掉 .json
            # 确保结构是 {材质名: {参数名: 路径}}
            if isinstance(mat_data, dict):
                result[mat_name] = mat_data
            else:
                result[mat_name] = {"path": str(mat_data) if mat_data else ""}
        except Exception as e:
            self.report({"WARNING"}, f"读取JSON文件失败 {json_path}: {e}")
        return result

    def execute(self, context):
        scene = context.scene
        props = scene.hyc_props
        
        # 打印拖放的文件信息
        print("\n=== 拖放文件信息 ===")
        print(f"filepath: {self.filepath}")
        print(f"directory: {self.directory}")
        print(f"files count: {len(self.files)}")
        if self.files:
            for i, file_item in enumerate(self.files):
                filename = getattr(file_item, "name", str(file_item))
                print(f"  文件 {i+1}: {filename}")
        print("===================")
        
        # 设置默认工作目录
        if not props.workspaceDir:
            props.workspaceDir = os.path.dirname(bpy.data.filepath)
        
        json_data = {}
        
        # 情况1: 通过 files 属性拖放多个文件
        if self.files and len(self.files) > 0:
            base_path = self.directory if self.directory else os.path.dirname(self.filepath)
            print(f"检测到 {len(self.files)} 个拖放文件，基础路径: {base_path}")
            for i, file_item in enumerate(self.files):
                filename = getattr(file_item, "name", "")
                if filename and filename.endswith(".json"):
                    json_path = os.path.join(base_path, filename)
                    print(f"  处理文件 {i+1}: {json_path}")
                    mat_data = self.load_single_json(json_path)
                    json_data.update(mat_data)
            
            if not json_data:
                self.report({"WARNING"}, "没有找到有效的JSON文件")
                return {"CANCELLED"}
        
        # 情况2: 通过 filepath 属性（单个文件或文件夹）
        elif self.filepath:
            # 判断是文件还是文件夹
            if os.path.isdir(self.filepath):
                # 从JSON文件夹加载所有材质
                json_data = HYC_JsonReader.load_materials_from_folder(self.filepath)
                if not json_data:
                    self.report({"WARNING"}, f"JSON文件夹中没有找到有效的材质文件: {self.filepath}")
                    return {"CANCELLED"}
            else:
                # 从单个JSON文件读取
                json_data = self.load_single_json(self.filepath)
        
        # 情况3: 没有提供路径，尝试自动查找
        else:
            if bpy.data.filepath:
                # 优先从JSON文件夹读取
                json_folder = os.path.join(props.workspaceDir, 'JSON')
                if os.path.exists(json_folder):
                    json_data = HYC_JsonReader.load_materials_from_folder(json_folder)
                else:
                    # 兼容旧格式：从Tex文件夹读取
                    json_path = os.path.join(props.workspaceDir, 'Tex', 
                                            os.path.basename(bpy.data.filepath).replace(".blend", ".json"))
                    if os.path.exists(json_path):
                        json_data = self.load_single_json(json_path)
            
            if not json_data:
                self.report({"ERROR"}, "请先保存文件或指定要导入的 JSON 文件/文件夹路径")
                return {"CANCELLED"}

        # 创建JSON读取器实例用于验证
        json_reader = HYC_JsonReader(self.filepath)
        
        # 验证纹理文件
        warnings = []
        for mat_name, textures in json_data.items():
            mat_warnings = json_reader.validate_textures(textures, mat_name)
            warnings.extend(mat_warnings)
        
        for warning in warnings:
            self.report({"WARNING"}, warning)

        # 创建材质创建器
        mat_creator = HYC_MaterialCreator(props)

        # 遍历材质并创建
        success_count = 0
        for mat_name, textures in json_data.items():
            # 确保 textures 是字典
            if not isinstance(textures, dict):
                self.report({"WARNING"}, f"材质 {mat_name} 的数据格式错误，跳过")
                continue
            
            mat_creator.create_materials_node(mat_name)

            albedo_path = HYC_JsonReader.get_value_by_semantic(textures, "Albedo")
            normal_path = HYC_JsonReader.get_value_by_semantic(textures, "Normal")
            mask_path = HYC_JsonReader.get_value_by_semantic(textures, "Mask")
            
            has_texture = False
            if albedo_path:
                mat_creator.create_albedo(albedo_path)
                has_texture = True
            if normal_path:
                mat_creator.create_normal(normal_path)
                has_texture = True
            if mask_path:
                mat_creator.create_mask(mask_path)
                has_texture = True
            
            if has_texture:
                success_count += 1

        self.report({"INFO"}, f"成功导入 {success_count} 个材质")
        return {"FINISHED"}


class HYC_Create_LOD(bpy.types.Operator):
    """创建LOD操作符"""

    bl_idname = "hyc.create_lod_op"
    bl_label = "创建LOD"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.area.type == "VIEW_3D"

    def move_to_first_collection(self, obj):
        """将物体移动到场景的第一个集合"""
        if bpy.data.collections:
            first_collection = bpy.data.collections[0]
            # 从当前所有集合中移除
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            # 添加到第一个集合
            first_collection.objects.link(obj)

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
            # 移动到第一个集合
            self.move_to_first_collection(existing_obj)
            return existing_obj

        # 不存在则创建新的空物体
        bpy.ops.object.empty_add(
            type="PLAIN_AXES",  # 纯轴显示
            location=(0, 0, 0),  # 位置设为原点，可按需修改
        )
        empty_obj = bpy.context.active_object
        empty_obj["fbx_type"] = "LodGroup"
        empty_obj.name = name
        # 移动到第一个集合
        self.move_to_first_collection(empty_obj)
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
            # 为最顶层空物体添加自定义属性 fbx_type = Transform
            main_empty["fbx_type"] = "Transform"
            # 移动到第一个集合
            self.move_to_first_collection(main_empty)

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
    """用于在3D视图中拖放 .json 文件的文件处理器（支持多选）"""

    bl_idname = "HYC_FH_DragJson"
    bl_label = "拖放导入 JSON 文件"
    bl_import_operator = "hyc.drag_json_op"
    bl_file_extensions = ".json"
    bl_file_selector = False  # 禁用文件选择对话框

    @classmethod
    def poll_drop(cls, context):
        return context.area.type == "VIEW_3D"


class HYC_OT_ExportFBX(bpy.types.Operator):
    """导出选中空物体及其子级为FBX文件"""

    bl_idname = "hyc.export_fbx_op"
    bl_label = "导出FBX"
    bl_options = {"REGISTER", "UNDO"}

    def get_hierarchy_objects(self, parent_obj):
        """递归获取父物体及其所有子级物体（包括空物体和网格）"""
        objects = []

        def collect_objects(obj):
            # 收集空物体和网格物体
            if obj.type == "MESH" or obj.type == "EMPTY":
                objects.append(obj)
            for child in obj.children:
                collect_objects(child)

        collect_objects(parent_obj)
        return objects

    def export_single_fbx(self, parent_obj, fbx_dir):
        """导出单个空物体及其层级为FBX"""
        # 获取层级中的所有物体
        hierarchy_objects = self.get_hierarchy_objects(parent_obj)

        if not hierarchy_objects:
            self.report({"WARNING"}, f"空物体 {parent_obj.name} 下没有可导出的物体")
            return False

        # 构建输出路径
        fbx_path = os.path.join(fbx_dir, f"{parent_obj.name}.fbx")

        # 取消所有选择
        bpy.ops.object.select_all(action="DESELECT")

        # 选择层级中的所有物体
        for obj in hierarchy_objects:
            obj.select_set(True)

        # 导出FBX - Blender 5.x 版本完整参数（带详细注释）
        bpy.ops.export_scene.fbx(
            # ===== 基础设置 =====
            filepath=fbx_path,  # 导出文件的完整路径
            check_existing=True,  # 检查文件是否已存在（存在时弹窗询问）
            filter_glob="*.fbx",  # 文件过滤格式
            # ===== 选择设置 =====
            use_selection=True,  # 仅导出选中的物体
            use_visible=False,  # 导出可见物体
            use_active_collection=False,  # 导出活动集合中的物体
            collection="",  # 指定导出的集合名称
            # ===== 对象类型 =====
            object_types={"MESH", "EMPTY"},  # 导出的对象类型集合（网格+空物体）
            # 可选值: 'EMPTY', 'CAMERA', 'LIGHT', 'ARMATURE', 'MESH', 'OTHER'
            # ===== 缩放设置 =====
            global_scale=1.0,  # 全局缩放因子
            apply_unit_scale=True,  # 应用单位缩放（米/厘米等）
            apply_scale_options="FBX_SCALE_NONE",  # 缩放选项
            # 可选值: 'FBX_SCALE_NONE', 'FBX_SCALE_UNITS', 'FBX_SCALE_CUSTOM', 'FBX_SCALE_ALL'
            # ===== 空间变换 =====
            use_space_transform=True,  # 使用空间变换
            bake_space_transform=False,  # 将空间变换烘焙到顶点
            # ===== 轴设置 =====
            axis_forward="-Z",  # 前向轴（Blender默认）
            axis_up="Y",  # 向上轴
            # 可选值: 'X', 'Y', 'Z', '-X', '-Y', '-Z'
            # ===== 网格设置 =====
            use_mesh_modifiers=True,  # 应用网格修改器
            use_mesh_modifiers_render=True,  # 使用渲染时的修改器设置
            mesh_smooth_type="EDGE",  # 平滑类型
            # 可选值: 'OFF', 'FACE', 'EDGE', 'SMOOTH_GROUP'
            colors_type="SRGB",  # 颜色类型
            # 可选值: 'NONE', 'SRGB', 'LINEAR'
            prioritize_active_color=False,  # 优先使用活动颜色层
            use_subsurf=False,  # 导出细分表面
            use_mesh_edges=False,  # 导出网格边
            use_tspace=False,  # 导出切线空间数据
            use_triangles=False,  # 转换为三角形
            # ===== 自定义属性 =====
            use_custom_props=True,  # 导出自定义属性到FBX
            # ===== 骨骼设置 =====
            add_leaf_bones=False,  # 添加叶骨骼（末端骨骼）
            primary_bone_axis="Y",  # 主骨骼轴
            secondary_bone_axis="X",  # 次骨骼轴
            use_armature_deform_only=False,  # 仅导出蒙皮骨骼
            armature_nodetype="NULL",  # 骨骼根节点类型
            # 可选值: 'NULL', 'ROOT', 'LIMBNODE'
            # ===== 动画烘焙 =====
            bake_anim=False,  # 是否烘焙动画
            bake_anim_use_all_bones=False,  # 使用所有骨骼烘焙动画
            bake_anim_use_nla_strips=False,  # 使用NLA strips烘焙
            bake_anim_use_all_actions=False,  # 烘焙所有动作
            bake_anim_force_startend_keying=False,  # 强制首尾关键帧
            bake_anim_step=1.0,  # 动画采样步长
            bake_anim_simplify_factor=1.0,  # 动画简化因子（1.0=不简化）
            # ===== 路径/纹理 =====
            path_mode="AUTO",  # 纹理路径模式
            # 可选值: 'AUTO', 'ABSOLUTE', 'RELATIVE', 'MATCH', 'STRIP', 'COPY'
            embed_textures=False,  # 将纹理嵌入FBX文件
            # ===== 批处理 =====
            batch_mode="OFF",  # 批处理模式
            # 可选值: 'OFF', 'SCENE', 'COLLECTION', 'SCENE_COLLECTION', 'ACTIVE_SCENE_COLLECTION'
            use_batch_own_dir=True,  # 每个物体使用独立目录
            # ===== 元数据 =====
            use_metadata=True,  # 导出元数据
        )

        self.report({"INFO"}, f"成功导出FBX: {fbx_path}")
        return True

    def execute(self, context):
        scene = context.scene
        props = scene.hyc_props
        # 获取选中的物体
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({"WARNING"}, "请先选择空物体")
            return {"CANCELLED"}
        # 过滤出所有选中的空物体
        empty_objects = [obj for obj in selected_objects if obj.type == "EMPTY"]
        if not empty_objects:
            self.report({"WARNING"}, "请至少选择一个空物体")
            return {"CANCELLED"}
        # 获取工作目录
        workspace_dir = props.workspaceDir
        if not workspace_dir:
            self.report({"WARNING"}, "请先设置工作目录")
            return {"CANCELLED"}
        # 创建FBX输出目录
        fbx_dir = os.path.join(workspace_dir, "Fbx")
        os.makedirs(fbx_dir, exist_ok=True)
        # 批量导出每个空物体
        export_count = 0
        for parent_obj in empty_objects:
            if self.export_single_fbx(parent_obj, fbx_dir):
                export_count += 1
        if export_count > 0:
            self.report({"INFO"}, f"共成功导出 {export_count} 个FBX文件")
        else:
            self.report({"WARNING"}, "没有成功导出任何FBX文件")
        return {"FINISHED"}


class HYC_OT_BakeGrassPivotUV(bpy.types.Operator):
    """将选中物体的原点坐标烘焙到UV层"""

    bl_idname = "hyc.bake_grass_pivot_uv"
    bl_label = "烘焙草叶轴心UV"
    bl_options = {"REGISTER", "UNDO"}

    def get_all_selected_transform_objects(self):
        """递归获取选中物体及所有子级物体"""
        result_objs = []

        def collect_child_obj(obj):
            if obj.type == "MESH":
                if obj not in result_objs:
                    result_objs.append(obj)
            # 递归遍历子物体
            for child in obj.children:
                collect_child_obj(child)

        # 遍历所有选中物体
        for sel_obj in bpy.context.selected_objects:
            collect_child_obj(sel_obj)
        return result_objs

    def get_obj_world_origin(self, obj):
        """获取物体原点世界坐标 (X,Y,Z)"""
        return obj.matrix_world.translation

    def create_or_switch_uv_layer(self, mesh, grass_pivot_uv_name):
        """创建GrassPivotUV UV层，不存在则新建"""
        uv_layers = mesh.uv_layers
        # 判断是否存在第二个UV层（索引为1）
        if len(uv_layers) > 1:
            uv_layer = uv_layers[1]
        else:
            # 不存在则创建新的UV层
            uv_layer = uv_layers.new(name=grass_pivot_uv_name)
        # 激活目标UV层
        uv_layers.active = uv_layer
        return uv_layer

    def execute(self, context):
        # 全局定义轴心UV集合名
        grass_pivot_uv_name = "GrassPivotUV"

        # 单位转换：Maya 默认使用厘米(cm)，Blender 默认使用米(m)
        unity_scale = 100.0  # 1m = 100cm
        """执行烘焙操作"""
        selected_meshes = self.get_all_selected_transform_objects()
        if not selected_meshes:
            self.report({"WARNING"}, "请至少选中一个模型物体")
            return {"CANCELLED"}

        for obj in selected_meshes:
            if obj.type != "MESH":
                continue
            self.report({"INFO"}, f"处理物体: {obj.name}")

            mesh = obj.data
            # 创建并激活目标UV层
            uv_layer = self.create_or_switch_uv_layer(mesh, grass_pivot_uv_name)
            if not uv_layer:
                self.report({"ERROR"}, f"创建UV层失败: {obj.name}")
                continue

            # 获取物体世界原点
            world_pos = self.get_obj_world_origin(obj)
            # Maya vs Blender 坐标系映射:
            # Maya: X=右, Y=上, Z=前(深度)
            # Blender: X=右, Y=前(深度), Z=上
            # 单位转换：Blender 的米 -> Maya 的厘米（乘以 100）
            u_val = world_pos.x * unity_scale
            v_val = 1.0 - (-world_pos.y * unity_scale)  # Maya.Z = -Blender.Y

            # 遍历所有顶点UV，统一赋值
            for uv_data in uv_layer.data:
                uv_data.uv = (u_val, v_val)

            self.report({"INFO"}, f"赋值完成 U:{u_val:.3f}  V:{v_val:.3f}")

        self.report({"INFO"}, "草叶轴心UV烘焙完成！")
        print("\n>>> 全部烘焙结束")
        return {"FINISHED"}