# CGMZ：全局数据与变量

用户指定跨存档数据候选。准确名称是 `CGMZ_Core.js`，不是 CGMG_Core。

| JS | 本地版本 | 官方说明 |
| --- | --- | --- |
| `CGMZ_Core.js` | 1.29.0 | [Core](https://www.caspergaming.com/plugins/cgmz/core/) |
| `CGMZ_GlobalData.js` | 1.0.2 | [Global Data](https://www.caspergaming.com/plugins/cgmz/globaldata/) |

作者 Casper Gaming。网页取自源码 @url；shadow 两个插件均在 js/plugins 根目录注册并启用。GlobalData 明确依赖 Core 且加载在其后；保留原文件名。两份本地帮助标注面向 MZ 1.9.0，不代表只允许此版本，也不证明与任意插件兼容。

用于跨存档解锁、全局开关/变量和键值数据。普通剧情进度仍随正常存档；仅将用户明确需要跨档共享的数据设为全局。参数 `Global Switches`、`Global Variables` 指定自动管理的 ID。

手动键值入口：`Add Text Data`、`Add Number Data`、`Add Variable Data`、`Add Switch Data`；读取用 `Get Data`/`Get Switch Data`，删除用 `Clear Data`。Key 区分大小写，同键新值覆盖旧值。默认随游戏保存写入，也可用 `Save Data` 独立保存，不能把设置内存值等同于已落盘。

Core 是依赖，不是独立全局存储功能。不要将其 `Initialize` 命令当普通准备步骤，它会重置 CGMZ 数据。若工程已有 Save Core 的全局数据机制或自定义实现，先选定管理方式，不让多套系统同时管理同一变量。

本次仅核对帮助、依赖和启用状态；应在隔离测试数据中检查跨档、新游戏和退出重启后的读写，避免污染正式全局进度。
