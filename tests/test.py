# 导入Maya Python命令模块
import maya.cmds as cmds

# 定义草叶轴心点专用UV集名称（全局常量）
GrassPivotUVSetName = 'GrassPivotUV'

def GetSelection():
    '''获取当前Maya中选中的对象列表'''
    list_select = []
    # 判断是否有选中对象
    if cmds.ls(selection=True) != []:
        # 获取选中对象并赋值
        list_select = cmds.ls(selection=True)
        return list_select
    else:
        # 无选中对象时返回空列表
        return []

def CollectSelectionMeshs(selections):
    '''收集选中对象及其所有子级变换节点（用于批量处理模型）'''
    def RemoveStringPrefix(inStr):
        '''内部工具函数：移除字符串开头的 | 符号'''
        return inStr[1:] if inStr[0] == '|' else inStr
  
    def GetTransformChildren(input_node, output_list, spec_type='transform'):
        '''
        递归获取节点下所有指定类型的子节点
        input_node: 输入节点
        output_list: 存储结果的列表
        spec_type: 要查找的节点类型，默认transform
        '''
        # 如果当前节点是指定类型，则记录到列表
        if cmds.nodeType(input_node) == spec_type:
            cur_node = cmds.ls(input_node, long=True)
            if cur_node not in output_list:
                output_list.append(cur_node)
        # 获取当前节点的子节点
        children_node = cmds.listRelatives(input_node, fullPath=True, children=True, type=spec_type)
        # 递归遍历所有子节点
        if children_node is not None:
            for c in children_node:
                GetTransformChildren(c, output_list)

    # 存储所有需要处理的模型节点
    all_node = []
    # 遍历选中对象，递归收集所有子级变换节点
    for s in selections:
        GetTransformChildren(s, all_node)
    return all_node

def GetBladeCenter(bladeName):
    '''获取单个模型的轴心点世界坐标'''
    # query查询、ws世界空间、rp轴心点坐标
    pos = cmds.xform(bladeName, q=True, ws=True, rp=True)
    return pos

def SetUVValue(uValue, vValue, setName):
    '''设置当前选中UV的坐标值（绝对赋值）'''
    # relative=False 表示使用绝对坐标而非偏移量
    cmds.polyEditUV(u=uValue, v=vValue, relative=False)

def PrintUVValue(uvs, title='uvs'):
    '''打印UV点坐标信息（调试用）'''
    print(title)
    for uv in uvs:
        print(cmds.polyEditUV(uv, query=True))

def TipMessage(str_msg='Done'):
    '''弹出Maya提示窗口'''
    cmds.confirmDialog(title='ReedPivotBaker', message=str_msg, button=['OK'])

def SavePivotToUV():
    '''主功能：将模型轴心点信息烘焙到专用UV通道'''
    # 获取选中对象
    selections = GetSelection()
    # 无选择时给出警告并退出
    if len(selections) == 0:
        cmds.warning('please choose at least One Mesh')
        return
  
    print('===================================')
    # 收集所有需要处理的模型
    select_meshs = CollectSelectionMeshs(selections)

    # 遍历每一个模型进行处理
    for obj in select_meshs:
        print('-----------------------------')
        print("0 - {}".format(obj))

        # 选中当前处理的模型
        cmds.select(obj)
        try:
            # 获取模型现有的所有UV集
            uv_set_list = cmds.polyUVSet(query=True, allUVSets=True)
            # 如果没有专用UV集，则创建
            if GrassPivotUVSetName not in uv_set_list:
                cmds.polyUVSet(create=True, uvSet=GrassPivotUVSetName)
      
            # 对专用UV集执行自动UV投射
            cmds.polyAutoProjection(uvSetName=GrassPivotUVSetName)
            # 将草叶轴心UV集调整为第二个UV通道（方便引擎/材质读取）
            print(uv_set_list)
            if uv_set_list[1] != GrassPivotUVSetName:
                cmds.polyUVSet(reorder=True, newUVSet=GrassPivotUVSetName, uvSet=uv_set_list[1])
            # 打印处理后的UV集列表（调试）
            print(cmds.polyUVSet(query=True, allUVSets=True))

            # 获取模型轴心点世界坐标
            blade_center = GetBladeCenter(obj)

            # 选中模型所有UV点
            uvs = cmds.polyListComponentConversion(tuv=True)
            cmds.select(uvs)
            # 打印修改前UV值
            PrintUVValue(uvs, '2 - before editing UV')
            # 将 X 坐标赋给 U，Z 坐标反转后赋给 V（烘焙轴心信息）
            SetUVValue(blade_center[0], 1.0 - blade_center[2], GrassPivotUVSetName)
            # 打印修改后UV值
            PrintUVValue(uvs, '3 - after editing UV')
      
            # 重新选中模型
            cmds.select(obj)
            # 刷新UV集列表
            uv_set_list = cmds.polyUVSet(query=True, allUVSets=True)
        except Exception as e:
            # 捕获异常，避免单个模型错误导致整体中断
            print("处理对象出错：", obj, "错误信息：", str(e))

    # 刷新Maya视图
    cmds.refresh()
    # 弹出完成提示
    TipMessage('finish Grass Pivot saving')

# 执行主函数（运行脚本即开始工作）
SavePivotToUV()