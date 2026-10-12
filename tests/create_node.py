import bpy
import os


def create_materials_node(matName: str):
    mat = bpy.data.materials.get(matName)
    if not mat:
        mat = bpy.data.materials.new(name=matName)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    matNode = nodes["Principled BSDF"]
    return nodes, links, matNode, mat


def create_textures_node(texName, nodes, imgae):
    if texName in nodes:

        texNode: bpy.types.ShaderNodeTexImage = nodes[texName]
    else:

        texNode: bpy.types.ShaderNodeTexImage = nodes.new(type="ShaderNodeTexImage")

    texNode.name = texName
    texNode.label = texName
    texNode.image = imgae
    return texNode


def create_image(imgPath, sRGB=True):
    imgName: str = os.path.basename(imgPath)
    image = bpy.data.images.get(imgName)
    if not image and os.path.exists(imgPath):
        image = bpy.data.images.load(imgPath)
    if sRGB is False:
        image.colorspace_settings.name = "Non-Color"

    image.alpha_mode = "CHANNEL_PACKED"
    return image


print("=" * 50)
matName = "testMat"
texName = "BaseColor"
imgPath = (
    r"E:\work\BP_FloatingCastle_Building_21\Tex\T_BlackThorns_Company_B1_Wall001_N.tga"
)
nodes, links, matNode, mat = create_materials_node(matName)


image = create_image(imgPath,False)
texNode = create_textures_node(texName, nodes, image)

links.new(texNode.outputs["Color"], matNode.inputs["Base Color"])

print(texNode)

print("*" * 50)
