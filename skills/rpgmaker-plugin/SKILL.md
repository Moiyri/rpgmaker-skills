---
name: rpgmaker-plugin
description: RPG Maker 插件统一入口。查询工程插件列表、文件是否安装、plugins.js 注册及启用状态、当前参数、插件命令与用法时使用；事件开发依赖插件时先用本技能检查。修改 plugins.js 转交 rpgmaker-plugins 正式脚本；插件编写流程后续完善。
---

# RPG Maker 插件

## 范围与依赖

当前完成查询。统一入口为 `scripts/plugin.py`，Python 3.10+。同时分发相邻 `rpgmaker-plugins` 和 `rpgmaker-events`：复用插件清单安全解析器和插件声明解析器，缺少依赖时停止并补齐。`plugin.js` 通常指工程实际文件 `js/plugins.js`，不要另建同名清单。

查询不执行 JavaScript。返回简短文本；失败写 stderr、退出码 1。只解析编辑器式 plugins.js，不支持执行表达式配置。插件可用完整子目录路径或唯一短名称，重复注册、同名歧义、非法路径时明确报错。

## 查询

`<skill>` 为本目录，`<project>` 为工程根目录。

```sh
python3 "<skill>/scripts/plugin.py" --project "<project>" list
python3 "<skill>/scripts/plugin.py" --project "<project>" list --search Message --enabled
python3 "<skill>/scripts/plugin.py" --project "<project>" check --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" parameters --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" parameters --plugin Ve_1_Message --parameter defaultLanguage
python3 "<skill>/scripts/plugin.py" --project "<project>" help --plugin Ve_1_Message
python3 "<skill>/scripts/plugin.py" --project "<project>" help --plugin Ve_1_Message --command ShowDialogue
```

- list：按清单加载顺序列出注册项，再列未注册的 .js 文件；不把文件存在等同于启用。
- check：区分未安装、未注册、已禁用、文件缺失和已启用。启用状态只是清单配置，不证明运行时加载成功。
- parameters：工程当前配置值；长值概要省略，指定参数取得完整值，保留多层编码字符串。
- help：插件声明的命令及用法。`--section parameters` 查看配置参数声明及默认值，`--struct 名称` 查看结构体，`--section help` 查看完整帮助；`--language` 选择语言。当前值与声明默认值不是一回事。

Python 方法：`check_plugin(project, plugin)`、`list_plugins(project)`、`plugin_parameters(project, plugin, parameter=None)`、`plugin_help(project, plugin, command=None, section='commands', struct=None)`，返回文本。

## 事件开发联动

编写依赖插件的事件前先 check，再 help 查询命令和参数；同一工程同一插件本轮检查一次即可，配置变化后重新检查。缺失、未注册或禁用时报告，不因检查而擅自安装或启用。原生事件指令无需检查插件。

## 编辑与编写入口

修改清单时阅读 [rpgmaker-plugins](../rpgmaker-plugins/SKILL.md)，只调用其 `plugins_js.py` 预览、写入和恢复。插件源码编写属于本技能后续开发范围；当前查询结果不能代替源码实现、依赖分析和 Playtest。
