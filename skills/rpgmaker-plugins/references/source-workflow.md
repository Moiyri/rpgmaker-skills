# 插件源码与清单

## 新增

先明确运行时行为、参数和依赖，再创建 `js/plugins/相对路径.js`；头部按工程 MV/MZ 声明参数及命令。核对实际引擎源码，不猜方法或参数。使用 `node --check` 检查语法，再通过 Plugins.add 或 plugins.py 注册，预览并提交。新增默认禁用，需要启用时显式 enabled=True。Debug 的工程功能优先写子插件，放在 Debug 后。

## 修改

源码文件可正常编辑，保持工程风格，保留不相关行为。参数配置必须走正式清单脚本；不是替换源码中的默认值。先 plugins.py help 查看顶层字段，help --struct 名称查看结构体，parameters 查看当前值。

参数修改先调用 `plugins.get(name).help(struct)`，根据字段声明构建路径并使用 `set_parameter(name, path, value)`，不让 agent 逐层 loads/dumps。结构体、数组、note 由脚本处理编码；不猜测缺失声明。删参数使用 unset_parameters。改名称或路径时先检查插件内部如何取得 PluginManager 参数、命令注册名及其他插件依赖，不仅改文件名。

## 删除

区分需求：禁用只 update(enabled=False)；移除清单用 remove；完全卸载还需要删除源码文件。先查询插件命令引用、其他插件依赖和参数；动态脚本引用无法穷尽时报告限制。用户明确要求完全卸载时，先备份源码、移除注册并提交，再删除对应文件，不删除素材或其他插件。插件清单恢复仍使用 plugins.py restore；源码恢复使用源码备份。

## 验证

配置写入后重新查询；源码修改运行 node --check，再按需用 playtest 技能测试实际行为。文件校验不等于游戏测试。记录修改与验证范围；不自动修改工程数据库以消除报错。
