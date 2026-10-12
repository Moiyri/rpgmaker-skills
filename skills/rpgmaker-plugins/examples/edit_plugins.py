"""注册、编辑、排序、移除的独立示例；不自动执行。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from plugins import Plugins

def enable_debug(project):
    plugins=Plugins(project)
    # Debug.js 已复制到此位置时新增注册；已注册则使用 update。
    plugins.add('playtest/Debug',enabled=True,description='测试工具')
    preview=plugins.preview()
    print(preview['diff'])
    return plugins.commit(preview)

def edit_parameters(project, plugin_name):
    plugins=Plugins(project)
    print(plugins.get(plugin_name).help())
    # 仅在查询结果确实声明这些字段和类型时使用。
    plugins.set_parameter(plugin_name, ['Enabled'], True)
    plugins.set_parameter(plugin_name, ['Speed'], 4)
    preview=plugins.preview()
    print(preview['diff'])
    return plugins.commit(preview)

# 同样先 preview 再 commit：
# plugins.update(name, enabled=False)       禁用
# plugins.update(name, unset_parameters=['OldKey']) 删除参数
# plugins.move(name, after='playtest/Debug') 调整顺序
# plugins.remove(name)                     仅删除注册
