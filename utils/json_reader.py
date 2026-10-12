import json
import os


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