import maya.cmds as cmds


def merge_models():
    # 1. 获取选择的所有模型，并且记录最后一个模型的名字
    selected = cmds.ls(selection=True)
    if not selected:
        cmds.warning("请先选择模型！")
        return

    last_name = selected[-1]

    # 2. 合并所有模型
    merged = cmds.polyUnite(selected, constructionHistory=False)[0]

    # 3. 删除所有历史记录
    cmds.delete(merged, constructionHistory=True)

    # 4. 将合并后的模型用记录的名字命名
    cmds.rename(merged, last_name)

    print(f"合并完成，模型已命名为: {last_name}")

def split_models():
    # 1. 获取当前选择的面，并记录模型名称
    selected_faces = cmds.ls(selection=True, flatten=True)
    if not selected_faces:
        cmds.warning("请先在面模式下选择面！")
        return

    if '.f[' not in selected_faces[0]:
        cmds.warning("请选择面而不是对象！请切换到面模式。")
        return

    mesh_name = selected_faces[0].split('.')[0]
    original_name = mesh_name

    # 2. 记录选择的面索引，并复制模型
    face_parts = [f.split('.')[-1] for f in selected_faces]
    dup = cmds.duplicate(mesh_name)[0]

    # 3. 从原始模型删除选择的面
    cmds.delete(selected_faces)

    # 4. 从复制体删除未选择的面（保留与原始选择相同的面）
    total = cmds.polyEvaluate(dup, face=True)
    cmds.select("{}.f[0:{}]".format(dup, total - 1), replace=True)
    dup_faces = ["{}.{}".format(dup, fp) for fp in face_parts]
    cmds.select(dup_faces, deselect=True)
    cmds.delete()

    # 5. 清理历史记录
    cmds.delete(original_name, constructionHistory=True)
    cmds.delete(dup, constructionHistory=True)

    # 6. 解组
    for obj in [original_name, dup]:
        parent = cmds.listRelatives(obj, parent=True)
        if parent:
            cmds.parent(obj, world=True)

    # 7. 命名：原模型保留原名，新模型命名为 name_##
    new_obj = None
    for i in range(100):
        new_name = "{}_{}".format(original_name, str(i).zfill(2))
        if not cmds.objExists(new_name):
            cmds.rename(dup, new_name)
            new_obj = new_name
            break
    else:
        new_obj = dup

    # 8. 选中结果以便查看
    cmds.select([original_name, new_obj])
    print("分离完成！原始模型: {}，新模型: {}".format(original_name, new_obj))

split_models()