import bpy
scene = bpy.context.scene

# 获取场景所有属性，过滤出自定义的（排除Blender原生属性）
print(scene.hyc_props.rough_channel)