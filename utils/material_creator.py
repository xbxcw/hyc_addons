import bpy
import os
from pathlib import Path


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