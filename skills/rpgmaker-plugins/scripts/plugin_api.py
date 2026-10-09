"""插件清单对象接口；所有预览、写入均调用正式 plugins_js.py 后端。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import plugins_js

class Plugins:
    """注册项编辑器。收集修改后 preview，再 commit(preview)；不编辑插件源码文件。"""
    def __init__(self,project):
        self.file=Path(project).resolve(strict=True)/'js/plugins.js'
        self.operations=[]
        self._parameter_source=None
        self._declarations={}
    def list(self):
        return plugins_js.run(['--file',str(self.file),'inspect'])['plugins']
    def get(self,name):
        return plugins_js.run(['--file',str(self.file),'inspect','--name',name])['plugins'][0]
    def add(self,name,*,enabled=False,description='',parameters=None,before=None,after=None):
        """注册插件，默认禁用。name 是相对路径，不含 .js；源码文件需先创建。"""
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Invalid plugin path')
        source=self.file.parent/'plugins'/path.with_suffix('.js')
        if not source.is_file() or not source.resolve().is_relative_to((self.file.parent/'plugins').resolve()):raise ValueError('Plugin source missing or outside plugins directory')
        op={'op':'add','plugin':{'name':name,'status':enabled,'description':description,'parameters':parameters or {}}}
        if before is not None:op['before']=before
        if after is not None:op['after']=after
        self.operations.append(op)
    def update(self,name,*,enabled=None,description=None,parameters=None,unset_parameters=None):
        """修改启停、说明或参数；参数值必须为字符串，未指定项保留。"""
        op={'op':'update','name':name}
        for key,value in [('status',enabled),('description',description),('parameters',parameters),('unset_parameters',unset_parameters)]:
            if value is not None:op[key]=value
        self.operations.append(op)
    def remove(self,name):
        """仅移除注册，不删除 .js 文件。"""
        self.operations.append({'op':'remove','name':name})
    def move(self,name,*,before=None,after=None):
        """调整加载顺序，before/after 必须且只能指定一项。"""
        op={'op':'move','name':name}
        if before is not None:op['before']=before
        if after is not None:op['after']=after
        self.operations.append(op)
    def _parameter_context(self,name,language):
        from parameter_paths import metadata
        source=self.file.read_bytes()
        if self._parameter_source is not None and source!=self._parameter_source:
            raise ValueError('Plugin configuration changed; create a new Plugins object')
        records=plugins_js.parse(source)[3]
        if self.operations:records=plugins_js.transform(records,self._plan())
        matches=[p for p in records if p['name']==name]
        if len(matches)!=1:raise ValueError('Use exact registered plugin path')
        meta=metadata(self.file.parent.parent,name,language)
        return source,matches[0]['parameters'],meta
    def parameter_help(self,name,path=None,*,language='zh'):
        """按声明返回简短参数路径、类型、当前值及说明；path 指定后展开一层。"""
        from parameter_paths import help_paths
        _,parameters,meta=self._parameter_context(name,language)
        return help_paths(meta,parameters,path)
    def set_parameter(self,name,path,value,*,language='zh'):
        """按声明修改参数。路径如 ['Settings','Entries',0,'Enabled']，无需手工 JSON 编解码。

        数组下标从 0 开始；布尔值用 bool，数值用 int/float；结构体 dict 合并字段。
        缺失声明、非法编码、错误类型、越界下标或超出声明范围均拒绝。
        """
        from parameter_paths import path_parts,field,walk,MISSING
        source,parameters,meta=self._parameter_context(name,language)
        path=path_parts(path);spec=field(meta['parameters'],path[0])
        updated=walk(spec,parameters.get(path[0],MISSING),path[1:],meta,value)
        declaration=Path(meta['source']);raw=declaration.read_bytes()
        if declaration in self._declarations and self._declarations[declaration]!=raw:
            raise ValueError('Plugin declaration changed; create a new Plugins object')
        self._parameter_source=source;self._declarations[declaration]=raw
        self.update(name,parameters={path[0]:updated})
    def _check_parameter_sources(self):
        if self._parameter_source is not None and self.file.read_bytes()!=self._parameter_source:
            raise ValueError('Plugin configuration changed; read parameters again')
        for path,source in self._declarations.items():
            if path.read_bytes()!=source:raise ValueError('Plugin declaration changed; read parameters again')
    def _plan(self):return {'version':1,'operations':deepcopy(self.operations)}
    def _fingerprint(self):return hashlib.sha256(json.dumps(self._plan(),sort_keys=True,ensure_ascii=True).encode()).hexdigest()
    def _run(self,preview=None):
        self._check_parameter_sources()
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.json';plan.write_text(json.dumps(self._plan(),ensure_ascii=False),encoding='utf-8')
            args=['--file',str(self.file),'apply','--plan',str(plan)]
            if preview is not None:
                if preview['plan_sha256']!=self._fingerprint():raise ValueError('Plan changed; preview again')
                args+=['--write','--expect-sha256',preview['sha256']]
            result=plugins_js.run(args);result['plan_sha256']=self._fingerprint();return result
    def preview(self):return self._run()
    def commit(self,preview):
        result=self._run(preview);self.operations.clear();self._parameter_source=None;self._declarations.clear();return result
