# Community Lighting：地图光照

用户指定的光照候选；用户提醒：agent 编辑出来的效果可能不好。实际布光需要游戏画面与用户反馈，不将参数合法等同于视觉效果合格。

- JS 文件名：`Community_Lighting_MZ.js`，MZ 版；不要与 MV 的 `Community_Lighting.js` 混用。
- shadow 完整注册名：`visual/Community_Lighting_MZ`，当前已启用；本地声明版本 4.6。
- [维护仓库与说明](https://github.com/ImaginaryVillain/community_lights)、[MZ 文件](https://github.com/ImaginaryVillain/community_lights/blob/master/Community_Lighting_MZ.js)。在线版本可能与本地不同。

## 功能与入口

地图暗化与光源、火焰闪烁、手电筒、昼夜循环、按 ID 控制灯光、图块光照与遮挡。使用前先通过 `manual()` 读用法，再通过 `help()` 获取相关参数结构、`parameters.get()` 读取当前配置；命令参数用 `commands.help(id)` 查询，不直接翻源码注释。

本地命令入口包括 `masterSwitch`、`activateById`、`lightColor`、`playerLightRadius`、`flashlight`、`setTint`、`setTime`、`tileLight`、`tileBlock`。这里只列 ID，不凭名称猜测参数或范围。

默认 Note Tag Key 为 CL 时，事件备注光源示例为 `<cl: light 250 #ffffff>`。先读取目标工程实际 Note Tag Key；为空时采用不同的兼容语法，不机械复制示例。数字 250 只是帮助中的用法示例，不是推荐布光半径。事件页首条注释可覆盖事件备注光照，具体支持以当前版本帮助为准。

## 制作与验证

结合地图尺寸、光源位置、环境亮度和画风确定配置，参照[光照手记](../../production-notes/lighting-review.md)。只在已确认范围内修改地图/事件，不默认批量布光。修改 plugins.js 使用插件正式脚本；地图备注与事件修改使用数据库/事件正式接口。

2026-10-12 已通过帮助接口读取本地用法并检查启用状态，补充核对维护仓库网页；未修改游戏配置、未进行画面测试。收录不代表本次已验证画面品质或插件兼容性。
