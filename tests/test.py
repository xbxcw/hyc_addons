import bpy


def create_billboard_material():
    selected_objs = bpy.context.selected_objects

    if not selected_objs:
        print("请至少选择一个模型")
        return

    for obj in selected_objs:
        original_name = obj.name
        print(f"原始名称: {original_name}")

        parts = original_name.split("_")
        if len(parts) < 3:
            print(f"  跳过 '{original_name}'：名称格式不符合要求（至少需要三段，如 SM_Holly037_LOD3）")
            continue

        core_name = "_".join(parts[1:-1])
        material_name = f"MI_{core_name}_Billboard"

        print(f"  处理后名称: {material_name}")

        mat = bpy.data.materials.get(material_name)
        if mat:
            print(f"  材质 '{material_name}' 已存在，跳过创建")
        else:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True
            print(f"  材质 '{material_name}' 创建成功")

        if obj.type == "MESH":
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            print(f"  已将材质 '{material_name}' 赋给模型 '{original_name}'")

    print("\nBillboard 材质创建完成！")


create_billboard_material()