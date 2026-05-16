import bpy
import os
wrokspace = r"E:\work\SM_Plant"
FileName = "SM_Plant_Potted01_b_036"
FilePath = os.path.join(wrokspace, FileName + '.blend')

# 打开blend文件
bpy.ops.wm.open_mainfile(filepath=FilePath)