# Gabe MZ Step Sound

准确文件名 `GabeMZ_StepSound.js`，shadow 注册名 `sound/GabeMZ_StepSound`，已启用。本地版本 1.1.1，作者 Gabe（Gabriel Nascimento），面向 MZ。[作者仓库](https://github.com/comuns-rpgmaker/GabeMZ)来自本地 `@url` 声明；不分发第三方源码。

## 能力与用法

角色行走时播放脚步音效，支持地图区域 ID、图块组地形标记及事件脚步声。先通过 `.manual()` 阅读说明，再查询 `stepSoundSettings` 与 `stepSoundsStruct` 的参数帮助和当前值。

在 Step Sound Settings 配置音效组。帮助示例 Base Name 为 `Step_Dirt`、Files Variance 为 4，会随机播放 `Step_Dirt1` 至 `Step_Dirt4`；音效文件放在工程 SE 目录。音量、音高、声像及各自随机变化通过结构参数配置。

地图备注 `<stepSound 131: 1>` 表示区域 131 使用脚步音效组 1。这里两种 ID 不相同，配置前核对音效组实际对应关系。相同格式写在图块组备注时，第一个数表示地形标记，不是区域 ID。

事件备注 `<stepSound>` 允许事件移动时播放脚步声。插件另有玩家、跟随者、事件脚步声开关命令，使用前查询命令声明；事件命令 ID 参数为 0 时针对当前事件。

默认制作方式见[脚步声手记](../../production-notes/how-to-add-footstep-sounds.md)。已核对本地帮助、参数和启用状态，未做运行测试。
