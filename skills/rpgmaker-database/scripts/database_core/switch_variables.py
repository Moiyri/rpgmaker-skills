"""开关和变量名称；运行时的值由事件指令控制。"""
from .system import TypeList


class NamedSlots:
    """现有编号名称表，支持 list/find/get/set/clear。

    ID 从 1 开始，由调用方选择位置；set 只修改已有编号名称。
    clear 清空名称，保留编号及引用，不重置存档值；空名称不等于未被使用。
    """
    def __init__(self,system,key,title):
        self._names=TypeList(system,key,title)
    def list(self,*,search=None,offset=0,limit=50):
        """列出编号和名称，支持搜索及分页。"""
        return self._names.list(search=search,offset=offset,limit=limit)
    def find(self,text):
        """按名称搜索，返回 (ID, 名称) 列表。"""
        return self._names.find(text)
    def get(self,id):
        """读取已有编号的名称。"""
        return self._names.get(id)
    def set(self,id,name):
        """为选定的已有编号命名。"""
        self._names.set(id,name)
    def clear(self,id):
        """清空名称，不删除编号、不重置游戏中的开关状态或变量值。"""
        self.set(id,'')
