# MUSH Audio Engine：配音候选

用户经验：这是比较庞大的音频插件，主要用来做配音。配音需求优先评估现有 MUSH 能力，不为普通 SE 播放默认引入整个音频引擎。

准确文件名 `MUSH_Audio_Engine.js`；shadow 注册路径 `sound/MUSH_Audio_Engine`。作者 MushroomCake28，本地版本 1.08，MZ。[原发布页](https://forums.rpgmakerweb.com/index.php?threads/mush-audio-engine-spatial-audio-voice-acting-new-channels-etc.128741/)取自 @url，当前网页可访问性未验证。

具备 VSC（Voice Sound Channel）配音通道，也涉及 UI 音效、多个 BGM/BGS、空间音频、音量管理等。原版帮助称关闭 `Voice Sound Channel` 后使用 SE 音量；但已核对 1.08 源码，VSC 播放路径直接使用 VSC 音量计算，未见该处回退判断，不能把帮助描述当作已验证行为。原版命令入口 `PlayVsc`、`StopVsc`，使用前查询实际参数，不凭名称猜路径或停止范围。

配音整合需明确语音文件与台词对应关系、切句/跳过时的停止规则、音量控制；插件不自动完成整个对白配音流程。先检查素材，再告知用户需要的文件格式、命名和目录，由用户准备音频。

源码明确会改造音频系统。仅核对与当前需求相关的音频插件交互，不预先编写大量兼容层。本次只读取声明与帮助，未验证播放；后续测试台词切换、跳过、停止、场景切换及音量控制。

## 原版与工程扩展的边界

2026-10-12 对照用户从[作者 itch.io 发布页](https://kamo-studio.itch.io/rpg-maker-mz-plugin-mush-audio-engine)下载的 `/Users/moiyri/Downloads/MUSH_Audio_Engine.js`（1.08）与 shadow 工程版。原版包含 `PlayVsc`、`StopVsc`，以及 `AudioManager.playVscManually` 等接口；没有消息标记解析。

工程版新增 `ENABLE_VSC` 参数、`enableVsc` 命令，以及消息开始时解析 `\vsc[...]` / `${...}` 的逻辑。这些不可写成原版插件能力；其中 `${...}` 已由用户明确确认为自己的补充功能。原版不自动在对话关闭时停止语音，也不提供自动等待语音结束后翻页的消息集成。

该核对只涉及源码，不代表实际音频播放测试；不将下载的原版文件放入技能库再分发。
